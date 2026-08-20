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
    ATTENDANCE_CHECK_IN_CREATED = "attendance.check_in.created"
    ATTENDANCE_CHECK_OUT_CREATED = "attendance.check_out.created"
    TASK_COMPLETION_OVERRIDDEN = "task.completion.overridden"
    TASK_COMPLETION_FIELD_EVIDENCE = "task.completion.field_evidence"
    TASK_SELF_DELETED = "task.self_deleted"


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
    action: StrEnum
    target_type: str
    target_id: str
    before: dict[str, Any]
    after: dict[str, Any]

    def __post_init__(self) -> None:
        validate_event_payload(self.before)
        validate_event_payload(self.after)


@dataclass(frozen=True, slots=True)
class OutboxRecord:
    event_type: StrEnum
    aggregate_type: str
    aggregate_id: str
    payload: dict[str, Any]
    schema_version: int = 1

    def __post_init__(self) -> None:
        validate_event_payload(self.payload)
