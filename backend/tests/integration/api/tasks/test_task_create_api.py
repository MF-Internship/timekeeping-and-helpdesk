from datetime import date

import pytest

from tasks.models import Task, TaskAssignee
from tests.integration.api.identity.helpers import api_client, create_user
from tests.integration.api.tasks.helpers import task_client

pytestmark = pytest.mark.django_db


def payload(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {"title": "Planned", "assigned_date": date.today().isoformat()}
    value.update(overrides)
    return value


def test_manager_assign_only_multi_create_normalizes_duplicates() -> None:
    client, manager = task_client("MANAGER", "task-create-manager")
    first = create_user("task-assignee-first")
    second = create_user("task-assignee-second")
    response = client.post(
        "/api/v1/tasks/",
        payload(assignee_ids=[second.pk, first.pk, second.pk]),
        format="json",
    )
    assert response.status_code == 201, response.json()
    task = Task.objects.get(pk=response.json()["id"])
    assert task.created_by == manager and task.status == "TODO"
    assert list(task.assignee_links.order_by("user_id").values_list("user_id", flat=True)) == [
        first.pk,
        second.pk,
    ]


def test_helpdesk_self_create_is_sole_actor_and_rejects_assignee_field() -> None:
    client, actor = task_client("HELPDESK", "task-self-create")
    created = client.post("/api/v1/tasks/", payload(), format="json")
    assert created.status_code == 201, created.json()
    assert TaskAssignee.objects.get(task_id=created.json()["id"]).user == actor
    denied = client.post("/api/v1/tasks/", payload(assignee_ids=[actor.pk]), format="json")
    assert denied.status_code == 400
    assert Task.objects.count() == 1


def test_expected_location_accepts_free_text_outside_location_catalog() -> None:
    client, _ = task_client("HELPDESK", "task-free-location")
    created = client.post(
        "/api/v1/tasks/",
        payload(expected_location="  UBND phường 1  "),
        format="json",
    )

    assert created.status_code == 201, created.json()
    assert created.json()["expected_location"] == "UBND phường 1"
    assert Task.objects.get(pk=created.json()["id"]).expected_location_text == "UBND phường 1"


def test_create_action_authorization_precedes_malformed_dto() -> None:
    leader, _ = task_client("LEADER", "task-create-leader")
    assert leader.post("/api/v1/tasks/", {}, format="json").status_code == 403
    assert api_client().post("/api/v1/tasks/", {}, format="json").status_code == 401
    assert Task.objects.count() == 0


def test_all_mixed_ineligible_ids_fail_atomically() -> None:
    client, _ = task_client("MANAGER", "task-invalid-manager")
    inactive = create_user("task-inactive", active=False)
    wrong_role = create_user("task-wrong-role", "LEADER")
    missing = max(inactive.pk, wrong_role.pk) + 1000
    response = client.post(
        "/api/v1/tasks/",
        payload(assignee_ids=[missing, inactive.pk, wrong_role.pk, missing]),
        format="json",
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == "INACTIVE_ASSIGNEE"
    assert response.json()["details"]["assignee_ids"] == sorted(
        [inactive.pk, wrong_role.pk, missing]
    )
    assert Task.objects.count() == TaskAssignee.objects.count() == 0
