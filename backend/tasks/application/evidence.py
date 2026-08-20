from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal
from typing import cast
from uuid import UUID, uuid4

from audit.ports.recording import AuditAction, AuditEntry
from core.error_codes import (
    EVIDENCE_UPLOAD_INVALID,
    EVIDENCE_UPLOAD_NOT_READY,
    IDEMPOTENCY_CONFLICT,
    INVALID_LOCATION_CHOICE,
    LOCATION_CHOICE_REQUIRED,
    NOT_FOUND,
    TASK_ALREADY_COMPLETED,
    VALIDATION_FAILED,
)
from core.errors import IdentityAPIError
from tasks.application.dependencies import TaskDependencies
from tasks.application.dto import (
    AccessTaskPhotoCommand,
    CompleteTaskFieldCommand,
    CreateEvidenceUploadCommand,
)
from tasks.domain.evidence import (
    EvidenceLocationResolution,
    EvidencePosition,
    EvidenceUploadStatus,
    GpsQuality,
    classify_gps_quality,
    resolve_evidence_location,
    validate_upload_metadata,
)
from tasks.domain.tasks import CompletionMethod, CompletionSnapshot, TaskSnapshot, TaskStatus
from tasks.ports.authorization import TaskReadScope
from tasks.ports.evidence import EvidenceObject, EvidenceStorage
from tasks.ports.locations import EvidenceLocationContext
from tasks.ports.repositories import (
    EvidenceUploadSnapshot,
    NewEvidenceUploadRecord,
    NewIdempotencyRecord,
    NewTaskUpdateRecord,
    TaskLifecycleUpdate,
    TaskPhotoRecord,
)


@dataclass(frozen=True, slots=True)
class EvidenceUploadResult:
    upload_id: str
    upload_url: str
    headers: dict[str, str]
    expires_at: str


@dataclass(frozen=True, slots=True)
class PhotoAccessResult:
    url: str
    expires_at: str


@dataclass(frozen=True, slots=True)
class PreparedFieldCompletion:
    upload_ids: tuple[UUID, ...]
    now: datetime
    photos: tuple[TaskPhotoRecord, ...]
    latitude: Decimal
    longitude: Decimal
    accuracy_m: Decimal
    quality: GpsQuality
    resolution: EvidenceLocationResolution
    request_hash: str


@dataclass(frozen=True, slots=True)
class EvidenceUploadClaim:
    upload_ids: tuple[UUID, ...]
    task_id: int
    actor_id: int
    now: datetime


@dataclass(frozen=True, slots=True)
class PreparedEvidenceUpload:
    upload_id: UUID
    evidence: EvidenceObject
    expires_at: datetime


