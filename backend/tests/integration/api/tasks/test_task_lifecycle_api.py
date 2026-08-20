from datetime import date

import pytest

from audit.models import AuditLog, OutboxEvent
from tasks.models import TaskUpdate
from tests.integration.api.tasks.helpers import create_task, task_client

pytestmark = pytest.mark.django_db


def test_self_status_success_block_reason_and_same_state_noop() -> None:
    client, actor = task_client("HELPDESK", "task-lifecycle-self")
    task = create_task(actor, actor, assigned_date=date.today())
    started = client.post(
        f"/api/v1/tasks/{task.pk}/status", {"status": "IN_PROGRESS"}, format="json"
    )
    assert started.status_code == 200, started.json()
    blocked = client.post(
        f"/api/v1/tasks/{task.pk}/status",
        {"status": "BLOCKED", "block_reason": " dependency "},
        format="json",
    )
    assert blocked.status_code == 200 and blocked.json()["block_reason"] == "dependency"
    count = TaskUpdate.objects.count()
    noop = client.post(f"/api/v1/tasks/{task.pk}/status", {"status": "BLOCKED"}, format="json")
    assert noop.status_code == 200 and TaskUpdate.objects.count() == count
    assert AuditLog.objects.count() == OutboxEvent.objects.count() == 0


def test_lifecycle_authorization_and_validation_precedence() -> None:
    owner_client, owner = task_client("HELPDESK", "task-scope-owner")
    outsider_client, _ = task_client("HELPDESK", "task-scope-outsider")
    leader_client, _ = task_client("LEADER", "task-scope-leader")
    task = create_task(owner, owner, assigned_date=date.today())
    malformed = {"status": "NOT_A_STATUS"}
    assert (
        leader_client.post(f"/api/v1/tasks/{task.pk}/status", malformed, format="json").status_code
        == 403
    )
    outsider = outsider_client.post(f"/api/v1/tasks/{task.pk}/status", malformed, format="json")
    assert outsider.status_code == 400
    task.refresh_from_db()
    assert task.status == "TODO" and not TaskUpdate.objects.exists()


def test_manager_override_is_exact_and_completed_task_is_frozen() -> None:
    manager_client, manager = task_client("MANAGER", "task-override-manager")
    helpdesk_client, helpdesk = task_client("HELPDESK", "task-override-helpdesk")
    task = create_task(helpdesk, helpdesk, assigned_date=date.today(), status="IN_PROGRESS")
    denied = helpdesk_client.post(
        f"/api/v1/tasks/{task.pk}/complete-override", {"completion_note": "done"}, format="json"
    )
    assert denied.status_code == 403
    complete = manager_client.post(
        f"/api/v1/tasks/{task.pk}/complete-override",
        {"completion_note": "Manager accepted"},
        format="json",
    )
    assert complete.status_code == 200, complete.json()
    assert complete.json()["status"] == "COMPLETED"
    assert AuditLog.objects.filter(actor=manager).count() == 1
    retry = manager_client.post(
        f"/api/v1/tasks/{task.pk}/complete-override", {"completion_note": "again"}, format="json"
    )
    assert retry.status_code == 409 and retry.json()["error_code"] == "TASK_ALREADY_COMPLETED"
    patch = manager_client.patch(f"/api/v1/tasks/{task.pk}/", {"title": "No"}, format="json")
    assert patch.status_code == 400
