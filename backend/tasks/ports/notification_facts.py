from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TaskNotificationCandidate:
    task_id: int
    recipient_ids: tuple[int, ...]
    assigned_date: date
    assignment_version: int
    is_completed: bool


@dataclass(frozen=True, slots=True)
class TaskNotificationTarget:
    destination: str
    target_id: int | None


class TaskNotificationFacts(Protocol):
    def due_upcoming(self, now: datetime) -> tuple[TaskNotificationCandidate, ...]: ...

    def due_overdue(self, now: datetime) -> tuple[TaskNotificationCandidate, ...]: ...

    def revalidate(self, task_id: int, recipient_id: int, event_type: str) -> bool: ...

    def resolve(self, actor_id: int, task_id: int) -> TaskNotificationTarget | None: ...
