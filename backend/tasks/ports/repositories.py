from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from tasks.domain.evidence import EvidenceUploadStatus, GpsQuality, LocationResolutionMethod
from tasks.domain.tasks import (
    CompletionSnapshot,
    TaskReadSnapshot,
    TaskSnapshot,
    TaskStatus,
    TaskUpdateSnapshot,
)


@dataclass(frozen=True, slots=True)
class NewTaskRecord:
    title: str
    description: str
    creator_id: int
    assigned_date: date
    location_id: int | None
    expected_location_text: str = ""


@dataclass(frozen=True, slots=True)
class NewTaskUpdateRecord:
    task_id: int
    actor_id: int
    status: TaskStatus
    recorded_at: datetime
    note: str | None
    block_reason: str | None
    completion: CompletionSnapshot | None
    captured_latitude: Decimal | None = None
    captured_longitude: Decimal | None = None
    accuracy_m: Decimal | None = None
    captured_at: datetime | None = None
    gps_quality: GpsQuality | None = None
    actual_location_id: int | None = None
    validation_result: str | None = None
    resolution_method: LocationResolutionMethod | None = None
    distance_m: Decimal | None = None
    location_candidates: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class EvidenceUploadSnapshot:
    id: UUID
    task_id: int
    user_id: int
    object_key: str
    mime: str
    size_bytes: int
    checksum_sha256: str
    status: EvidenceUploadStatus
    expires_at: datetime
    bound_update_id: int | None


@dataclass(frozen=True, slots=True)
class NewEvidenceUploadRecord:
    id: UUID
    task_id: int
    actor_id: int
    object_key: str
    mime: str
    size_bytes: int
    checksum_sha256: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class TaskPhotoRecord:
    upload_id: UUID
    object_key: str
    mime: str
    size_bytes: int
    checksum_sha256: str


@dataclass(frozen=True, slots=True)
class IdempotencySnapshot:
    request_hash: str
    task_update_id: int


@dataclass(frozen=True, slots=True)
class NewIdempotencyRecord:
    actor_id: int
    task_id: int
    key: str
    request_hash: str
    task_update_id: int


@dataclass(frozen=True, slots=True)
class AssigneeDelta:
    task_id: int
    remove_ids: tuple[int, ...]
    add_ids: tuple[int, ...]
    assigned_at: datetime


@dataclass(frozen=True, slots=True)
class TaskContentUpdate:
    task_id: int
    title: str
    description: str
    location_id: int | None
    expected_location_text: str = ""


@dataclass(frozen=True, slots=True)
class TaskLifecycleUpdate:
    task_id: int
    status: TaskStatus
    block_reason: str | None
    completion: CompletionSnapshot | None


class TaskRepository(Protocol):
    def create(self, record: NewTaskRecord) -> TaskSnapshot: ...

    def get(self, task_id: int, *, lock: bool = False) -> TaskSnapshot | None: ...
    def list_scoped(self, actor_id: int, *, all_tasks: bool) -> tuple[TaskSnapshot, ...]: ...
    def list_detailed(self, actor_id: int, *, all_tasks: bool) -> tuple[TaskReadSnapshot, ...]: ...
    def get_detailed(
        self, task_id: int, actor_id: int, *, all_tasks: bool
    ) -> TaskReadSnapshot | None: ...
    def assignee_ids(self, task_id: int) -> tuple[int, ...]: ...
    def add_assignees(
        self, task_id: int, user_ids: tuple[int, ...], assigned_at: datetime
    ) -> None: ...
    def replace_assignees(self, delta: AssigneeDelta) -> int: ...
    def update_content(self, record: TaskContentUpdate) -> TaskSnapshot: ...
    def soft_delete(self, task_id: int, deleted_at: datetime) -> None: ...
    def append_update(self, record: NewTaskUpdateRecord) -> TaskUpdateSnapshot: ...
    def update_lifecycle(self, record: TaskLifecycleUpdate) -> TaskSnapshot: ...
    def create_evidence_upload(self, record: NewEvidenceUploadRecord) -> EvidenceUploadSnapshot: ...
    def get_evidence_uploads(
        self, upload_ids: tuple[UUID, ...], *, lock: bool = False
    ) -> tuple[EvidenceUploadSnapshot, ...]: ...
    def list_cleanup_upload_ids(self, expired_at: datetime, limit: int) -> tuple[UUID, ...]: ...
    def mark_evidence_upload_expired(self, upload_id: UUID) -> None: ...
    def delete_expired_evidence_upload(self, upload_id: UUID) -> None: ...
    def bind_evidence_uploads(
        self, task_update_id: int, photos: tuple[TaskPhotoRecord, ...]
    ) -> None: ...
    def get_idempotency(
        self, actor_id: int, task_id: int, key: str
    ) -> IdempotencySnapshot | None: ...
    def create_idempotency(self, record: NewIdempotencyRecord) -> None: ...
    def get_photo_object_key(self, task_id: int, photo_id: int) -> str | None: ...
