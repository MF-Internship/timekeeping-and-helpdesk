from __future__ import annotations

from datetime import datetime

from notifications.application.dependencies import NotificationDependencies
from notifications.application.dto import DeliveryPlan, StoredNotification
from notifications.domain.delivery import expires_at, next_delivery_time
from notifications.domain.events import (
    NotificationEventType,
    NotificationTargetType,
    Occurrence,
)


class OccurrenceService:
    def __init__(self, dependencies: NotificationDependencies) -> None:
        self._dependencies = dependencies

    def record(self, occurrence: Occurrence) -> StoredNotification | None:
        account_port = self._dependencies.accounts
        if account_port is not None:
            eligibility = account_port.get_eligibility(occurrence.recipient_id)
            if eligibility is None or not eligibility.is_active:
                return None
        stored, _ = self._dependencies.notifications.insert_occurrence(occurrence)
        subscriptions = self._dependencies.subscriptions.active_for_user(occurrence.recipient_id)
        for subscription in subscriptions:
            self._dependencies.deliveries.materialize(
                DeliveryPlan(
                    stored.id,
                    subscription.id,
                    next_delivery_time(occurrence.occurred_at),
                    expires_at(occurrence.occurred_at),
                    occurrence.collapse_key,
                )
            )
        return stored

    def record_atomic(self, occurrence: Occurrence) -> StoredNotification | None:
        with self._dependencies.unit_of_work_factory():
            return self.record(occurrence)

    def suppress(
        self, target_type: str, target_id: int, recipient_ids: tuple[int, ...] = ()
    ) -> int:
        return int(
            self._dependencies.deliveries.suppress_target(target_type, target_id, recipient_ids)
        )

    def record_assignments(
        self,
        task_id: int,
        assignee_ids: tuple[int, ...],
        assignment_version: int,
    ) -> None:
        occurred_at = self._dependencies.clock.now()
        for recipient_id in assignee_ids:
            self.record(
                Occurrence(
                    NotificationEventType.TASK_ASSIGNED,
                    NotificationTargetType.TASK,
                    task_id,
                    recipient_id,
                    occurred_at,
                    assignment_version=assignment_version,
                )
            )

    def suppress_removed_assignments(self, task_id: int, assignee_ids: tuple[int, ...]) -> None:
        self.suppress(NotificationTargetType.TASK.value, task_id, assignee_ids)

    def suppress_task_reminders(self, task_id: int) -> None:
        self.suppress(NotificationTargetType.TASK.value, task_id)

    def record_multi_assignee_completion(
        self,
        task_id: int,
        recipient_ids: tuple[int, ...],
        occurred_at: datetime,
    ) -> None:
        for recipient_id in recipient_ids:
            self.record(
                Occurrence(
                    NotificationEventType.MULTI_ASSIGNEE_TASK_COMPLETED,
                    NotificationTargetType.TASK,
                    task_id,
                    recipient_id,
                    occurred_at,
                )
            )

    def suppress_open_session_reminder(self, session_id: int, owner_id: int) -> None:
        self.suppress(NotificationTargetType.ATTENDANCE_SESSION.value, session_id, (owner_id,))
