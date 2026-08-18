from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from django.db import close_old_connections, transaction
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from audit.models import AuditLog, OutboxEvent
from config.composition import identity_container
from core.errors import IdentityAPIError
from identity.application.dto import ProfileUpdateRequest
from identity.domain.authorization import Role
from identity.models import User


def _make_users(operation: str) -> tuple[User, User]:
    actor = User.objects.create_user(
        username=f"toctou-actor-{operation}",
        password="SafePassword123!",
        full_name="Actor",
        role="MANAGER",
        must_change_password=False,
    )
    target = User.objects.create_user(
        username=f"toctou-target-{operation}",
        password="SafePassword123!",
        full_name="Before",
        role="HELPDESK",
        must_change_password=False,
    )
    with transaction.atomic():
        identity_container().sessions.issue(target.pk)
    return actor, target


def _mutate(operation: str, actor_id: int, target_id: int) -> str:
    service = identity_container().user_admin
    try:
        if operation == "profile":
            service.update_profile(
                actor_id,
                target_id,
                ProfileUpdateRequest(full_name="After", provided_fields=frozenset({"full_name"})),
            )
        elif operation == "role":
            service.change_role(actor_id, target_id, Role.LEADER)
        elif operation == "status":
            service.change_status(actor_id, target_id, False)
        else:
            service.reset_password(actor_id, target_id)
    except IdentityAPIError as error:
        return error.error_code
    return "unexpected-success"


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.parametrize("operation", ["profile", "role", "status", "reset"])
def test_locked_manager_recheck_closes_every_promotion_toctou(  # noqa: PLR0915
    operation: str,
) -> None:
    actor, target = _make_users(operation)
    original_password = target.password
    promoted = Event()
    release = Event()

    def promote() -> None:
        close_old_connections()
        try:
            with transaction.atomic():
                locked = User.objects.select_for_update().get(pk=target.pk)
                locked.role = "MANAGER"
                locked.save(update_fields=["role"])
                promoted.set()
                release.wait(timeout=10)
        finally:
            close_old_connections()

    def mutate() -> str:
        close_old_connections()
        try:
            promoted.wait(timeout=10)
            return _mutate(operation, actor.pk, target.pk)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        promotion = executor.submit(promote)
        mutation = executor.submit(mutate)
        promoted.wait(timeout=10)
        release.set()
        promotion.result(timeout=15)
        assert mutation.result(timeout=15) == "PERMISSION_DENIED"

    target.refresh_from_db()
    assert target.role == "MANAGER"
    assert target.full_name == "Before"
    assert target.is_active is True
    assert target.must_change_password is False
    assert target.password == original_password
    assert OutstandingToken.objects.filter(user=target).count() == 1
    assert BlacklistedToken.objects.filter(token__user=target).count() == 0
    assert AuditLog.objects.count() == 0
    assert OutboxEvent.objects.count() == 0
