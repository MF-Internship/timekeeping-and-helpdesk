from __future__ import annotations

from datetime import datetime, time

from attendance.adapters.notification_facts import DjangoAttendanceNotificationFacts
from identity.adapters.notification_facts import DjangoAccountNotificationFacts
from identity.application.authorization import DjangoAuthorizationGateway
from identity.domain.authorization import PermissionAction
from locations.models import Config
from notifications.application.dto import (
    AccountEligibility,
    AttendanceCandidate,
    TargetResolution,
    TaskCandidate,
)
from notifications.application.subscriptions import SubscriptionService
from tasks.adapters.notification_facts import DjangoTaskNotificationFacts
from tasks.ports.notification_facts import TaskNotificationCandidate


class DjangoNotificationAuthorization:
    def __init__(self) -> None:
        self._gateway = DjangoAuthorizationGateway()

    def authorize(self, actor_id: int, action: object) -> object:
        return self._gateway.authorize(actor_id, PermissionAction(str(action)))


class DjangoNotificationAccountFacts:
    def __init__(self) -> None:
        self._source = DjangoAccountNotificationFacts()

    def get_eligibility(self, user_id: int) -> AccountEligibility | None:
        value = self._source.get_eligibility(user_id)
        return AccountEligibility(value.user_id, value.is_active) if value else None


class DjangoNotificationTaskFacts:
    def __init__(self, source: DjangoTaskNotificationFacts) -> None:
        self._source = source

    def due_upcoming(self, now: datetime) -> tuple[TaskCandidate, ...]:
        return tuple(_task_candidate(value) for value in self._source.due_upcoming(now))

    def due_overdue(self, now: datetime) -> tuple[TaskCandidate, ...]:
        return tuple(_task_candidate(value) for value in self._source.due_overdue(now))

    def revalidate(self, task_id: int, recipient_id: int, event_type: str) -> bool:
        return self._source.revalidate(task_id, recipient_id, event_type)

    def resolve(self, actor_id: int, task_id: int) -> TargetResolution | None:
        value = self._source.resolve(actor_id, task_id)
        return TargetResolution("TASK", value.target_id) if value else None


class DjangoNotificationAttendanceFacts:
    def __init__(self, source: DjangoAttendanceNotificationFacts) -> None:
        self._source = source

    def due_open_sessions(self, now: datetime) -> tuple[AttendanceCandidate, ...]:
        return tuple(
            AttendanceCandidate(
                value.session_id, value.recipient_id, value.reminder_at, value.is_open
            )
            for value in self._source.due_open_sessions(now)
        )

    def revalidate(self, session_id: int, recipient_id: int, event_type: str) -> bool:
        return self._source.revalidate(session_id, recipient_id, event_type)

    def resolve(self, actor_id: int, session_id: int) -> TargetResolution | None:
        value = self._source.resolve(actor_id, session_id)
        return TargetResolution("ATTENDANCE", None) if value else None


class DjangoPushSubscriptionRevoker:
    def __init__(self, subscriptions: SubscriptionService) -> None:
        self._subscriptions = subscriptions

    def revoke_all(self, user_id: int, reason: object) -> None:
        self._subscriptions.revoke_all(user_id, reason)


def notification_shift_end() -> time:
    value = Config.objects.only("shift_end").get(pk=1).shift_end
    if not isinstance(value, time):
        raise TypeError("Config.shift_end must be a time")
    return value


def _task_candidate(value: TaskNotificationCandidate) -> TaskCandidate:
    return TaskCandidate(
        value.task_id,
        value.recipient_ids,
        value.assigned_date,
        value.assignment_version,
        value.is_completed,
    )
