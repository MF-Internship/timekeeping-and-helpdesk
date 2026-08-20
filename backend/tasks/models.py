from __future__ import annotations

from typing import Any, ClassVar

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models.functions import Now

from tasks.domain.evidence import EvidenceUploadStatus, GpsQuality, LocationResolutionMethod
from tasks.domain.tasks import CompletionMethod, TaskStatus


def _nonblank(field: str) -> models.Q:
    return models.Q(**{f"{field}__isnull": False}) & ~models.Q(**{f"{field}__regex": r"^\s*$"})


def _task_completion_shape() -> models.Q:
    common = models.Q(
        status=TaskStatus.COMPLETED.value,
        completed_by__isnull=False,
        completed_at__isnull=False,
    )
    method = (
        models.Q(completion_method=CompletionMethod.MANAGER_OVERRIDE.value)
        & _nonblank("completion_note")
    ) | models.Q(completion_method=CompletionMethod.FIELD_EVIDENCE.value)
    completed = common & method
    incomplete = ~models.Q(status=TaskStatus.COMPLETED.value) & models.Q(
        completed_by__isnull=True,
        completed_at__isnull=True,
        completion_method__isnull=True,
        completion_note__isnull=True,
    )
    return completed | incomplete


def _update_completion_shape() -> models.Q:
    completed = models.Q(status=TaskStatus.COMPLETED.value, completion_method__isnull=False) & (
        (
            models.Q(completion_method=CompletionMethod.MANAGER_OVERRIDE.value)
            & _nonblank("completion_note")
        )
        | models.Q(
            completion_method=CompletionMethod.FIELD_EVIDENCE.value,
            captured_latitude__isnull=False,
            captured_longitude__isnull=False,
            accuracy_m__isnull=False,
            captured_at__isnull=False,
            gps_quality__isnull=False,
        )
    )
    incomplete = ~models.Q(status=TaskStatus.COMPLETED.value) & models.Q(
        completion_method__isnull=True,
        completion_note__isnull=True,
    )
    return completed | incomplete


class Task(models.Model):
    title: models.TextField[str, str] = models.TextField()
    description: models.TextField[str, str] = models.TextField(blank=True, default="")
    created_by: models.ForeignKey[Any, Any] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_tasks",
    )
    assigned_date: models.DateField[Any, Any] = models.DateField()
    status: models.CharField[str, str] = models.CharField(
        max_length=16,
        choices=[(value.value, value.value) for value in TaskStatus],
        default=TaskStatus.TODO.value,
        db_default=TaskStatus.TODO.value,
    )
    location: models.ForeignKey[Any, Any] = models.ForeignKey(
        "locations.Location",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="expected_tasks",
    )
    expected_location_text: models.TextField[str, str] = models.TextField(
        blank=True, default="", db_default=""
    )
    deleted_at: models.DateTimeField[Any, Any] = models.DateTimeField(null=True, blank=True)
    completed_by: models.ForeignKey[Any, Any] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="completed_tasks",
    )
    completed_at: models.DateTimeField[Any, Any] = models.DateTimeField(null=True, blank=True)
    completion_method: models.CharField[str | None, str | None] = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        choices=[(value.value, value.value) for value in CompletionMethod],
    )
    completion_note: models.TextField[str | None, str | None] = models.TextField(
        null=True, blank=True
    )
    block_reason: models.TextField[str | None, str | None] = models.TextField(null=True, blank=True)

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(condition=_nonblank("title"), name="task_title_nonblank"),
            models.CheckConstraint(
                condition=models.Q(status__in=[value.value for value in TaskStatus]),
                name="task_status_valid",
            ),
            models.CheckConstraint(
                condition=(models.Q(status=TaskStatus.BLOCKED.value) & _nonblank("block_reason"))
                | (
                    ~models.Q(status=TaskStatus.BLOCKED.value) & models.Q(block_reason__isnull=True)
                ),
                name="task_block_reason_shape",
            ),
            models.CheckConstraint(
                condition=_task_completion_shape(),
                name="task_completion_shape",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=["status", "assigned_date", "id"],
                name="task_status_date_id_idx",
            ),
            models.Index(
                fields=["created_by", "status", "assigned_date", "id"],
                name="task_creator_status_idx",
            ),
        ]


class TaskAssignee(models.Model):
    task: models.ForeignKey[Task, Task] = models.ForeignKey(
        Task,
        on_delete=models.PROTECT,
        related_name="assignee_links",
    )
    user: models.ForeignKey[Any, Any] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="task_assignments",
    )
    assigned_at: models.DateTimeField[Any, Any] = models.DateTimeField(
        default=Now,
        db_default=Now(),
    )

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(fields=["task", "user"], name="task_assignee_unique")
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["user", "task"], name="task_assignee_user_idx")
        ]