class TaskEvidenceService:
    def __init__(self, dependencies: TaskDependencies) -> None:
        self._dependencies = dependencies
        self._storage = cast(EvidenceStorage, dependencies.storage)

    def create_upload(self, command: CreateEvidenceUploadCommand) -> EvidenceUploadResult:
        self._dependencies.authorization.authorize_field_completion(command.actor_id)
        _validate_upload_command(command)
        task = self._load_self_scoped(command.task_id, command.actor_id)
        if task.status is TaskStatus.COMPLETED:
            raise IdentityAPIError(TASK_ALREADY_COMPLETED, status_code=409)
        prepared = _prepare_upload(command, task.id, self._dependencies.clock.now())
        signed = self._storage.presign_put(prepared.evidence)
        with self._dependencies.unit_of_work_factory():
            self._dependencies.repository.create_evidence_upload(
                _new_upload_record(command, task.id, prepared)
            )
        return EvidenceUploadResult(
            str(prepared.upload_id), signed.url, signed.headers, signed.expires_at.isoformat()
        )

    def complete_field(self, command: CompleteTaskFieldCommand) -> TaskSnapshot:
        self._dependencies.authorization.authorize_field_completion(command.actor_id)
        replay = self._early_idempotent_replay(command)
        if replay is not None:
            return replay
        prepared = self._prepare_field(command)
        return self._commit_field(command, prepared)

    def _early_idempotent_replay(self, command: CompleteTaskFieldCommand) -> TaskSnapshot | None:
        existing = self._dependencies.repository.get_idempotency(
            command.actor_id, command.task_id, command.idempotency_key
        )
        if existing is None:
            return None
        if existing.request_hash != _request_hash(command):
            raise IdentityAPIError(IDEMPOTENCY_CONFLICT, status_code=409)
        task = self._dependencies.repository.get(command.task_id)
        if task is None:
            raise IdentityAPIError(NOT_FOUND, status_code=404)
        return task

    def _prepare_field(self, command: CompleteTaskFieldCommand) -> PreparedFieldCompletion:
        upload_ids = _upload_ids(command.upload_ids)
        now = self._dependencies.clock.now()
        position = _validated_field_position(command, now)
        claim = EvidenceUploadClaim(upload_ids, command.task_id, command.actor_id, now)
        preflight = self._load_uploads(claim, lock=False)
        photos = self._inspect_uploads(preflight)
        context = self._dependencies.locations.evidence_context(
            position.latitude, position.longitude
        )
        quality, resolution = _field_location_resolution(
            position, context, command.selected_location_id
        )
        _ensure_valid_resolution(resolution)
        return PreparedFieldCompletion(
            upload_ids,
            now,
            photos,
            position.latitude,
            position.longitude,
            position.accuracy_m,
            quality,
            resolution,
            _request_hash(command),
        )

    def _commit_field(
        self, command: CompleteTaskFieldCommand, prepared: PreparedFieldCompletion
    ) -> TaskSnapshot:
        with self._dependencies.unit_of_work_factory():
            replay = self._idempotent_replay(command, prepared.request_hash)
            if replay is not None:
                return replay
            task = self._load_self_scoped(command.task_id, command.actor_id, lock=True)
            if task.status is TaskStatus.COMPLETED:
                raise IdentityAPIError(TASK_ALREADY_COMPLETED, status_code=409)
            current_assignee_ids = self._dependencies.repository.assignee_ids(task.id)
            claim = EvidenceUploadClaim(
                prepared.upload_ids, command.task_id, command.actor_id, prepared.now
            )
            self._load_uploads(claim, lock=True)
            prepared = self._refresh_location_resolution(command, prepared)
            completion = _field_completion(command, prepared.now)
            update = self._dependencies.repository.append_update(
                _field_update_record(task, command, prepared, completion)
            )
            self._dependencies.repository.bind_evidence_uploads(update.id, prepared.photos)
            self._dependencies.repository.create_idempotency(
                _idempotency_record(command, task.id, prepared.request_hash, update.id)
            )
            completed = self._dependencies.repository.update_lifecycle(
                _completed_lifecycle(task.id, completion)
            )
            self._notify_completion(task.id, current_assignee_ids, completion)
            self._append_field_audit(task, completion)
            return completed

    def _notify_completion(
        self,
        task_id: int,
        current_assignee_ids: tuple[int, ...],
        completion: CompletionSnapshot,
    ) -> None:
        self._dependencies.notifications.suppress_task_reminders(task_id)
        if completion.completed_by_id not in current_assignee_ids:
            return
        if len(current_assignee_ids) < 2:
            return
        recipients = tuple(
            assignee_id
            for assignee_id in current_assignee_ids
            if assignee_id != completion.completed_by_id
        )
        self._dependencies.notifications.record_multi_assignee_completion(
            task_id, recipients, completion.completed_at
        )

    def _refresh_location_resolution(
        self,
        command: CompleteTaskFieldCommand,
        prepared: PreparedFieldCompletion,
    ) -> PreparedFieldCompletion:
        context = self._dependencies.locations.evidence_context(
            prepared.latitude, prepared.longitude
        )
        position = EvidencePosition(
            prepared.latitude,
            prepared.longitude,
            prepared.accuracy_m,
        )
        quality, resolution = _field_location_resolution(
            position, context, command.selected_location_id
        )
        _ensure_valid_resolution(resolution)
        return replace(prepared, quality=quality, resolution=resolution)

    def _append_field_audit(self, task: TaskSnapshot, completion: CompletionSnapshot) -> None:
        after = {
            "task_id": task.id,
            "status": TaskStatus.COMPLETED.value,
            "completion_method": completion.completion_method.value,
            "completed_by_id": completion.completed_by_id,
            "completed_at": completion.completed_at.isoformat(),
        }
        self._dependencies.audit.append_audit_entry(
            AuditEntry(
                completion.completed_by_id,
                AuditAction.TASK_COMPLETION_FIELD_EVIDENCE,
                "Task",
                str(task.id),
                {"status": task.status.value},
                after,
            )
        )

    def _idempotent_replay(
        self, command: CompleteTaskFieldCommand, request_hash: str
    ) -> TaskSnapshot | None:
        existing = self._dependencies.repository.get_idempotency(
            command.actor_id, command.task_id, command.idempotency_key
        )
        if existing is None:
            return None
        if existing.request_hash != request_hash:
            raise IdentityAPIError(IDEMPOTENCY_CONFLICT, status_code=409)
        task = self._dependencies.repository.get(command.task_id, lock=True)
        if task is None:
            raise IdentityAPIError(NOT_FOUND, status_code=404)
        return task

    def access_photo(self, command: AccessTaskPhotoCommand) -> PhotoAccessResult:
        scope = self._dependencies.authorization.authorize_photo_read(command.actor_id)
        task = self._dependencies.repository.get(command.task_id)
        if task is None:
            raise IdentityAPIError(NOT_FOUND, status_code=404)
        if scope is TaskReadScope.SELF:
            self._ensure_self_scope(task, command.actor_id)
        key = self._dependencies.repository.get_photo_object_key(command.task_id, command.photo_id)
        if key is None:
            raise IdentityAPIError(NOT_FOUND, status_code=404)
        url, expires_at = self._storage.presign_get(key)
        return PhotoAccessResult(url, expires_at.isoformat())

    def _load_self_scoped(self, task_id: int, actor_id: int, *, lock: bool = False) -> TaskSnapshot:
        task = self._dependencies.repository.get(task_id, lock=lock)
        if task is None:
            raise IdentityAPIError(NOT_FOUND, status_code=404)
        self._ensure_self_scope(task, actor_id)
        return task

    def _ensure_self_scope(self, task: TaskSnapshot, actor_id: int) -> None:
        if (
            actor_id != task.created_by_id
            and actor_id not in self._dependencies.repository.assignee_ids(task.id)
        ):
            raise IdentityAPIError(NOT_FOUND, status_code=404)

    def _load_uploads(
        self,
        claim: EvidenceUploadClaim,
        *,
        lock: bool,
    ) -> tuple[EvidenceUploadSnapshot, ...]:
        uploads = self._dependencies.repository.get_evidence_uploads(claim.upload_ids, lock=lock)
        if len(uploads) != len(claim.upload_ids):
            raise IdentityAPIError(EVIDENCE_UPLOAD_INVALID, status_code=422)
        for upload in uploads:
            if (
                upload.task_id != claim.task_id
                or upload.user_id != claim.actor_id
                or upload.bound_update_id is not None
            ):
                raise IdentityAPIError(EVIDENCE_UPLOAD_INVALID, status_code=422)
            if (
                upload.status in {EvidenceUploadStatus.BOUND, EvidenceUploadStatus.EXPIRED}
                or upload.expires_at <= claim.now
            ):
                raise IdentityAPIError(EVIDENCE_UPLOAD_NOT_READY, status_code=422)
        return uploads

    def _inspect_uploads(
        self, uploads: tuple[EvidenceUploadSnapshot, ...]
    ) -> tuple[TaskPhotoRecord, ...]:
        photos: list[TaskPhotoRecord] = []
        for upload in uploads:
            stored = self._storage.inspect(upload.object_key)
            if (stored.mime, stored.size_bytes, stored.checksum_sha256) != (
                upload.mime,
                upload.size_bytes,
                upload.checksum_sha256,
            ):
                raise IdentityAPIError(EVIDENCE_UPLOAD_NOT_READY, status_code=422)
            photos.append(
                TaskPhotoRecord(
                    upload.id,
                    upload.object_key,
                    upload.mime,
                    upload.size_bytes,
                    upload.checksum_sha256,
                )
            )
        return tuple(photos)


