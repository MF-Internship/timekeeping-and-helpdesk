from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from typing import Any

from tasks.domain.tasks import (
    IdentityDisplay,
    LocationDisplay,
    TaskAssigneeSnapshot,
    TaskReadSnapshot,
    TaskSnapshot,
    TaskStatus,
)
from tasks.ports.assignees import AssigneeEligibility
from tasks.ports.authorization import TaskCreateMode, TaskReadScope, TaskUpdateScope
from tasks.ports.repositories import (
    AssigneeDelta,
    NewTaskRecord,
    NewTaskUpdateRecord,
    TaskContentUpdate,
    TaskLifecycleUpdate,
)

NOW = datetime(2026, 8, 20, 2, 30, tzinfo=UTC)


def snapshot(
    *,
    task_id: int = 1,
    creator_id: int = 10,
    status: TaskStatus = TaskStatus.TODO,
    assigned_date: date = date(2026, 8, 20),
) -> TaskSnapshot:
    return TaskSnapshot(
        id=task_id,
        title="Original",
        description="Description",
        created_by_id=creator_id,
        assigned_date=assigned_date,
        status=status,
        location_id=None,
        completed_by_id=None,
        completed_at=None,
        completion_method=None,
        completion_note=None,
        block_reason="old" if status is TaskStatus.BLOCKED else None,
    )


class Authorization:
    def __init__(
        self,
        *,
        create: TaskCreateMode = TaskCreateMode.ASSIGN,
        read: TaskReadScope = TaskReadScope.ALL,
        update: TaskUpdateScope = TaskUpdateScope.ANY,
    ) -> None:
        self.create_mode = create
        self.read_scope = read
        self.update_scope = update
        self.override_allowed = True

    def authorize_create(self, actor_id: int) -> TaskCreateMode:
        return self.create_mode

    def authorize_read(self, actor_id: int) -> TaskReadScope:
        return self.read_scope

    def authorize_update(self, actor_id: int) -> TaskUpdateScope:
        return self.update_scope

    def authorize_delete(self, actor_id: int) -> None:
        return None

    def authorize_field_completion(self, actor_id: int) -> None:
        return None

    def authorize_photo_read(self, actor_id: int) -> TaskReadScope:
        return self.read_scope

    def authorize_override(self, actor_id: int) -> None:
        if not self.override_allowed:
            raise PermissionError("override")


class Assignees:
    def __init__(self, violating: tuple[int, ...] = ()) -> None:
        self.violating = violating
        self.locked: list[tuple[int, ...]] = []
        self.self_locked: list[int] = []

    def lock_eligible(self, user_ids: tuple[int, ...]) -> AssigneeEligibility:
        self.locked.append(user_ids)
        return AssigneeEligibility(
            tuple(
                IdentityDisplay(value, f"User {value}")
                for value in user_ids
                if value not in self.violating
            ),
            self.violating,
        )

    def lock_and_reauthorize_self(self, actor_id: int) -> IdentityDisplay:
        self.self_locked.append(actor_id)
        return IdentityDisplay(actor_id, f"User {actor_id}")


class Locations:
    def get(self, location_id: int) -> LocationDisplay:
        return LocationDisplay(location_id, f"LOC-{location_id}", "Location", True)


class Clock:
    def now(self) -> datetime:
        return NOW

    def business_date(self) -> date:
        return date(2026, 8, 20)


class UnitOfWork:
    def __init__(self) -> None:
        self.entered = 0
        self.exited_with: type[BaseException] | None = None

    def __enter__(self) -> UnitOfWork:
        self.entered += 1
        return self

    def __exit__(self, exc_type: type[BaseException] | None, *_: object) -> None:
        self.exited_with = exc_type


class Audit:
    def __init__(self) -> None:
        self.entries: list[object] = []
        self.outbox: list[object] = []

    def append_audit_entry(self, entry: object) -> None:
        self.entries.append(entry)

    def append_outbox_event(self, event: object) -> None:
        self.outbox.append(event)


