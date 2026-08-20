from __future__ import annotations

from datetime import datetime
from uuid import UUID

from django.db.models import Q, QuerySet

from tasks.domain.evidence import EvidenceUploadStatus, GpsQuality, LocationResolutionMethod
from tasks.domain.tasks import (
    CompletionMethod,
    IdentityDisplay,
    LocationDisplay,
    TaskAssigneeSnapshot,
    TaskPhotoSnapshot,
    TaskReadSnapshot,
    TaskSnapshot,
    TaskStatus,
    TaskUpdateSnapshot,
)
from tasks.models import (
    CompletionIdempotency,
    EvidenceUpload,
    Task,
    TaskAssignee,
    TaskPhoto,
    TaskUpdate,
)
from tasks.ports.repositories import (
    AssigneeDelta,
    EvidenceUploadSnapshot,
    IdempotencySnapshot,
    NewEvidenceUploadRecord,
    NewIdempotencyRecord,
    NewTaskRecord,
    NewTaskUpdateRecord,
    TaskContentUpdate,
    TaskLifecycleUpdate,
    TaskPhotoRecord,
)


class DjangoTaskRepository:
    def create(self, record: NewTaskRecord) -> TaskSnapshot:
        model = Task.objects.create(
            title=record.title,
            description=record.description,
            created_by_id=record.creator_id,
            assigned_date=record.assigned_date,
            location_id=record.location_id,
            expected_location_text=record.expected_location_text,
        )
        return task_snapshot(model)

    def get(self, task_id: int, *, lock: bool = False) -> TaskSnapshot | None:
        query = Task.objects.select_for_update() if lock else Task.objects
        model = query.filter(pk=task_id, deleted_at__isnull=True).first()
        return task_snapshot(model) if model is not None else None

    def list_scoped(self, actor_id: int, *, all_tasks: bool) -> tuple[TaskSnapshot, ...]:
        query = _scoped(Task.objects.filter(deleted_at__isnull=True), actor_id, all_tasks=all_tasks)
        return tuple(task_snapshot(model) for model in _ordered(query))

    def list_detailed(self, actor_id: int, *, all_tasks: bool) -> tuple[TaskReadSnapshot, ...]:
        query = _scoped(
            _detailed(Task.objects.filter(deleted_at__isnull=True)), actor_id, all_tasks=all_tasks
        )
        return tuple(task_read_snapshot(model) for model in _ordered(query))

    def get_detailed(
        self, task_id: int, actor_id: int, *, all_tasks: bool
    ) -> TaskReadSnapshot | None:
        query = _scoped(
            _detailed(Task.objects.filter(deleted_at__isnull=True)), actor_id, all_tasks=all_tasks
        )
        model = query.filter(pk=task_id).first()
        return task_read_snapshot(model) if model is not None else None

    def assignee_ids(self, task_id: int) -> tuple[int, ...]:
        values = TaskAssignee.objects.filter(task_id=task_id).order_by("user_id")
        return tuple(values.values_list("user_id", flat=True))

    def add_assignees(
        self,
        task_id: int,
        user_ids: tuple[int, ...],
        assigned_at: datetime,
    ) -> None:
        TaskAssignee.objects.bulk_create(
            [
                TaskAssignee(task_id=task_id, user_id=user_id, assigned_at=assigned_at)
                for user_id in user_ids
            ]
        )

    def replace_assignees(self, delta: AssigneeDelta) -> None:
        TaskAssignee.objects.filter(task_id=delta.task_id, user_id__in=delta.remove_ids).delete()
        self.add_assignees(delta.task_id, delta.add_ids, delta.assigned_at)

    def update_content(self, record: TaskContentUpdate) -> TaskSnapshot:
        Task.objects.filter(pk=record.task_id).update(
            title=record.title,
            description=record.description,
            location_id=record.location_id,
            expected_location_text=record.expected_location_text,
        )
        return task_snapshot(Task.objects.get(pk=record.task_id))

    def soft_delete(self, task_id: int, deleted_at: datetime) -> None:
        Task.objects.filter(pk=task_id, deleted_at__isnull=True).update(deleted_at=deleted_at)

    def append_update(self, record: NewTaskUpdateRecord) -> TaskUpdateSnapshot:
        completion = record.completion
        model = TaskUpdate.objects.create(
            task_id=record.task_id,
            user_id=record.actor_id,
            status=record.status.value,
            recorded_at=record.recorded_at,
            note=record.note,
            block_reason=record.block_reason,
            completion_method=(completion.completion_method.value if completion else None),
            completion_note=completion.completion_note if completion else None,
            captured_latitude=record.captured_latitude,
            captured_longitude=record.captured_longitude,
            accuracy_m=record.accuracy_m,
            captured_at=record.captured_at,
            gps_quality=record.gps_quality.value if record.gps_quality else None,
            actual_location_id=record.actual_location_id,
            validation_result=record.validation_result,
            resolution_method=(
                record.resolution_method.value if record.resolution_method else None
            ),
            distance_m=record.distance_m,
            location_candidates=list(record.location_candidates),
        )
        return task_update_snapshot(model)

    def update_lifecycle(self, record: TaskLifecycleUpdate) -> TaskSnapshot:
        completion = record.completion
        Task.objects.filter(pk=record.task_id).update(
            status=record.status.value,
            block_reason=record.block_reason,
            completed_by_id=completion.completed_by_id if completion else None,
            completed_at=completion.completed_at if completion else None,
            completion_method=completion.completion_method.value if completion else None,
            completion_note=completion.completion_note if completion else None,
        )
        return task_snapshot(Task.objects.get(pk=record.task_id))

    def create_evidence_upload(self, record: NewEvidenceUploadRecord) -> EvidenceUploadSnapshot:
        model = EvidenceUpload.objects.create(
            id=record.id,
            task_id=record.task_id,
            user_id=record.actor_id,
            object_key=record.object_key,
            mime=record.mime,
            size_bytes=record.size_bytes,
            checksum_sha256=record.checksum_sha256,
            expires_at=record.expires_at,
        )
        return evidence_upload_snapshot(model)

    def get_evidence_uploads(
        self, upload_ids: tuple[UUID, ...], *, lock: bool = False
    ) -> tuple[EvidenceUploadSnapshot, ...]:
        query = EvidenceUpload.objects.select_for_update() if lock else EvidenceUpload.objects
        return tuple(
            evidence_upload_snapshot(model)
            for model in query.filter(pk__in=upload_ids).order_by("id")
        )

    def list_cleanup_upload_ids(self, expired_at: datetime, limit: int) -> tuple[UUID, ...]:
        return tuple(
            EvidenceUpload.objects.filter(
                status__in=(
                    EvidenceUploadStatus.PENDING.value,
                    EvidenceUploadStatus.UPLOADED.value,
                    EvidenceUploadStatus.EXPIRED.value,
                ),
                bound_update__isnull=True,
                expires_at__lte=expired_at,
            )
            .order_by("expires_at", "id")
            .values_list("id", flat=True)[:limit]
        )

    def mark_evidence_upload_expired(self, upload_id: UUID) -> None:
        EvidenceUpload.objects.filter(pk=upload_id, bound_update__isnull=True).update(
            status=EvidenceUploadStatus.EXPIRED.value
        )

    def delete_expired_evidence_upload(self, upload_id: UUID) -> None:
        EvidenceUpload.objects.filter(
            pk=upload_id,
            status=EvidenceUploadStatus.EXPIRED.value,
            bound_update__isnull=True,
        ).delete()

    def bind_evidence_uploads(
        self, task_update_id: int, photos: tuple[TaskPhotoRecord, ...]
    ) -> None:
        TaskPhoto.objects.bulk_create(
            [
                TaskPhoto(
                    task_update_id=task_update_id,
                    evidence_upload_id=photo.upload_id,
                    object_key=photo.object_key,
                    mime=photo.mime,
                    size_bytes=photo.size_bytes,
                    checksum_sha256=photo.checksum_sha256,
                )
                for photo in photos
            ]
        )
        EvidenceUpload.objects.filter(pk__in=[photo.upload_id for photo in photos]).update(
            status=EvidenceUploadStatus.BOUND.value,
            bound_update_id=task_update_id,
        )

    def get_idempotency(self, actor_id: int, task_id: int, key: str) -> IdempotencySnapshot | None:
        model = CompletionIdempotency.objects.filter(
            actor_id=actor_id, task_id=task_id, key=key
        ).first()
        return (
            IdempotencySnapshot(model.request_hash, model.task_update_id)  # type: ignore[attr-defined]
            if model
            else None
        )

    def create_idempotency(self, record: NewIdempotencyRecord) -> None:
        CompletionIdempotency.objects.create(
            actor_id=record.actor_id,
            task_id=record.task_id,
            key=record.key,
            request_hash=record.request_hash,
            task_update_id=record.task_update_id,
        )

    def get_photo_object_key(self, task_id: int, photo_id: int) -> str | None:
        return (
            TaskPhoto.objects.filter(pk=photo_id, task_update__task_id=task_id)
            .values_list("object_key", flat=True)
            .first()
        )


