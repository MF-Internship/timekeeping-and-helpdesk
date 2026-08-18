from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from threading import Event
from typing import Any, cast

from django.db import close_old_connections, transaction
from rest_framework.test import APIClient
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from audit.adapters.persistence.recording import DjangoAuditRecorder
from audit.models import AuditLog, OutboxEvent
from identity.adapters.persistence.unit_of_work import DjangoUnitOfWork
from identity.adapters.persistence.users import DjangoUserRepository
from identity.adapters.security.passwords import DjangoPasswordService
from identity.adapters.security.sessions import SimpleJWTSessionRepository
from identity.application.authentication import AuthenticationService
from identity.application.dependencies import IdentityDependencies
from identity.application.dto import PasswordChangeRequest
from identity.application.self_service import SelfService
from identity.application.user_admin import UserAdminService
from identity.models import User
from identity.ports.sessions import IssuedSession, RevocationReason, SessionRepository
from identity.ports.users import MutableUserRepository

ORIGIN = "test-origin-credential-at-least-32-chars"
OLD_PASSWORD = "SafePassword123!"
RESET_PASSWORD = "ResetPassword456!"
CHANGED_PASSWORD = "ChangedPassword456!"


def make_user(username: str, role: str = "HELPDESK") -> User:
    return User.objects.create_user(
        username=username,
        password=OLD_PASSWORD,
        full_name=username.title(),
        role=role,
        must_change_password=False,
    )


def assert_refresh_rejected(raw: str) -> None:
    try:
        RefreshToken(cast(Any, raw))
    except TokenError:
        return
    raise AssertionError("revoked refresh remained usable")


class BlockingSessionRepository:
    def __init__(self, issuance: str, issued: Event, release: Event) -> None:
        self.delegate = SimpleJWTSessionRepository()
        self.issuance = issuance
        self.issued = issued
        self.release = release

    def issue(self, user_id: int) -> IssuedSession:
        result = self.delegate.issue(user_id)
        if self.issuance == "login":
            self._pause()
        return result

    def rotate(self, refresh: str) -> IssuedSession:
        result = self.delegate.rotate(refresh)
        if self.issuance == "refresh":
            self._pause()
        return result

    def revoke_all(self, user_id: int, reason: RevocationReason) -> int:
        return self.delegate.revoke_all(user_id, reason)

    def refresh_owner(self, refresh: str) -> int:
        return self.delegate.refresh_owner(refresh)

    def _pause(self) -> None:
        self.issued.set()
        if not self.release.wait(timeout=10):
            raise TimeoutError("issuance race was not released")


class SignalingUserRepository:
    def __init__(self, waiting: Event) -> None:
        self.delegate = DjangoUserRepository()
        self.waiting = waiting

    def get_for_update(self, user_id: int) -> Any:
        self.waiting.set()
        return self.delegate.get_for_update(user_id)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.delegate, name)


@dataclass(slots=True)
class RaceContext:
    target: User
    actor: User
    issuance: str
    revocation: RevocationReason
    seed: IssuedSession
    original_password_hash: str
    issued: Event = field(default_factory=Event)
    revocation_waiting: Event = field(default_factory=Event)
    release: Event = field(default_factory=Event)
    output: dict[str, Any] = field(default_factory=dict)


def _dependencies(
    *, users: MutableUserRepository | None = None, sessions: SessionRepository | None = None
) -> IdentityDependencies:
    return IdentityDependencies(
        users or DjangoUserRepository(),
        DjangoPasswordService(),
        sessions or SimpleJWTSessionRepository(),
        DjangoUnitOfWork,
        DjangoAuditRecorder(),
    )


def _issue_worker(context: RaceContext) -> None:
    close_old_connections()
    try:
        sessions = cast(
            SessionRepository,
            BlockingSessionRepository(context.issuance, context.issued, context.release),
        )
        service = AuthenticationService(_dependencies(sessions=sessions))
        if context.issuance == "login":
            result, _account, _capabilities = service.login(context.target.username, OLD_PASSWORD)
        else:
            result = service.refresh(context.seed.refresh)
        context.output["racing"] = result
    finally:
        close_old_connections()