class Repository:
    def __init__(
        self, task: TaskSnapshot | None = None, assignees: tuple[int, ...] = (20,)
    ) -> None:
        self.task = task
        self.assignees = assignees
        self.created: list[NewTaskRecord] = []
        self.added: list[tuple[int, tuple[int, ...], datetime]] = []
        self.replacements: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
        self.updates: list[NewTaskUpdateRecord] = []
        self.lifecycle: list[dict[str, Any]] = []
        self.fail_add = False

    def read_snapshot(self) -> TaskReadSnapshot | None:
        if self.task is None:
            return None
        return TaskReadSnapshot(
            self.task,
            IdentityDisplay(self.task.created_by_id, "Creator"),
            None,
            tuple(
                TaskAssigneeSnapshot(IdentityDisplay(user_id, f"User {user_id}"), NOW)
                for user_id in self.assignees
            ),
            None,
            (),
        )

    def create(self, record: NewTaskRecord) -> TaskSnapshot:
        self.created.append(record)
        self.task = snapshot(
            task_id=99,
            creator_id=record.creator_id,
            assigned_date=record.assigned_date,
        )
        self.task = replace(self.task, expected_location_text=record.expected_location_text)
        return self.task

    def get(self, task_id: int, *, lock: bool = False) -> TaskSnapshot | None:
        return self.task if self.task is not None and self.task.id == task_id else None

    def list_scoped(self, actor_id: int, *, all_tasks: bool) -> tuple[TaskSnapshot, ...]:
        return (self.task,) if self.task is not None else ()

    def list_detailed(self, actor_id: int, *, all_tasks: bool) -> tuple[TaskReadSnapshot, ...]:
        record = self.read_snapshot()
        return (record,) if record is not None else ()

    def get_detailed(
        self, task_id: int, actor_id: int, *, all_tasks: bool
    ) -> TaskReadSnapshot | None:
        record = self.read_snapshot()
        if record is None or record.task.id != task_id:
            return None
        if not all_tasks and actor_id not in {
            record.task.created_by_id,
            *(item.user.id for item in record.assignees),
        }:
            return None
        return record

    def assignee_ids(self, task_id: int) -> tuple[int, ...]:
        return self.assignees

    def add_assignees(self, task_id: int, user_ids: tuple[int, ...], assigned_at: datetime) -> None:
        if self.fail_add:
            raise RuntimeError("assignment unavailable")
        self.added.append((task_id, user_ids, assigned_at))
        self.assignees = user_ids

    def replace_assignees(self, delta: AssigneeDelta) -> None:
        self.replacements.append((delta.remove_ids, delta.add_ids))
        self.assignees = tuple(
            sorted((set(self.assignees) - set(delta.remove_ids)) | set(delta.add_ids))
        )

    def update_content(self, record: TaskContentUpdate) -> TaskSnapshot:
        assert self.task is not None
        self.task = replace(
            self.task,
            title=record.title,
            description=record.description,
            location_id=record.location_id,
            expected_location_text=record.expected_location_text,
        )
        return self.task

    def soft_delete(self, task_id: int, deleted_at: datetime) -> None:
        if self.task is not None and self.task.id == task_id:
            self.task = replace(self.task, deleted_at=deleted_at)

    def append_update(self, record: NewTaskUpdateRecord) -> object:
        self.updates.append(record)
        return object()

    def update_lifecycle(self, record: TaskLifecycleUpdate) -> TaskSnapshot:
        assert self.task is not None
        self.lifecycle.append(
            {
                "status": record.status,
                "block_reason": record.block_reason,
                "completion": record.completion,
            }
        )
        self.task = replace(
            self.task,
            status=record.status,
            block_reason=record.block_reason,
            completed_by_id=record.completion.completed_by_id if record.completion else None,
            completed_at=record.completion.completed_at if record.completion else None,
            completion_method=(record.completion.completion_method if record.completion else None),
            completion_note=record.completion.completion_note if record.completion else None,
        )
        return self.task