def _ordered(query: QuerySet[Task]) -> QuerySet[Task]:
    return query.order_by("status", "assigned_date", "id")


def _scoped(query: QuerySet[Task], actor_id: int, *, all_tasks: bool) -> QuerySet[Task]:
    if all_tasks:
        return query
    return query.filter(Q(created_by_id=actor_id) | Q(assignee_links__user_id=actor_id)).distinct()


def _detailed(query: QuerySet[Task]) -> QuerySet[Task]:
    return query.select_related("created_by", "location", "completed_by").prefetch_related(
        "assignee_links__user", "updates__user", "updates__photos", "updates__actual_location"
    )


def task_snapshot(model: Task) -> TaskSnapshot:
    method = CompletionMethod(model.completion_method) if model.completion_method else None
    return TaskSnapshot(
        id=model.pk,
        title=model.title,
        description=model.description,
        created_by_id=model.created_by_id,  # type: ignore[attr-defined]
        assigned_date=model.assigned_date,
        status=TaskStatus(model.status),
        location_id=model.location_id,  # type: ignore[attr-defined]
        completed_by_id=model.completed_by_id,  # type: ignore[attr-defined]
        completed_at=model.completed_at,
        completion_method=method,
        completion_note=model.completion_note,
        block_reason=model.block_reason,
        expected_location_text=model.expected_location_text,
        deleted_at=model.deleted_at,
    )


