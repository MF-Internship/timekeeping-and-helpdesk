from __future__ import annotations

from audit.ports.recording import AuditAction, AuditEntry
from core.error_codes import (
    BLOCK_REASON_REQUIRED,
    INACTIVE_ASSIGNEE,
    NOT_FOUND,
    SERVER_OWNED_FIELD,
    TASK_ALREADY_COMPLETED,
    VALIDATION_FAILED,
)
from core.errors import IdentityAPIError
from tasks.application.dependencies import TaskDependencies
from tasks.application.dto import (
    ChangeTaskStatusCommand,
    CompleteTaskOverrideCommand,
    CreateTaskCommand,
    DeleteTaskCommand,
    UpdateTaskCommand,
)
from tasks.domain.tasks import CompletionSnapshot, TaskSnapshot, TaskStatus
from tasks.domain.transitions import (
    TransitionOutcome,
    build_completion_snapshot,
    decide_transition,
    normalize_optional_text,
    resolve_block_reason,
)
from tasks.ports.authorization import TaskCreateMode, TaskUpdateScope
from tasks.ports.repositories import (
    AssigneeDelta,
    NewTaskRecord,
    NewTaskUpdateRecord,
    TaskContentUpdate,
    TaskLifecycleUpdate,
)


class TaskCommandService:
    def __init__(self, dependencies: TaskDependencies) -> None:
        self._dependencies = dependencies

    def create(self, command: CreateTaskCommand) -> TaskSnapshot:
        mode = self._dependencies.authorization.authorize_create(command.actor_id)
        title = _required_text(command.title, "title")
        description = command.description.strip()
        assignee_ids = _normalize_ids(command.assignee_ids)
        _validate_create_shape(mode, assignee_ids)
        with self._dependencies.unit_of_work_factory():
            if mode is TaskCreateMode.SELF:
                self._dependencies.assignees.lock_and_reauthorize_self(command.actor_id)
                assignee_ids = (command.actor_id,)
            else:
                self._validate_assignees(assignee_ids)
            self._validate_location(command.location_id)
            task = self._dependencies.repository.create(
                NewTaskRecord(
                    title,
                    description,
                    command.actor_id,
                    command.assigned_date,
                    command.location_id,
                    _optional_text(command.expected_location),
                )
            )
            self._dependencies.repository.add_assignees(
                task.id,
                assignee_ids,
                self._dependencies.clock.now(),
            )
            return task

    def update(self, command: UpdateTaskCommand) -> TaskSnapshot:
        scope = self._dependencies.authorization.authorize_update(command.actor_id)
        with self._dependencies.unit_of_work_factory():
            task = self._load_scoped(command.task_id, command.actor_id, scope)
            _reject_terminal(task)
            if scope is TaskUpdateScope.SELF and command.assignee_ids is not None:
                raise IdentityAPIError(SERVER_OWNED_FIELD, status_code=400)
            self._replace_assignees(task, command)
            title, description, location_id, expected_location = self._updated_content(
                task, command
            )
            return self._dependencies.repository.update_content(
                TaskContentUpdate(task.id, title, description, location_id, expected_location)
            )

    def delete(self, command: DeleteTaskCommand) -> None:
        self._dependencies.authorization.authorize_delete(command.actor_id)
        with self._dependencies.unit_of_work_factory():
            task = self._dependencies.repository.get(command.task_id, lock=True)
            if task is None or task.created_by_id != command.actor_id:
                raise IdentityAPIError(NOT_FOUND, status_code=404)
            if self._dependencies.repository.assignee_ids(task.id) != (command.actor_id,):
                raise IdentityAPIError(NOT_FOUND, status_code=404)
            if task.status is TaskStatus.COMPLETED:
                raise IdentityAPIError(TASK_ALREADY_COMPLETED, status_code=409)
            deleted_at = self._dependencies.clock.now()
            self._dependencies.repository.soft_delete(task.id, deleted_at)
            self._dependencies.audit.append_audit_entry(
                AuditEntry(
                    command.actor_id,
                    AuditAction.TASK_SELF_DELETED,
                    "Task",
                    str(task.id),
                    {"deleted": False},
                    {"deleted": True, "deleted_at": deleted_at.isoformat()},
                )
            )

    def change_status(self, command: ChangeTaskStatusCommand) -> TaskSnapshot:
        scope = self._dependencies.authorization.authorize_update(command.actor_id)
        with self._dependencies.unit_of_work_factory():
            task = self._load_scoped(command.task_id, command.actor_id, scope)
            _reject_terminal(task)
            decision = decide_transition(task.status, command.status)
            if decision.outcome is TransitionOutcome.NO_OP:
                return task
            if decision.outcome is TransitionOutcome.REJECTED:
                raise IdentityAPIError(VALIDATION_FAILED, status_code=400)
            try:
                block_reason = resolve_block_reason(
                    command.status,
                    note=command.note,
                    block_reason=command.block_reason,
                )
            except ValueError as error:
                raise IdentityAPIError(BLOCK_REASON_REQUIRED, status_code=422) from error
            return self._persist_status(task, command, block_reason)

    def complete_override(self, command: CompleteTaskOverrideCommand) -> TaskSnapshot:
        self._dependencies.authorization.authorize_override(command.actor_id)
        with self._dependencies.unit_of_work_factory():
            task = self._dependencies.repository.get(command.task_id, lock=True)
            if task is None:
                raise IdentityAPIError(NOT_FOUND, status_code=404)
            if task.status is TaskStatus.COMPLETED:
                raise IdentityAPIError(TASK_ALREADY_COMPLETED, status_code=409)
            try:
                completion = build_completion_snapshot(
                    command.actor_id,
                    self._dependencies.clock.now(),
                    command.completion_note,
                )
            except ValueError as error:
                raise IdentityAPIError(VALIDATION_FAILED, status_code=400) from error
            result = self._persist_completion(task, command, completion)
            self._append_override_audit(task, command, completion)
            return result

    def _persist_status(
        self,
        task: TaskSnapshot,
        command: ChangeTaskStatusCommand,
        block_reason: str | None,
    ) -> TaskSnapshot:
        recorded_at = self._dependencies.clock.now()
        self._dependencies.repository.append_update(
            NewTaskUpdateRecord(
                task.id,
                command.actor_id,
                command.status,
                recorded_at,
                normalize_optional_text(command.note),
                block_reason,
                None,
            )
        )
        return self._dependencies.repository.update_lifecycle(
            TaskLifecycleUpdate(task.id, command.status, block_reason, None)
        )

    def _persist_completion(
        self,
        task: TaskSnapshot,
        command: CompleteTaskOverrideCommand,
        completion: CompletionSnapshot,
    ) -> TaskSnapshot:
        self._dependencies.repository.append_update(
            NewTaskUpdateRecord(
                task.id,
                command.actor_id,
                TaskStatus.COMPLETED,
                completion.completed_at,
                None,
                None,
                completion,
            )
        )
        return self._dependencies.repository.update_lifecycle(
            TaskLifecycleUpdate(task.id, TaskStatus.COMPLETED, None, completion)
        )

    def _append_override_audit(
        self,
        task: TaskSnapshot,
        command: CompleteTaskOverrideCommand,
        completion: CompletionSnapshot,
    ) -> None:
        after = {
            "task_id": task.id,
            "status": TaskStatus.COMPLETED.value,
            "completion_method": completion.completion_method.value,
            "completed_by_id": command.actor_id,
            "completed_at": completion.completed_at.isoformat(),
        }
        self._dependencies.audit.append_audit_entry(
            AuditEntry(
                command.actor_id,
                AuditAction.TASK_COMPLETION_OVERRIDDEN,
                "Task",
                str(task.id),
                {"status": task.status.value},
                after,
            )
        )

    def _load_scoped(
        self,
        task_id: int,
        actor_id: int,
        scope: TaskUpdateScope,
    ) -> TaskSnapshot:
        task = self._dependencies.repository.get(task_id, lock=True)
        if task is None:
            raise IdentityAPIError(NOT_FOUND, status_code=404)
        if scope is TaskUpdateScope.SELF:
            assignees = self._dependencies.repository.assignee_ids(task.id)
            if actor_id != task.created_by_id and actor_id not in assignees:
                raise IdentityAPIError(NOT_FOUND, status_code=404)
        return task

    def _replace_assignees(self, task: TaskSnapshot, command: UpdateTaskCommand) -> None:
        if command.assignee_ids is None:
            return
        desired_ids = _normalize_ids(command.assignee_ids)
        if not desired_ids:
            raise IdentityAPIError(VALIDATION_FAILED, status_code=400)
        current_ids = self._dependencies.repository.assignee_ids(task.id)
        additions = tuple(sorted(set(desired_ids) - set(current_ids)))
        self._validate_assignees(additions)
        self._dependencies.repository.replace_assignees(
            AssigneeDelta(
                task.id,
                tuple(sorted(set(current_ids) - set(desired_ids))),
                additions,
                self._dependencies.clock.now(),
            )
        )

    def _updated_content(
        self, task: TaskSnapshot, command: UpdateTaskCommand
    ) -> tuple[str, str, int | None, str]:
        location_id = task.location_id
        if command.replace_location:
            self._validate_location(command.location_id)
            location_id = command.location_id
        title = _required_text(command.title, "title") if command.title is not None else task.title
        description = (
            command.description.strip() if command.description is not None else task.description
        )
        expected_location = task.expected_location_text
        if command.replace_expected_location:
            expected_location = _optional_text(command.expected_location or "")
        return title, description, location_id, expected_location

    def _validate_assignees(self, user_ids: tuple[int, ...]) -> None:
        if not user_ids:
            return
        result = self._dependencies.assignees.lock_eligible(user_ids)
        if result.violating_ids:
            raise IdentityAPIError(
                INACTIVE_ASSIGNEE,
                status_code=422,
                details={"assignee_ids": list(result.violating_ids)},
            )

    def _validate_location(self, location_id: int | None) -> None:
        if location_id is not None and self._dependencies.locations.get(location_id) is None:
            raise IdentityAPIError(NOT_FOUND, status_code=404)


def _validate_create_shape(mode: TaskCreateMode, assignee_ids: tuple[int, ...]) -> None:
    if mode is TaskCreateMode.ASSIGN and not assignee_ids:
        raise IdentityAPIError(VALIDATION_FAILED, status_code=400)
    if mode is TaskCreateMode.SELF and assignee_ids:
        raise IdentityAPIError(SERVER_OWNED_FIELD, status_code=400)


def _required_text(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise IdentityAPIError(VALIDATION_FAILED, status_code=400, details={field: ["required"]})
    return normalized


def _optional_text(value: str) -> str:
    return value.strip()


def _normalize_ids(values: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(sorted(set(values)))


def _reject_terminal(task: TaskSnapshot) -> None:
    if task.status is TaskStatus.COMPLETED:
        raise IdentityAPIError(VALIDATION_FAILED, status_code=400)