def _revoke_worker(context: RaceContext) -> None:
    close_old_connections()
    context.issued.wait(timeout=10)
    try:
        users = cast(MutableUserRepository, SignalingUserRepository(context.revocation_waiting))
        dependencies = _dependencies(users=users)
        if context.revocation is RevocationReason.LOGOUT:
            AuthenticationService(dependencies).logout(context.target.pk, context.seed.refresh)
        elif context.revocation is RevocationReason.PASSWORD_RESET:
            context.output["reset"] = UserAdminService(dependencies).reset_password(
                context.actor.pk, context.target.pk
            )
        elif context.revocation is RevocationReason.PASSWORD_CHANGE:
            context.output["replacement"] = SelfService(dependencies).change_password(
                context.target.pk,
                PasswordChangeRequest(OLD_PASSWORD, CHANGED_PASSWORD),
            )
        else:
            UserAdminService(dependencies).change_status(context.actor.pk, context.target.pk, False)
    finally:
        close_old_connections()


def _assert_access_behavior(context: RaceContext) -> None:
    client = APIClient(HTTP_X_ORIGIN_CREDENTIAL=ORIGIN)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {context.output['racing'].access}")
    response = client.get("/api/v1/me/")
    expected = {
        RevocationReason.LOGOUT: (200, None),
        RevocationReason.PASSWORD_RESET: (403, "PASSWORD_CHANGE_REQUIRED"),
        RevocationReason.PASSWORD_CHANGE: (200, None),
        RevocationReason.ACCOUNT_DEACTIVATED: (401, "ACCOUNT_INACTIVE"),
    }[context.revocation]
    assert response.status_code == expected[0]
    if expected[1] is not None:
        assert response.json()["error_code"] == expected[1]


def _assert_final_state(context: RaceContext) -> None:
    context.target.refresh_from_db()
    expected_live = 1 if context.revocation is RevocationReason.PASSWORD_CHANGE else 0
    outstanding = OutstandingToken.objects.filter(user_id=context.target.pk)
    assert outstanding.filter(blacklistedtoken__isnull=True).count() == expected_live
    assert BlacklistedToken.objects.filter(token__user_id=context.target.pk).exists()
    assert_refresh_rejected(context.seed.refresh)
    assert_refresh_rejected(context.output["racing"].refresh)
    assert context.target.is_active is not (
        context.revocation is RevocationReason.ACCOUNT_DEACTIVATED
    )
    assert context.target.must_change_password is (
        context.revocation is RevocationReason.PASSWORD_RESET
    )
    password_changed = context.revocation in {
        RevocationReason.PASSWORD_RESET,
        RevocationReason.PASSWORD_CHANGE,
    }
    assert (context.target.password != context.original_password_hash) is password_changed
    if context.revocation is RevocationReason.PASSWORD_CHANGE:
        RefreshToken(context.output["replacement"].refresh)
    expected_events = 1 if context.revocation is RevocationReason.LOGOUT else 2
    assert AuditLog.objects.filter(target_id=str(context.target.pk)).count() == expected_events
    events = OutboxEvent.objects.filter(aggregate_id=str(context.target.pk)).order_by(
        "aggregate_version"
    )
    assert list(events.values_list("aggregate_version", flat=True)) == list(
        range(1, expected_events + 1)
    )
    assert all(event.payload["user_id"] == context.target.pk for event in events)
    _assert_access_behavior(context)


def run_issuance_revocation_race(*, issuance: str, revocation: RevocationReason) -> dict[str, Any]:
    target = make_user(f"target-{issuance}-{revocation.value.lower()}")
    actor = (
        target
        if revocation in {RevocationReason.LOGOUT, RevocationReason.PASSWORD_CHANGE}
        else make_user(f"actor-{issuance}-{revocation.value.lower()}", "MANAGER")
    )
    with transaction.atomic():
        seed = SimpleJWTSessionRepository().issue(target.pk)
    context = RaceContext(target, actor, issuance, revocation, seed, target.password)

    with ThreadPoolExecutor(max_workers=2) as executor:
        issue_future = executor.submit(_issue_worker, context)
        revoke_future = executor.submit(_revoke_worker, context)
        assert context.issued.wait(timeout=10)
        assert context.revocation_waiting.wait(timeout=10)
        context.release.set()
        issue_future.result(timeout=15)
        revoke_future.result(timeout=15)

    _assert_final_state(context)
    context.output["target"] = context.target
    context.output["seed"] = seed
    return context.output
