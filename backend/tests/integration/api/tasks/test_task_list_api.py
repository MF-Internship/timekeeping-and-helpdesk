from datetime import timedelta

import pytest
from django.utils import timezone

from tasks.models import Task, TaskAssignee, TaskUpdate
from tests.integration.api.tasks.helpers import create_task, task_client

pytestmark = pytest.mark.django_db


def test_list_groups_are_exclusive_ordered_private_and_read_only() -> None:
    client, actor = task_client("HELPDESK", "task-list-self")
    today = timezone.localdate()
    create_task(actor, actor, assigned_date=today - timedelta(days=2), title="late")
    create_task(actor, actor, assigned_date=today, title="today")
    create_task(actor, actor, assigned_date=today + timedelta(days=1), title="next")
    create_task(
        actor, actor, assigned_date=today - timedelta(days=9), title="done", status="COMPLETED"
    )
    before = (Task.objects.count(), TaskAssignee.objects.count(), TaskUpdate.objects.count())
    response = client.get("/api/v1/tasks/")
    assert response.status_code == 200, response.json()
    assert list(response.json()) == ["business_date", "overdue", "today", "upcoming", "completed"]
    assert [item["title"] for item in response.json()["overdue"]] == ["late"]
    assert response.json()["overdue"][0]["overdue_days"] == 2
    assert response.json()["completed"][0]["overdue_days"] is None
    assert "private" in response["Cache-Control"] and "no-store" in response["Cache-Control"]
    assert before == (
        Task.objects.count(),
        TaskAssignee.objects.count(),
        TaskUpdate.objects.count(),
    )


def test_list_rejects_unknown_query_and_deduplicates_creator_assignee_scope() -> None:
    client, actor = task_client("HELPDESK", "task-list-deduplicate")
    task = create_task(actor, actor, assigned_date=timezone.localdate())
    response = client.get("/api/v1/tasks/")
    ids = [
        item["id"]
        for group in ("overdue", "today", "upcoming", "completed")
        for item in response.json()[group]
    ]
    assert ids.count(task.pk) == 1
    assert client.get("/api/v1/tasks/?status=TODO").status_code == 400
