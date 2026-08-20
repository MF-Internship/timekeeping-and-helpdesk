from datetime import date

import pytest

from tasks.models import TaskUpdate
from tests.integration.api.identity.helpers import api_client
from tests.integration.api.tasks.helpers import create_task, task_client

pytestmark = pytest.mark.django_db


def test_detail_scope_allows_participants_manager_and_read_only_leader() -> None:
    owner_client, owner = task_client("HELPDESK", "task-detail-owner")
    assignee_client, assignee = task_client("HELPDESK", "task-detail-assignee")
    outsider_client, _ = task_client("HELPDESK", "task-detail-outsider")
    manager_client, _ = task_client("MANAGER", "task-detail-manager")
    leader_client, _ = task_client("LEADER", "task-detail-leader")
    task = create_task(owner, assignee, assigned_date=date.today())
    assert owner_client.get(f"/api/v1/tasks/{task.pk}/").status_code == 200
    assert assignee_client.get(f"/api/v1/tasks/{task.pk}/").status_code == 200
    assert outsider_client.get(f"/api/v1/tasks/{task.pk}/").status_code == 404
    assert manager_client.get(f"/api/v1/tasks/{task.pk}/").status_code == 200
    transitioned = manager_client.post(
        f"/api/v1/tasks/{task.pk}/status",
        {"status": "IN_PROGRESS"},
        format="json",
    )
    assert transitioned.status_code == 200
    leader = leader_client.get(f"/api/v1/tasks/{task.pk}/")
    assert leader.status_code == 200
    assert {"username", "is_active"}.isdisjoint(leader.json()["created_by"])


def test_string_identifier_and_denied_mutations_have_no_side_effects() -> None:
    leader_client, leader = task_client("LEADER", "task-scope-readonly")
    task = create_task(leader, assigned_date=date.today())
    assert leader_client.get("/api/v1/tasks/not-an-integer/").status_code == 404
    assert leader_client.get(f"/api/v1/tasks/{task.pk + 9999}/").status_code == 404
    assert api_client().get(f"/api/v1/tasks/{task.pk}/").status_code == 401
    response = leader_client.patch(f"/api/v1/tasks/{task.pk}/", {"unexpected": {}}, format="json")
    assert response.status_code == 403
    assert not TaskUpdate.objects.exists()