def _upload_ids(values: tuple[str, ...]) -> tuple[UUID, ...]:
    if not 1 <= len(values) <= 5 or len(set(values)) != len(values):
        raise IdentityAPIError(VALIDATION_FAILED, status_code=400)
    try:
        return tuple(sorted((UUID(value) for value in values), key=str))
    except ValueError as error:
        raise IdentityAPIError(VALIDATION_FAILED, status_code=400) from error


def _validate_upload_command(command: CreateEvidenceUploadCommand) -> None:
    try:
        validate_upload_metadata(command.mime, command.size_bytes, command.checksum_sha256)
    except ValueError as error:
        raise IdentityAPIError(VALIDATION_FAILED, status_code=400) from error


def _validated_field_position(command: CompleteTaskFieldCommand, now: datetime) -> EvidencePosition:
    if not command.idempotency_key.strip() or len(command.idempotency_key) > 128:
        raise IdentityAPIError(VALIDATION_FAILED, status_code=400)
    try:
        position = EvidencePosition(command.latitude, command.longitude, command.accuracy_m)
    except ValueError as error:
        raise IdentityAPIError(VALIDATION_FAILED, status_code=400) from error
    if command.captured_at is None or abs((now - command.captured_at).total_seconds()) > 60:
        raise IdentityAPIError(VALIDATION_FAILED, status_code=400)
    return position


