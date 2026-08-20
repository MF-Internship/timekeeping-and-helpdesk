from __future__ import annotations

from dataclasses import dataclass, replace

from audit.ports.recording import AuditAction, AuditEntry, IdentityEventType, OutboxRecord
from core.error_codes import PERMISSION_DENIED
from core.errors import IdentityAPIError
from identity.application.dependencies import IdentityDependencies
from identity.application.dto import (
    GeneratedPasswordDisplayResult,
    ProfileUpdateRequest,
    UserCreateRequest,
)
from identity.domain.accounts import AccountSnapshot, NewAccount
from identity.domain.authorization import ASSIGNABLE_ROLES, Role
from identity.ports.push_subscriptions import PushSubscriptionRevocationReason
from identity.ports.sessions import RevocationReason


@dataclass(frozen=True, slots=True)
class MutationEvidence:
    action: AuditAction
    event: IdentityEventType
    target: AccountSnapshot
    audit_before: dict[str, object]
    audit_after: dict[str, object]
    event_payload: dict[str, object]


@dataclass(frozen=True, slots=True)
class RevocationEvidence:
    count: int
    reason: RevocationReason


class UserAdminService:
    def __init__(self, dependencies: IdentityDependencies) -> None:
        self.users = dependencies.users
        self.passwords = dependencies.passwords
        self.sessions = dependencies.sessions
        self.unit_of_work_factory = dependencies.unit_of_work_factory
        self.audit = dependencies.audit
        self.push_subscriptions = dependencies.push_subscriptions

    def create(self, actor_id: int, request: UserCreateRequest) -> GeneratedPasswordDisplayResult:
        if request.role not in ASSIGNABLE_ROLES:
            raise IdentityAPIError(PERMISSION_DENIED, status_code=403)
        generated = self.passwords.generate(request.username)
        with self.unit_of_work_factory():
            account = self.users.create(self._new_account(request, generated))
            self._record(actor_id, self._created_evidence(account))
        return GeneratedPasswordDisplayResult(account, generated)

    def _new_account(self, request: UserCreateRequest, generated: str) -> NewAccount:
        return NewAccount(
            username=request.username,
            full_name=request.full_name,
            phone=request.phone,
            email=request.email,
            role=request.role,
            password_hash=self.passwords.encode(generated),
        )

    @classmethod
    def _created_evidence(cls, account: AccountSnapshot) -> MutationEvidence:
        payload: dict[str, object] = {
            "user_id": account.id,
            "role": account.role.value,
            "is_active": account.is_active,
            "must_change_password": account.must_change_password,
        }
        return MutationEvidence(
            AuditAction.USER_CREATED,
            IdentityEventType.USER_CREATED,
            account,
            {},
            cls._audit_created(account),
            payload,
        )

    def update_profile(
        self, actor_id: int, target_id: int, request: ProfileUpdateRequest
    ) -> AccountSnapshot:
        with self.unit_of_work_factory():
            before = self._eligible_locked(target_id)
            full_name = (
                request.full_name if "full_name" in request.provided_fields else before.full_name
            )
            if full_name is None:
                raise ValueError("full_name")
            after = replace(
                before,
                full_name=full_name,
                phone=request.phone if "phone" in request.provided_fields else before.phone,
                email=request.email if "email" in request.provided_fields else before.email,
            )
            saved = self.users.save(after)
            changed_fields = sorted(request.provided_fields)
            self._record(
                actor_id,
                MutationEvidence(
                    AuditAction.USER_PROFILE_UPDATED,
                    IdentityEventType.USER_PROFILE_UPDATED,
                    saved,
                    self._profile_values(before, changed_fields),
                    self._profile_values(saved, changed_fields),
                    {"user_id": saved.id, "changed_fields": changed_fields},
                ),
            )
            return saved

    def change_role(self, actor_id: int, target_id: int, role: Role) -> AccountSnapshot:
        if role not in ASSIGNABLE_ROLES:
            raise IdentityAPIError(PERMISSION_DENIED, status_code=403)
        with self.unit_of_work_factory():
            before = self._eligible_locked(target_id)
            saved = self.users.save(replace(before, role=role))
            self._record(
                actor_id,
                MutationEvidence(
                    AuditAction.USER_ROLE_CHANGED,
                    IdentityEventType.USER_ROLE_CHANGED,
                    saved,
                    {"role": before.role.value},
                    {"role": saved.role.value},
                    {
                        "user_id": saved.id,
                        "previous_role": before.role.value,
                        "role": saved.role.value,
                    },
                ),
            )
            return saved

    def change_status(self, actor_id: int, target_id: int, is_active: bool) -> AccountSnapshot:
        with self.unit_of_work_factory():
            before = self._eligible_locked(target_id)
            if before.is_active is is_active:
                return before
            saved = self.users.save(replace(before, is_active=is_active))
            self._record(
                actor_id,
                MutationEvidence(
                    AuditAction.USER_STATUS_CHANGED,
                    IdentityEventType.USER_STATUS_CHANGED,
                    saved,
                    {"is_active": before.is_active},
                    {"is_active": saved.is_active},
                    {"user_id": saved.id, "is_active": saved.is_active},
                ),
            )
            if before.is_active and not is_active:
                count = self.sessions.revoke_all(target_id, RevocationReason.ACCOUNT_DEACTIVATED)
                self.push_subscriptions.revoke_all(
                    target_id, PushSubscriptionRevocationReason.ACCOUNT_DEACTIVATED
                )
                self._record_revocation(
                    actor_id,
                    target_id,
                    RevocationEvidence(count, RevocationReason.ACCOUNT_DEACTIVATED),
                )
            return saved

    def reset_password(self, actor_id: int, target_id: int) -> GeneratedPasswordDisplayResult:
        with self.unit_of_work_factory():
            before = self._eligible_locked(target_id)
            generated = self.passwords.generate(before.username)
            saved = self.users.set_password(
                target_id, self.passwords.encode(generated), must_change=True
            )
            count = self.sessions.revoke_all(target_id, RevocationReason.PASSWORD_RESET)
            self._record(
                actor_id,
                MutationEvidence(
                    AuditAction.USER_PASSWORD_RESET,
                    IdentityEventType.USER_PASSWORD_RESET,
                    saved,
                    {"must_change_password": before.must_change_password},
                    {"must_change_password": True},
                    {"user_id": saved.id, "must_change_password": True},
                ),
            )
            self._record_revocation(
                actor_id,
                target_id,
                RevocationEvidence(count, RevocationReason.PASSWORD_RESET),
            )
            return GeneratedPasswordDisplayResult(saved, generated)

    def _eligible_locked(self, target_id: int) -> AccountSnapshot:
        target = self.users.get_for_update(target_id)
        if target is None:
            raise LookupError(target_id)
        if target.role is Role.MANAGER:
            raise IdentityAPIError(PERMISSION_DENIED, status_code=403)
        return target

    @staticmethod
    def _audit_created(account: AccountSnapshot) -> dict[str, object]:
        return {
            "user_id": account.id,
            "username": account.username,
            "full_name": account.full_name,
            "phone": account.phone,
            "email": account.email,
            "role": account.role.value,
            "is_active": account.is_active,
            "must_change_password": account.must_change_password,
        }

    @staticmethod
    def _profile_values(account: AccountSnapshot, changed_fields: list[str]) -> dict[str, object]:
        return {field: getattr(account, field) for field in changed_fields}

    def _record(self, actor_id: int, evidence: MutationEvidence) -> None:
        self.audit.append_audit_entry(
            AuditEntry(
                actor_id,
                evidence.action,
                "User",
                str(evidence.target.id),
                evidence.audit_before,
                evidence.audit_after,
            )
        )
        self.audit.append_outbox_event(
            OutboxRecord(
                evidence.event,
                "User",
                str(evidence.target.id),
                evidence.event_payload,
            )
        )

    def _record_revocation(
        self, actor_id: int, target_id: int, evidence: RevocationEvidence
    ) -> None:
        if evidence.count == 0:
            return
        before, after, event_payload = self._revocation_payloads(target_id, evidence)
        self.audit.append_audit_entry(
            AuditEntry(
                actor_id,
                AuditAction.SESSIONS_REVOKED,
                "User",
                str(target_id),
                before,
                after,
            )
        )
        self.audit.append_outbox_event(
            OutboxRecord(
                IdentityEventType.SESSIONS_REVOKED,
                "User",
                str(target_id),
                event_payload,
            )
        )

    @staticmethod
    def _revocation_payloads(
        target_id: int, evidence: RevocationEvidence
    ) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        before: dict[str, object] = {"active_refresh_sessions": evidence.count}
        shared: dict[str, object] = {
            "reason": evidence.reason.value,
            "revoked_refresh_session_count": evidence.count,
        }
        return before, {"active_refresh_sessions": 0, **shared}, {"user_id": target_id, **shared}
