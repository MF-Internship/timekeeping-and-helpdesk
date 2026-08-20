from datetime import date

import pytest

from audit.adapters.persistence.recording import DjangoAuditRecorder
from audit.models import AuditLog, OutboxEvent
from tasks.application.commands import TaskCommandService
from tasks.application.dependencies import TaskDependencies
from tasks.application.dto import CompleteTaskOverrideCommand
from tasks.models import TaskUpdate
from tests.integration.api.identity.helpers import create_user
from tests.integration.api.tasks.helpers import create_task
from tests.integration.postgres.tasks.helpers import production_dependencies

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


class FailingAudit:
    def append_audit_entry(self, entry: object) -> None:
        raise RuntimeError("audit unavailable")

    def append_outbox_event(self, event: object) -> None:
        raise AssertionError("task core must not create outbox events")


class AppendThenFailAudit(DjangoAuditRecorder):
    def append_audit_entry(self, entry: object) -> None:
        super().append_audit_entry(entry)  # type: ignore[arg-type]
        raise RuntimeError("failure after audit append")


def test_audit_failure_rolls_back_completion_snapshot_and_update() -> None:
    manager = create_user("pg-lifecycle-rollback-manager", "MANAGER")
    assignee = create_user("pg-lifecycle-rollback-assignee")
    task = create_task(manager, assignee, assigned_date=date.today(), status="IN_PROGRESS")
    production = production_dependencies()
    dependencies = TaskDependencies(
        production.authorization,
        production.assignees,
        production.locations,
        production.repository,
        production.clock,
        FailingAudit(),
        production.unit_of_work_factory,
    )
    with pytest.raises(RuntimeError, match="audit unavailable"):
        TaskCommandService(dependencies).complete_override(
            CompleteTaskOverrideCommand(manager.pk, task.pk, "valid")
        )
    task.refresh_from_db()
    assert task.status == "IN_PROGRESS" and task.completed_at is None
    assert not TaskUpdate.objects.exists()
    assert not AuditLog.objects.exists() and not OutboxEvent.objects.exists()


def test_failure_after_task_update_insert_rolls_back_every_row() -> None:
    manager = create_user("pg-update-insert-rollback-manager", "MANAGER")
    assignee = create_user("pg-update-insert-rollback-assignee")
    task = create_task(manager, assignee, assigned_date=date.today())
    production = production_dependencies()

    class FailingLifecycleRepository:
        def __getattr__(self, name: str) -> object:
            return getattr(production.repository, name)

        def update_lifecycle(self, record: object) -> object:
            raise RuntimeError("failure after TaskUpdate insert")

    dependencies = TaskDependencies(
        production.authorization,
        production.assignees,
        production.locations,
        FailingLifecycleRepository(),  # type: ignore[arg-type]
        production.clock,
        production.audit,
        production.unit_of_work_factory,
    )
    with pytest.raises(RuntimeError, match="after TaskUpdate"):
        TaskCommandService(dependencies).complete_override(
            CompleteTaskOverrideCommand(manager.pk, task.pk, "valid")
        )
    task.refresh_from_db()
    assert task.status == "TODO"
    assert not TaskUpdate.objects.exists() and not AuditLog.objects.exists()


def test_failure_after_audit_append_rolls_back_audit_and_business_rows() -> None:
    manager = create_user("pg-audit-append-rollback-manager", "MANAGER")
    assignee = create_user("pg-audit-append-rollback-assignee")
    task = create_task(manager, assignee, assigned_date=date.today())
    production = production_dependencies()
    dependencies = TaskDependencies(
        production.authorization,
        production.assignees,
        production.locations,
        production.repository,
        production.clock,
        AppendThenFailAudit(),
        production.unit_of_work_factory,
    )
    with pytest.raises(RuntimeError, match="after audit append"):
        TaskCommandService(dependencies).complete_override(
            CompleteTaskOverrideCommand(manager.pk, task.pk, "valid")
        )
    task.refresh_from_db()
    assert task.status == "TODO"
    assert not TaskUpdate.objects.exists() and not AuditLog.objects.exists()


def test_url_bearing_note_is_canonical_but_excluded_from_safe_audit_payload() -> None:
    manager = create_user("pg-lifecycle-url-manager", "MANAGER")
    assignee = create_user("pg-lifecycle-url-assignee")
    task = create_task(manager, assignee, assigned_date=date.today())
    note = "See https://internal.invalid/tickets/42"
    result = TaskCommandService(production_dependencies()).complete_override(
        CompleteTaskOverrideCommand(manager.pk, task.pk, note)
    )
    update = TaskUpdate.objects.get(task=task)
    audit = AuditLog.objects.get(target_type="Task", target_id=str(task.pk))
    assert result.completion_note == update.completion_note == note
    assert "completion_note" not in audit.after
    assert not OutboxEvent.objects.exists()
