from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from tasks.domain.evidence import GpsQuality, LocationResolutionMethod


class TaskStatus(StrEnum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"


class CompletionMethod(StrEnum):
    MANAGER_OVERRIDE = "MANAGER_OVERRIDE"
    FIELD_EVIDENCE = "FIELD_EVIDENCE"


@dataclass(frozen=True, slots=True)
class IdentityDisplay:
    id: int
    full_name: str


@dataclass(frozen=True, slots=True)
class LocationDisplay:
    id: int
    code: str
    name: str
    is_active: bool
    address: str = ""


@dataclass(frozen=True, slots=True)
class TaskAssigneeSnapshot:
    user: IdentityDisplay
    assigned_at: datetime


@dataclass(frozen=True, slots=True)
class CompletionSnapshot:
    completed_by_id: int
    completed_at: datetime
    completion_method: CompletionMethod
    completion_note: str | None


@dataclass(frozen=True, slots=True)
class TaskSnapshot:
    id: int
    title: str
    description: str
    created_by_id: int
    assigned_date: date
    status: TaskStatus
    location_id: int | None
    completed_by_id: int | None
    completed_at: datetime | None
    completion_method: CompletionMethod | None
    completion_note: str | None
    block_reason: str | None
    expected_location_text: str = ""
    deleted_at: datetime | None = None
    assignment_version: int = 1


@dataclass(frozen=True, slots=True)
class TaskUpdateSnapshot:
    id: int
    task_id: int
    user_id: int
    status: TaskStatus
    recorded_at: datetime
    note: str | None
    block_reason: str | None
    completion_method: CompletionMethod | None
    completion_note: str | None
    captured_latitude: str | None = None
    captured_longitude: str | None = None
    accuracy_m: str | None = None
    captured_at: datetime | None = None
    gps_quality: GpsQuality | None = None
    actual_location_id: int | None = None
    validation_result: str | None = None
    resolution_method: LocationResolutionMethod | None = None
    distance_m: str | None = None
    location_candidates: tuple[int, ...] = ()
    photos: tuple[TaskPhotoSnapshot, ...] = ()
    actual_location: LocationDisplay | None = None


@dataclass(frozen=True, slots=True)
class TaskPhotoSnapshot:
    id: int
    mime: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class TaskReadSnapshot:
    task: TaskSnapshot
    created_by: IdentityDisplay
    location: LocationDisplay | None
    assignees: tuple[TaskAssigneeSnapshot, ...]
    completed_by: IdentityDisplay | None
    updates: tuple[tuple[TaskUpdateSnapshot, IdentityDisplay], ...]
