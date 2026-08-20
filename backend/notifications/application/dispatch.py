from __future__ import annotations

from datetime import datetime

from notifications.application.dependencies import NotificationDependencies
from notifications.application.dto import TaskCandidate
from notifications.application.occurrences import OccurrenceService
from notifications.domain.delivery import LOCAL_ZONE
from notifications.domain.events import NotificationEventType, NotificationTargetType, Occurrence


class OccurrenceDispatcher:
    def __init__(
        self, dependencies: NotificationDependencies, occurrences: OccurrenceService
    ) -> None:
        self._dependencies = dependencies
        self._occurrences = occurrences

    def dispatch(self) -> int:
        now = self._dependencies.clock.now()
        count = 0
        if self._dependencies.tasks is not None:
            count += self._task_candidates(
                self._dependencies.tasks.due_upcoming(now), NotificationEventType.TASK_UPCOMING, now
            )
            count += self._task_candidates(
                self._dependencies.tasks.due_overdue(now), NotificationEventType.TASK_OVERDUE, now
            )
        return count + self._attendance_candidates(now)

    def _attendance_candidates(self, now: datetime) -> int:
        facts = self._dependencies.attendance
        if facts is None:
            return 0
        occurrences = (
            Occurrence(
                NotificationEventType.ATTENDANCE_SESSION_OPEN_NEAR_SHIFT_END,
                NotificationTargetType.ATTENDANCE_SESSION,
                item.session_id,
                item.recipient_id,
                item.reminder_at,
            )
            for item in facts.due_open_sessions(now)
            if item.is_open
        )
        return sum(self._record_if_valid(item) for item in occurrences)

    def _task_candidates(
        self,
        candidates: tuple[TaskCandidate, ...],
        event_type: NotificationEventType,
        now: datetime,
    ) -> int:
        count = 0
        for raw in candidates:
            candidate = raw
            if candidate.is_completed:
                continue
            for recipient_id in candidate.recipient_ids:
                occurrence = _task_occurrence(candidate, recipient_id, event_type, now)
                count += self._record_if_valid(occurrence)
        return count

    def _record_if_valid(self, occurrence: Occurrence) -> int:
        facts = (
            self._dependencies.tasks
            if occurrence.target_type is NotificationTargetType.TASK
            else self._dependencies.attendance
        )
        if facts is None:
            return 0
        with self._dependencies.unit_of_work_factory():
            valid = facts.revalidate(
                occurrence.target_id,
                occurrence.recipient_id,
                occurrence.event_type.value,
            )
            return int(bool(valid and self._occurrences.record(occurrence)))


def _task_occurrence(
    candidate: TaskCandidate,
    recipient_id: int,
    event_type: NotificationEventType,
    now: datetime,
) -> Occurrence:
    return Occurrence(
        event_type,
        NotificationTargetType.TASK,
        candidate.task_id,
        recipient_id,
        now,
        assigned_date=(
            candidate.assigned_date if event_type is NotificationEventType.TASK_UPCOMING else None
        ),
        occurrence_date=(
            now.astimezone(LOCAL_ZONE).date()
            if event_type is NotificationEventType.TASK_OVERDUE
            else None
        ),
    )
