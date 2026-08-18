from __future__ import annotations

from dataclasses import dataclass, replace

from audit.ports.recording import AuditAction, AuditEntry, IdentityEventType, OutboxRecord
from identity.application.dependencies import IdentityDependencies
from identity.application.dto import PasswordChangeRequest, ProfileUpdateRequest
from identity.domain.accounts import AccountSnapshot
from identity.ports.sessions import IssuedSession, RevocationReason


@dataclass(frozen=True, slots=True)
class ProfileEvidence:
    before: AccountSnapshot
    after: AccountSnapshot
    changed_fields: list[str]


class SelfService:
    def __init__(self, dependencies: IdentityDependencies) -> None:
        self.users = dependencies.users
        self.passwords = dependencies.passwords
        self.sessions = dependencies.sessions
        self.unit_of_work_factory = dependencies.unit_of_work_factory
        self.audit = dependencies.audit

    def get(self, actor_id: int) -> AccountSnapshot:
        account = self.users.get(actor_id)
        if account is None:
            raise LookupError(actor_id)
        return account

    def update(self, actor_id: int, request: ProfileUpdateRequest) -> AccountSnapshot:
        with self.unit_of_work_factory():
            before = self.users.get_for_update(actor_id)
            if before is None:
                raise LookupError(actor_id)
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
            self._record_profile(ProfileEvidence(before, saved, sorted(request.provided_fields)))
            return saved

    def change_password(self, actor_id: int, request: PasswordChangeRequest) -> IssuedSession:
        with self.unit_of_work_factory():
            account = self.users.get_for_update(actor_id)
            if account is None:
                raise LookupError(actor_id)
            if not self.passwords.verify(
                self.users.password_hash(actor_id), request.current_password
            ):
                raise ValueError("current_password")
            self.passwords.validate(account.username, request.new_password)
            self.users.set_password(
                actor_id,
                self.passwords.encode(request.new_password),
                must_change=False,
            )
            revoked = self.sessions.revoke_all(actor_id, RevocationReason.PASSWORD_CHANGE)
            self._record_password(actor_id, revoked)
            return self.sessions.issue(actor_id)

    def _record_profile(self, evidence: ProfileEvidence) -> None:
        actor_id = evidence.after.id
        old = {field: getattr(evidence.before, field) for field in evidence.changed_fields}
        new = {field: getattr(evidence.after, field) for field in evidence.changed_fields}
        self.audit.append_audit_entry(
            AuditEntry(
                actor_id,
                AuditAction.USER_PROFILE_UPDATED,
                "User",
                str(actor_id),
                old,
                new,
            )
        )
        self.audit.append_outbox_event(
            OutboxRecord(
                IdentityEventType.USER_PROFILE_UPDATED,
                "User",
                str(actor_id),
                {"user_id": actor_id, "changed_fields": evidence.changed_fields},
            )
        )

    def _record_password(self, actor_id: int, revoked: int) -> None:
        self._record_password_change(actor_id)
        if revoked > 0:
            self._record_password_revocation(actor_id, revoked)

    def _record_password_change(self, actor_id: int) -> None:
        after = {"must_change_password": False}
        self.audit.append_audit_entry(
            AuditEntry(
                actor_id,
                AuditAction.USER_PASSWORD_CHANGED,
                "User",
                str(actor_id),
                {"must_change_password": True},
                after,
            )
        )
        self.audit.append_outbox_event(
            OutboxRecord(
                IdentityEventType.USER_PASSWORD_CHANGED,
                "User",
                str(actor_id),
                {"user_id": actor_id, **after},
            )
        )

    def _record_password_revocation(self, actor_id: int, revoked: int) -> None:
        before, after, event_payload = self._password_revocation_payloads(actor_id, revoked)
        self.audit.append_audit_entry(
            AuditEntry(
                actor_id,
                AuditAction.SESSIONS_REVOKED,
                "User",
                str(actor_id),
                before,
                after,
            )
        )
        self.audit.append_outbox_event(
            OutboxRecord(
                IdentityEventType.SESSIONS_REVOKED,
                "User",
                str(actor_id),
                event_payload,
            )
        )

    @staticmethod
    def _password_revocation_payloads(
        actor_id: int, revoked: int
    ) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        shared: dict[str, object] = {
            "reason": RevocationReason.PASSWORD_CHANGE.value,
            "revoked_refresh_session_count": revoked,
        }
        return (
            {"active_refresh_sessions": revoked},
            {"active_refresh_sessions": 0, **shared},
            {"user_id": actor_id, **shared},
        )
