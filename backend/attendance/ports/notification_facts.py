from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AttendanceNotificationCandidate:
    session_id: int
    recipient_id: int
    reminder_at: datetime
    is_open: bool


@dataclass(frozen=True, slots=True)
class AttendanceNotificationTarget:
    destination: str
    target_id: int | None


class AttendanceNotificationFacts(Protocol):
    def due_open_sessions(self, now: datetime) -> tuple[AttendanceNotificationCandidate, ...]: ...

    def revalidate(self, session_id: int, recipient_id: int, event_type: str) -> bool: ...

    def resolve(self, actor_id: int, session_id: int) -> AttendanceNotificationTarget | None: ...