def task_update_snapshot(model: TaskUpdate) -> TaskUpdateSnapshot:
    method = CompletionMethod(model.completion_method) if model.completion_method else None
    task_id = model.task_id  # type: ignore[attr-defined]
    user_id = model.user_id  # type: ignore[attr-defined]
    actual_location_id = model.actual_location_id  # type: ignore[attr-defined]
    return TaskUpdateSnapshot(
        model.pk,
        task_id,
        user_id,
        TaskStatus(model.status),
        model.recorded_at,
        model.note,
        model.block_reason,
        method,
        model.completion_note,
        _decimal_text(model.captured_latitude),
        _decimal_text(model.captured_longitude),
        _decimal_text(model.accuracy_m),
        model.captured_at,
        GpsQuality(model.gps_quality) if model.gps_quality else None,
        actual_location_id,
        model.validation_result,
        LocationResolutionMethod(model.resolution_method) if model.resolution_method else None,
        _decimal_text(model.distance_m),
        tuple(model.location_candidates),
        _photo_snapshots(model),
        _actual_location_display(model),
    )


def _decimal_text(value: object | None) -> str | None:
    return str(value) if value is not None else None


def _photo_snapshots(model: TaskUpdate) -> tuple[TaskPhotoSnapshot, ...]:
    photos = sorted(model.photos.all(), key=lambda value: value.pk)  # type: ignore[attr-defined]
    return tuple(TaskPhotoSnapshot(photo.pk, photo.mime, photo.size_bytes) for photo in photos)


def _actual_location_display(model: TaskUpdate) -> LocationDisplay | None:
    location_id = model.actual_location_id  # type: ignore[attr-defined]
    if location_id is None:
        return None
    location = model.actual_location
    return LocationDisplay(
        location_id, location.code, location.name, location.is_active, location.address
    )


def evidence_upload_snapshot(model: EvidenceUpload) -> EvidenceUploadSnapshot:
    return EvidenceUploadSnapshot(
        model.pk,
        model.task_id,  # type: ignore[attr-defined]
        model.user_id,  # type: ignore[attr-defined]
        model.object_key,
        model.mime,
        model.size_bytes,
        model.checksum_sha256,
        EvidenceUploadStatus(model.status),
        model.expires_at,
        model.bound_update_id,  # type: ignore[attr-defined]
    )


def task_read_snapshot(model: Task) -> TaskReadSnapshot:
    creator = IdentityDisplay(model.created_by_id, model.created_by.full_name)  # type: ignore[attr-defined]
    return TaskReadSnapshot(
        task_snapshot(model),
        creator,
        _location_display(model),
        _assignee_displays(model),
        _completed_by_display(model),
        _update_displays(model),
    )


def _location_display(model: Task) -> LocationDisplay | None:
    location_id = model.location_id  # type: ignore[attr-defined]
    if location_id is None:
        return None
    return LocationDisplay(
        location_id,
        model.location.code,
        model.location.name,
        model.location.is_active,
        model.location.address,
    )


def _assignee_displays(model: Task) -> tuple[TaskAssigneeSnapshot, ...]:
    links = model.assignee_links.all()  # type: ignore[attr-defined]
    return tuple(
        TaskAssigneeSnapshot(
            IdentityDisplay(link.user_id, link.user.full_name),
            link.assigned_at,
        )
        for link in sorted(links, key=lambda value: value.user_id)
    )


def _completed_by_display(model: Task) -> IdentityDisplay | None:
    completed_by_id = model.completed_by_id  # type: ignore[attr-defined]
    if completed_by_id is None:
        return None
    return IdentityDisplay(completed_by_id, model.completed_by.full_name)


def _update_displays(
    model: Task,
) -> tuple[tuple[TaskUpdateSnapshot, IdentityDisplay], ...]:
    updates = model.updates.all()  # type: ignore[attr-defined]
    return tuple(
        (
            task_update_snapshot(update),
            IdentityDisplay(update.user_id, update.user.full_name),
        )
        for update in sorted(updates, key=lambda value: value.pk)
    )
