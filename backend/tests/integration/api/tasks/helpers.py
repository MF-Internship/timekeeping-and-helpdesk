from __future__ import annotations

from datetime import date

from django.utils import timezone
from rest_framework.test import APIClient

from identity.models import User
from tasks.domain.tasks import CompletionMethod
from tasks.models import Task, TaskAssignee
from tests.integration.api.identity.helpers import authenticated_client, create_user


def task_client(role: str, username: str) -> tuple[APIClient, User]:
    user = create_user(username, role)
    return authenticated_client(user), user


def create_task(
    creator: User,
    *assignees: User,
    assigned_date: date,
    title: str = "Task",
    status: str = "TODO",
) -> Task:
    completed = status == "COMPLETED"
    task = Task.objects.create(
        title=title,
        created_by=creator,
        assigned_date=assigned_date,
        status=status,
        block_reason="Blocked for test" if status == "BLOCKED" else None,
        completed_by=creator if completed else None,
        completed_at=timezone.now() if completed else None,
        completion_method=CompletionMethod.MANAGER_OVERRIDE.value if completed else None,
        completion_note="Completed for test" if completed else None,
    )
    TaskAssignee.objects.bulk_create(
        [TaskAssignee(task=task, user=user, assigned_at=timezone.now()) for user in assignees]
    )
    return task
