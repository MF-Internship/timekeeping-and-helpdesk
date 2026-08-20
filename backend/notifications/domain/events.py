from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class NotificationEventType(StrEnum):
    TASK_ASSIGNED = "TASK_ASSIGNED"
    TASK_UPCOMING = "TASK_UPCOMING"
    TASK_OVERDUE = "TASK_OVERDUE"
    ATTENDANCE_SESSION_OPEN_NEAR_SHIFT_END = "ATTENDANCE_SESSION_OPEN_NEAR_SHIFT_END"
    MULTI_ASSIGNEE_TASK_COMPLETED = "MULTI_ASSIGNEE_TASK_COMPLETED"


class NotificationTargetType(StrEnum):
    TASK = "TASK"
    ATTENDANCE_SESSION = "ATTENDANCE_SESSION"


SAFE_TITLES = {
    NotificationEventType.TASK_ASSIGNED: "Bạn có công việc mới được giao",
    NotificationEventType.TASK_UPCOMING: "Công việc sắp đến hạn thực hiện",
    NotificationEventType.TASK_OVERDUE: "Công việc đã quá hạn",
    NotificationEventType.ATTENDANCE_SESSION_OPEN_NEAR_SHIFT_END: "Phiên chấm công vẫn đang mở",
    NotificationEventType.MULTI_ASSIGNEE_TASK_COMPLETED: "Công việc chung đã hoàn thành",
}


@dataclass(frozen=True, slots=True)
class Occurrence:
    event_type: NotificationEventType
    target_type: NotificationTargetType
    target_id: int
    recipient_id: int
    occurred_at: datetime
    assignment_version: int | None = None
    assigned_date: date | None = None
    occurrence_date: date | None = None

    def __post_init__(self) -> None:
        if self.target_id < 1 or self.recipient_id < 1:
            raise ValueError("target and recipient identifiers must be positive")
        if self.event_type is NotificationEventType.TASK_ASSIGNED:
            if self.assignment_version is None or self.assignment_version < 1:
                raise ValueError("assignment_version is required")
        elif self.event_type is NotificationEventType.TASK_UPCOMING:
            if self.assigned_date is None:
                raise ValueError("assigned_date is required")
        elif self.event_type is NotificationEventType.TASK_OVERDUE and self.occurrence_date is None:
            raise ValueError("occurrence_date is required")

    @property
    def title(self) -> str:
        return SAFE_TITLES[self.event_type]

    @property
    def dedupe_key(self) -> str:
        parts: list[str | int] = ["v1", self.event_type.value, self.target_id, self.recipient_id]
        if self.event_type is NotificationEventType.TASK_ASSIGNED:
            parts.append(self.assignment_version or 0)
        elif self.event_type is NotificationEventType.TASK_UPCOMING:
            parts.append((self.assigned_date or date.min).isoformat())
        elif self.event_type is NotificationEventType.TASK_OVERDUE:
            parts.append((self.occurrence_date or date.min).isoformat())
        return ":".join(str(part) for part in parts)

    @property
    def collapse_key(self) -> str:
        return collapse_key(self.dedupe_key)


def collapse_key(dedupe_key: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_-]", "_", dedupe_key)
    if len(normalized) <= 32:
        return normalized
    return f"n_{hashlib.sha256(dedupe_key.encode()).hexdigest()[:30]}"