class TaskUpdate(models.Model):
    task: models.ForeignKey[Task, Task] = models.ForeignKey(
        Task,
        on_delete=models.PROTECT,
        related_name="updates",
    )
    user: models.ForeignKey[Any, Any] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="task_updates",
    )
    status: models.CharField[str, str] = models.CharField(
        max_length=16,
        choices=[(value.value, value.value) for value in TaskStatus],
    )
    recorded_at: models.DateTimeField[Any, Any] = models.DateTimeField(
        default=Now,
        db_default=Now(),
    )
    note: models.TextField[str | None, str | None] = models.TextField(null=True, blank=True)
    block_reason: models.TextField[str | None, str | None] = models.TextField(null=True, blank=True)
    completion_method: models.CharField[str | None, str | None] = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        choices=[(value.value, value.value) for value in CompletionMethod],
    )
    completion_note: models.TextField[str | None, str | None] = models.TextField(
        null=True, blank=True
    )
    captured_latitude: models.DecimalField[Any, Any] = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    captured_longitude: models.DecimalField[Any, Any] = models.DecimalField(
        max_digits=10, decimal_places=6, null=True, blank=True
    )
    accuracy_m: models.DecimalField[Any, Any] = models.DecimalField(
        max_digits=12, decimal_places=3, null=True, blank=True
    )
    captured_at: models.DateTimeField[Any, Any] = models.DateTimeField(null=True, blank=True)
    gps_quality: models.CharField[str | None, str | None] = models.CharField(
        max_length=24,
        choices=[(value.value, value.value) for value in GpsQuality],
        null=True,
        blank=True,
    )
    actual_location: models.ForeignKey[Any, Any] = models.ForeignKey(
        "locations.Location",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="actual_task_updates",
    )
    validation_result: models.CharField[str | None, str | None] = models.CharField(
        max_length=24, null=True, blank=True
    )
    resolution_method: models.CharField[str | None, str | None] = models.CharField(
        max_length=24,
        choices=[(value.value, value.value) for value in LocationResolutionMethod],
        null=True,
        blank=True,
    )
    distance_m: models.DecimalField[Any, Any] = models.DecimalField(
        max_digits=12, decimal_places=3, null=True, blank=True
    )
    location_candidates: ArrayField[Any, Any] = ArrayField(
        models.BigIntegerField(), default=list, db_default=[], blank=True
    )

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=models.Q(status__in=[value.value for value in TaskStatus]),
                name="task_update_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(note__isnull=True) | _nonblank("note"),
                name="task_update_note_nonblank",
            ),
            models.CheckConstraint(
                condition=(models.Q(status=TaskStatus.BLOCKED.value) & _nonblank("block_reason"))
                | (
                    ~models.Q(status=TaskStatus.BLOCKED.value) & models.Q(block_reason__isnull=True)
                ),
                name="task_update_block_shape",
            ),
            models.CheckConstraint(
                condition=_update_completion_shape(),
                name="task_update_completion_shape",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["task", "id"], name="task_update_task_id_idx")
        ]


class EvidenceUpload(models.Model):
    id: models.UUIDField[Any, Any] = models.UUIDField(primary_key=True, editable=False)
    task: models.ForeignKey[Task, Task] = models.ForeignKey(
        Task, on_delete=models.PROTECT, related_name="evidence_uploads"
    )
    user: models.ForeignKey[Any, Any] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="task_evidence_uploads",
    )
    object_key: models.TextField[str, str] = models.TextField(unique=True)
    mime: models.CharField[str, str] = models.CharField(max_length=64)
    size_bytes: models.PositiveBigIntegerField[int, int] = models.PositiveBigIntegerField()
    checksum_sha256: models.CharField[str, str] = models.CharField(max_length=64)
    status: models.CharField[str, str] = models.CharField(
        max_length=16,
        choices=[(value.value, value.value) for value in EvidenceUploadStatus],
        default=EvidenceUploadStatus.PENDING.value,
        db_default=EvidenceUploadStatus.PENDING.value,
    )
    created_at: models.DateTimeField[Any, Any] = models.DateTimeField(default=Now, db_default=Now())
    expires_at: models.DateTimeField[Any, Any] = models.DateTimeField()
    bound_update: models.ForeignKey[TaskUpdate, TaskUpdate] = models.ForeignKey(
        TaskUpdate,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="bound_uploads",
    )

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=models.Q(size_bytes__gt=0, size_bytes__lte=5 * 1024 * 1024),
                name="evidence_upload_size_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(status=EvidenceUploadStatus.BOUND.value)
                & models.Q(bound_update__isnull=False)
                | ~models.Q(status=EvidenceUploadStatus.BOUND.value)
                & models.Q(bound_update__isnull=True),
                name="evidence_upload_bound_shape",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["task", "user", "status"], name="evidence_upload_owner_idx"),
            models.Index(fields=["status", "expires_at"], name="evidence_upload_expiry_idx"),
        ]


class TaskPhoto(models.Model):
    task_update: models.ForeignKey[TaskUpdate, TaskUpdate] = models.ForeignKey(
        TaskUpdate, on_delete=models.PROTECT, related_name="photos"
    )
    evidence_upload: models.OneToOneField[EvidenceUpload, EvidenceUpload] = models.OneToOneField(
        EvidenceUpload, on_delete=models.PROTECT, related_name="task_photo"
    )
    object_key: models.TextField[str, str] = models.TextField(unique=True)
    mime: models.CharField[str, str] = models.CharField(max_length=64)
    size_bytes: models.PositiveBigIntegerField[int, int] = models.PositiveBigIntegerField()
    checksum_sha256: models.CharField[str, str] = models.CharField(max_length=64)
    created_at: models.DateTimeField[Any, Any] = models.DateTimeField(default=Now, db_default=Now())


class CompletionIdempotency(models.Model):
    actor: models.ForeignKey[Any, Any] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="task_completion_idempotency",
    )
    task: models.ForeignKey[Task, Task] = models.ForeignKey(
        Task, on_delete=models.PROTECT, related_name="completion_idempotency"
    )
    key: models.CharField[str, str] = models.CharField(max_length=128)
    request_hash: models.CharField[str, str] = models.CharField(max_length=64)
    task_update: models.OneToOneField[TaskUpdate, TaskUpdate] = models.OneToOneField(
        TaskUpdate,
        on_delete=models.PROTECT,
        related_name="completion_idempotency",
    )
    created_at: models.DateTimeField[Any, Any] = models.DateTimeField(default=Now, db_default=Now())

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["actor", "task", "key"], name="task_completion_idempotency_unique"
            )
        ]
