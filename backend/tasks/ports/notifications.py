from __future__ import annotations

from datetime import datetime
from typing import Protocol


class TaskNotificationSink(Protocol):
    def record_assignments(
        self,
        task_id: int,
        assignee_ids: tuple[int, ...],
        assignment_version: int,
    ) -> None: ...

    def suppress_removed_assignments(self, task_id: int, assignee_ids: tuple[int, ...]) -> None: ...

    def suppress_task_reminders(self, task_id: int) -> None: ...

    def record_multi_assignee_completion(
        self,
        task_id: int,
        recipient_ids: tuple[int, ...],
        occurred_at: datetime,
    ) -> None: ...


class NoopTaskNotificationSink:
    def record_assignments(
        self,
        task_id: int,
        assignee_ids: tuple[int, ...],
        assignment_version: int,
    ) -> None:
        return None

    def suppress_removed_assignments(self, task_id: int, assignee_ids: tuple[int, ...]) -> None:
        return None

    def suppress_task_reminders(self, task_id: int) -> None:
        return None

    def record_multi_assignee_completion(
        self,
        task_id: int,
        recipient_ids: tuple[int, ...],
        occurred_at: datetime,
    ) -> None:
        return None