def _field_location_resolution(
    position: EvidencePosition,
    context: EvidenceLocationContext,
    selected_location_id: int | None,
) -> tuple[GpsQuality, EvidenceLocationResolution]:
    quality = classify_gps_quality(
        position.accuracy_m,
        context.task_gps_good_accuracy_m,
        context.task_gps_low_accuracy_m,
    )
    return quality, resolve_evidence_location(quality, context.candidates, selected_location_id)


def _ensure_valid_resolution(resolution: EvidenceLocationResolution) -> None:
    details = {
        "candidates": [
            {"id": item.id, "code": item.code, "name": item.name} for item in resolution.candidates
        ]
    }
    if resolution.choice_required:
        raise IdentityAPIError(LOCATION_CHOICE_REQUIRED, status_code=409, details=details)
    if resolution.invalid_choice:
        raise IdentityAPIError(INVALID_LOCATION_CHOICE, status_code=422, details=details)


def _prepare_upload(
    command: CreateEvidenceUploadCommand, task_id: int, now: datetime
) -> PreparedEvidenceUpload:
    upload_id = uuid4()
    extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[command.mime]
    object_key = f"task-evidence/staging/{task_id}/{command.actor_id}/{upload_id}.{extension}"
    evidence = EvidenceObject(object_key, command.mime, command.size_bytes, command.checksum_sha256)
    return PreparedEvidenceUpload(upload_id, evidence, now + timedelta(days=7))


def _new_upload_record(
    command: CreateEvidenceUploadCommand, task_id: int, prepared: PreparedEvidenceUpload
) -> NewEvidenceUploadRecord:
    evidence = prepared.evidence
    return NewEvidenceUploadRecord(
        prepared.upload_id,
        task_id,
        command.actor_id,
        evidence.object_key,
        evidence.mime,
        evidence.size_bytes,
        evidence.checksum_sha256,
        prepared.expires_at,
    )


def _request_hash(command: CompleteTaskFieldCommand) -> str:
    normalized = {
        "upload_ids": sorted(command.upload_ids),
        "latitude": str(command.latitude),
        "longitude": str(command.longitude),
        "accuracy_m": str(command.accuracy_m),
        "captured_at": command.captured_at.isoformat() if command.captured_at else None,
        "selected_location_id": command.selected_location_id,
        "completion_note": command.completion_note.strip() if command.completion_note else None,
    }
    return hashlib.sha256(json.dumps(normalized, sort_keys=True).encode()).hexdigest()


def _field_completion(command: CompleteTaskFieldCommand, now: datetime) -> CompletionSnapshot:
    return CompletionSnapshot(
        command.actor_id,
        now,
        CompletionMethod.FIELD_EVIDENCE,
        command.completion_note.strip() if command.completion_note else None,
    )


def _idempotency_record(
    command: CompleteTaskFieldCommand, task_id: int, request_hash: str, update_id: int
) -> NewIdempotencyRecord:
    return NewIdempotencyRecord(
        command.actor_id, task_id, command.idempotency_key, request_hash, update_id
    )


def _completed_lifecycle(task_id: int, completion: CompletionSnapshot) -> TaskLifecycleUpdate:
    return TaskLifecycleUpdate(task_id, TaskStatus.COMPLETED, None, completion)


def _field_update_record(
    task: TaskSnapshot,
    command: CompleteTaskFieldCommand,
    prepared: PreparedFieldCompletion,
    completion: CompletionSnapshot,
) -> NewTaskUpdateRecord:
    resolution = prepared.resolution
    validation_result = _field_validation_result(prepared)
    return NewTaskUpdateRecord(
        task.id,
        command.actor_id,
        TaskStatus.COMPLETED,
        prepared.now,
        None,
        None,
        completion,
        prepared.latitude,
        prepared.longitude,
        prepared.accuracy_m,
        command.captured_at,
        prepared.quality,
        resolution.location_id,
        validation_result,
        resolution.method,
        resolution.distance_m,
        tuple(item.id for item in resolution.candidates),
    )


def _field_validation_result(prepared: PreparedFieldCompletion) -> str | None:
    if prepared.resolution.location_id is not None:
        return "INSIDE_GEOFENCE"
    if prepared.quality is GpsQuality.GOOD:
        return "OUTSIDE_GEOFENCE"
    return None
