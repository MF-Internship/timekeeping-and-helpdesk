from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.db.models import Prefetch, QuerySet

from tasks.domain.tasks import TaskStatus
from tasks.models import Task, TaskAssignee
from tasks.ports.authorization import TaskAuthorization, TaskReadScope
from tasks.ports.notification_facts import TaskNotificationCandidate, TaskNotificationTarget

LOCAL_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")
UPCOMING_TIME = time(17, 0)
OVERDUE_TIME = time(8, 0)


class DjangoTaskNotificationFacts:
    def __init__(self, authorization: TaskAuthorization) -> None:
        self._authorization = authorization

    def due_upcoming(self, now: datetime) -> tuple[TaskNotificationCandidate, ...]:
        local_now = now.astimezone(LOCAL_TIMEZONE)
        if local_now.time() < UPCOMING_TIME:
            return ()
        return self._candidates(assigned_date=local_now.date() + timedelta(days=1))

    def due_overdue(self, now: datetime) -> tuple[TaskNotificationCandidate, ...]:
        local_now = now.astimezone(LOCAL_TIMEZONE)
        if local_now.time() < OVERDUE_TIME:
            return ()
        return self._candidates(assigned_date__lt=local_now.date())

    def revalidate(self, task_id: int, recipient_id: int, event_type: str) -> bool:
        task = (
            Task.objects.select_for_update()
            .filter(pk=task_id, deleted_at__isnull=True)
            .first()
        )
        if task is None:
            return False
        eligible = _eligible_assignees(task_id).filter(user_id=recipient_id).exists()
        if not eligible:
            return False
        if event_type in {"TASK_UPCOMING", "TASK_OVERDUE"}:
            return task.status != TaskStatus.COMPLETED.value
        if event_type == "MULTI_ASSIGNEE_TASK_COMPLETED":
            return (
                task.status == TaskStatus.COMPLETED.value
                and task.completed_by_id != recipient_id  # type: ignore[attr-defined]
            )
        return event_type == "TASK_ASSIGNED"

    def resolve(self, actor_id: int, task_id: int) -> TaskNotificationTarget | None:
        scope = self._authorization.authorize_read(actor_id)
        task = Task.objects.filter(pk=task_id, deleted_at__isnull=True).first()
        if task is None:
            return None
        if scope is TaskReadScope.SELF and not (
            task.created_by_id == actor_id  # type: ignore[attr-defined]
            or TaskAssignee.objects.filter(task_id=task_id, user_id=actor_id).exists()
        ):
            return None
        return TaskNotificationTarget("tasks", task_id)

    @staticmethod
    def _candidates(**filters: object) -> tuple[TaskNotificationCandidate, ...]:
        assignees = Prefetch(
            "assignee_links",
            queryset=_eligible_assignees().order_by("user_id"),
            to_attr="notification_assignees",
        )
        tasks = (
            Task.objects.filter(
                deleted_at__isnull=True,
                status__in=(
                    TaskStatus.TODO.value,
                    TaskStatus.IN_PROGRESS.value,
                    TaskStatus.BLOCKED.value,
                ),
                **filters,
            )
            .prefetch_related(assignees)
            .order_by("id")
        )
        return tuple(_candidate(task) for task in tasks)


def _eligible_assignees(task_id: int | None = None) -> QuerySet[TaskAssignee]:
    query = TaskAssignee.objects.filter(user__is_active=True, user__role="HELPDESK")
    return query.filter(task_id=task_id) if task_id is not None else query


def _candidate(task: Task) -> TaskNotificationCandidate:
    links = task.notification_assignees  # type: ignore[attr-defined]
    return TaskNotificationCandidate(
        task.pk,
        tuple(link.user_id for link in links),
        task.assigned_date,
        task.assignment_version,
        task.status == TaskStatus.COMPLETED.value,
    )
