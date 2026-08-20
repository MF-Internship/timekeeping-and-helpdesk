from datetime import date

import pytest

from tasks.models import TaskAssignee
from tests.integration.api.identity.helpers import create_user
from tests.integration.api.tasks.helpers import create_task, task_client

pytestmark = pytest.mark.django_db


def test_manager_replaces_desired_set_and_assigned_date_is_immutable() -> None:
    client, manager = task_client("MANAGER", "task-update-manager")
    retained = create_user("task-update-retained")
    removed = create_user("task-update-removed")
    added = create_user("task-update-added")
    task = create_task(manager, retained, removed, assigned_date=date(2026, 8, 1))
    response = client.patch(
        f"/api/v1/tasks/{task.pk}/",
        {"title": "Changed", "assignee_ids": [added.pk, retained.pk, added.pk]},
        format="json",
    )
    assert response.status_code == 200, response.json()
    task.refresh_from_db()
    assert task.assigned_date == date(2026, 8, 1)
    assert set(TaskAssignee.objects.filter(task=task).values_list("user_id", flat=True)) == {
        retained.pk,
        added.pk,
    }


def test_retained_inactive_is_allowed_but_readding_it_is_rejected() -> None:
    client, manager = task_client("MANAGER", "task-update-history-manager")
    historical = create_user("task-update-historical")
    replacement = create_user("task-update-replacement")
    task = create_task(manager, historical, assigned_date=date.today())
    historical.is_active = False
    historical.save(update_fields=["is_active"])
    metadata = client.patch(f"/api/v1/tasks/{task.pk}/", {"description": "kept"}, format="json")
    assert metadata.status_code == 200
    removed = client.patch(
        f"/api/v1/tasks/{task.pk}/", {"assignee_ids": [replacement.pk]}, format="json"
    )
    assert removed.status_code == 200
    rejected = client.patch(
        f"/api/v1/tasks/{task.pk}/",
        {"assignee_ids": [replacement.pk, historical.pk]},
        format="json",
    )
    assert rejected.status_code == 422
    assert rejected.json()["details"]["assignee_ids"] == [historical.pk]


def test_helpdesk_cannot_manage_assignees_and_server_fields_are_rejected() -> None:
    client, actor = task_client("HELPDESK", "task-update-self")
    other = create_user("task-update-other")
    task = create_task(actor, actor, assigned_date=date.today())
    assert client.patch(
        f"/api/v1/tasks/{task.pk}/", {"assignee_ids": [actor.pk, other.pk]}, format="json"
    ).status_code in {400, 403}
    assert (
        client.patch(
            f"/api/v1/tasks/{task.pk}/", {"assigned_date": "2026-09-01"}, format="json"
        ).status_code
        == 400
    )
