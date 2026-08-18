from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from core.event_payload import validate_event_payload


class AuditAction(StrEnum):
    USER_CREATED = "identity.user.created"
    USER_PROFILE_UPDATED = "identity.user.profile_updated"
    USER_ROLE_CHANGED = "identity.user.role_changed"
    USER_STATUS_CHANGED = "identity.user.status_changed"
    USER_PASSWORD_RESET = "identity.user.password_reset"
    USER_PASSWORD_CHANGED = "identity.user.password_changed"
    SESSIONS_REVOKED = "identity.sessions.revoked"


class IdentityEventType(StrEnum):
    USER_CREATED = "identity.user.created"
    USER_PROFILE_UPDATED = "identity.user.profile_updated"
    USER_ROLE_CHANGED = "identity.user.role_changed"
    USER_STATUS_CHANGED = "identity.user.status_changed"
    USER_PASSWORD_RESET = "identity.user.password_reset"
    USER_PASSWORD_CHANGED = "identity.user.password_changed"
    SESSIONS_REVOKED = "identity.sessions.revoked"


@dataclass(frozen=True, slots=True)
class AuditEntry:
    actor_id: int
    action: AuditAction
    target_type: str
    target_id: str
    before: dict[str, Any]
    after: dict[str, Any]

    def __post_init__(self) -> None:
        validate_event_payload(self.before)
        validate_event_payload(self.after)


@dataclass(frozen=True, slots=True)
class OutboxRecord:
    event_type: IdentityEventType
    aggregate_type: str
    aggregate_id: str
    payload: dict[str, Any]
    schema_version: int = 1

    def __post_init__(self) -> None:
        validate_event_payload(self.payload)
