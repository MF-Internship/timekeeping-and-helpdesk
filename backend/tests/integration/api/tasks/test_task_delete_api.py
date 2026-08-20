from datetime import date

import pytest

from audit.models import AuditLog
from tasks.models import Task, TaskAssignee
from tests.integration.api.tasks.helpers import create_task, task_client

pytestmark = pytest.mark.django_db


def test_helpdesk_soft_deletes_own_self_task_and_retains_rows_and_audit() -> None:
    client, actor = task_client("HELPDESK", "task-delete-owner")
    task = create_task(actor, actor, assigned_date=date.today())

    response = client.delete(f"/api/v1/tasks/{task.pk}/")

    assert response.status_code == 204
    task.refresh_from_db()
    assert task.deleted_at is not None
    assert TaskAssignee.objects.filter(task=task, user=actor).exists()
    assert AuditLog.objects.filter(action="task.self_deleted", target_id=str(task.pk)).count() == 1
    assert client.get(f"/api/v1/tasks/{task.pk}/").status_code == 404


def test_delete_denies_manager_created_other_and_completed_tasks_without_audit() -> None:
    client, actor = task_client("HELPDESK", "task-delete-denied")
    manager_client, manager = task_client("MANAGER", "task-delete-manager")
    manager_task = create_task(manager, actor, assigned_date=date.today())
    completed = create_task(
        actor, actor, assigned_date=date.today(), title="Completed", status="COMPLETED"
    )

    assert client.delete(f"/api/v1/tasks/{manager_task.pk}/").status_code == 404
    assert client.delete(f"/api/v1/tasks/{completed.pk}/").status_code == 409
    assert manager_client.delete(f"/api/v1/tasks/{manager_task.pk}/").status_code == 403
    assert AuditLog.objects.filter(action="task.self_deleted").count() == 0
    assert Task.objects.filter(deleted_at__isnull=False).count() == 0
