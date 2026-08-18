from __future__ import annotations

from audit.ports.recording import AuditAction, AuditEntry, IdentityEventType, OutboxRecord
from core.error_codes import (
    ACCOUNT_INACTIVE,
    INVALID_CREDENTIALS,
    INVALID_TOKEN,
    PASSWORD_CHANGE_REQUIRED,
)
from core.errors import IdentityAPIError
from identity.application.dependencies import IdentityDependencies
from identity.domain.accounts import AccountSnapshot
from identity.domain.authorization import effective_capabilities
from identity.ports.sessions import IssuedSession, RevocationReason


class AuthenticationService:
    def __init__(self, dependencies: IdentityDependencies) -> None:
        self.users = dependencies.users
        self.passwords = dependencies.passwords
        self.sessions = dependencies.sessions
        self.unit_of_work_factory = dependencies.unit_of_work_factory
        self.audit = dependencies.audit

    def login(
        self, username: str, password: str
    ) -> tuple[IssuedSession, AccountSnapshot, tuple[str, ...]]:
        with self.unit_of_work_factory():
            account = self.users.get_by_username_for_update(username.strip())
            if account is None or not account.is_active:
                raise IdentityAPIError(INVALID_CREDENTIALS, status_code=401)
            encoded = self.users.password_hash(account.id)
            if not self.passwords.verify(encoded, password):
                raise IdentityAPIError(INVALID_CREDENTIALS, status_code=401)
            issued = self.sessions.issue(account.id)
            self.users.record_login(account.id)
        capabilities = tuple(
            sorted(action.value for action in effective_capabilities(account.role))
        )
        return issued, account, capabilities

    def refresh(self, raw_refresh: str) -> IssuedSession:
        try:
            owner_id = self.sessions.refresh_owner(raw_refresh)
        except ValueError as error:
            raise IdentityAPIError(INVALID_TOKEN, status_code=401) from error
        with self.unit_of_work_factory():
            account = self.users.get_for_update(owner_id)
            if account is None:
                raise IdentityAPIError(INVALID_TOKEN, status_code=401)
            if not account.is_active:
                raise IdentityAPIError(ACCOUNT_INACTIVE, status_code=401)
            if account.must_change_password:
                raise IdentityAPIError(PASSWORD_CHANGE_REQUIRED, status_code=403)
            try:
                return self.sessions.rotate(raw_refresh)
            except ValueError as error:
                raise IdentityAPIError(INVALID_TOKEN, status_code=401) from error

    def logout(self, actor_id: int) -> None:
        with self.unit_of_work_factory():
            account = self.users.get_for_update(actor_id)
            if account is None or not account.is_active:
                raise IdentityAPIError(ACCOUNT_INACTIVE, status_code=401)
            if account.must_change_password:
                raise IdentityAPIError(PASSWORD_CHANGE_REQUIRED, status_code=403)
            count = self.sessions.revoke_all(actor_id, RevocationReason.LOGOUT)
            if count > 0:
                self._record_revocation(actor_id, count, RevocationReason.LOGOUT)

    def _record_revocation(self, actor_id: int, count: int, reason: RevocationReason) -> None:
        before = {"active_refresh_sessions": count}
        after = {
            "active_refresh_sessions": 0,
            "reason": reason.value,
            "revoked_refresh_session_count": count,
        }
        event_payload = {
            "user_id": actor_id,
            "reason": reason.value,
            "revoked_refresh_session_count": count,
        }
        self.audit.append_audit_entry(
            AuditEntry(
                actor_id=actor_id,
                action=AuditAction.SESSIONS_REVOKED,
                target_type="User",
                target_id=str(actor_id),
                before=before,
                after=after,
            )
        )
        self.audit.append_outbox_event(
            OutboxRecord(
                event_type=IdentityEventType.SESSIONS_REVOKED,
                aggregate_type="User",
                aggregate_id=str(actor_id),
                payload=event_payload,
            )
        )
