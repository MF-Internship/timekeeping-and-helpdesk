from __future__ import annotations

from audit.adapters.persistence.recording import DjangoAuditRecorder
from config.composition import task_container
from config.task_adapters import (
    DjangoAssigneeDirectory,
    DjangoTaskAuthorization,
    DjangoTaskLocationDirectory,
)
from tasks.adapters.clock import DjangoClock
from tasks.adapters.persistence.repositories import DjangoTaskRepository
from tasks.adapters.persistence.unit_of_work import DjangoUnitOfWork
from tasks.application.commands import TaskCommandService
from tasks.application.dependencies import TaskDependencies
from tasks.application.queries import TaskQueryService


def commands() -> TaskCommandService:
    return task_container().commands


def queries() -> TaskQueryService:
    return task_container().queries


def production_dependencies() -> TaskDependencies:
    return TaskDependencies(
        DjangoTaskAuthorization(),
        DjangoAssigneeDirectory(),
        DjangoTaskLocationDirectory(),
        DjangoTaskRepository(),
        DjangoClock(),
        DjangoAuditRecorder(),
        DjangoUnitOfWork,
    )
