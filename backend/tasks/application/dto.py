from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from tasks.domain.tasks import TaskStatus


@dataclass(frozen=True, slots=True)
class CreateTaskCommand:
    actor_id: int
    title: str
    description: str
    assigned_date: date
    location_id: int | None = None
    assignee_ids: tuple[int, ...] = ()
    expected_location: str = ""


@dataclass(frozen=True, slots=True)
class UpdateTaskCommand:
    actor_id: int
    task_id: int
    title: str | None = None
    description: str | None = None
    location_id: int | None = None
    replace_location: bool = False
    assignee_ids: tuple[int, ...] | None = None
    expected_location: str | None = None
    replace_expected_location: bool = False


@dataclass(frozen=True, slots=True)
class DeleteTaskCommand:
    actor_id: int
    task_id: int


@dataclass(frozen=True, slots=True)
class ChangeTaskStatusCommand:
    actor_id: int
    task_id: int
    status: TaskStatus
    note: str | None = None
    block_reason: str | None = None


@dataclass(frozen=True, slots=True)
class CompleteTaskOverrideCommand:
    actor_id: int
    task_id: int
    completion_note: str


@dataclass(frozen=True, slots=True)
class CreateEvidenceUploadCommand:
    actor_id: int
    task_id: int
    mime: str
    size_bytes: int
    checksum_sha256: str


@dataclass(frozen=True, slots=True)
class CompleteTaskFieldCommand:
    actor_id: int
    task_id: int
    idempotency_key: str
    upload_ids: tuple[str, ...]
    latitude: Decimal
    longitude: Decimal
    accuracy_m: Decimal
    captured_at: datetime | None = None
    selected_location_id: int | None = None
    completion_note: str | None = None


@dataclass(frozen=True, slots=True)
class AccessTaskPhotoCommand:
    actor_id: int
    task_id: int
    photo_id: int
