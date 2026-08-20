from __future__ import annotations

import uuid
from typing import Any, ClassVar

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    actor: models.ForeignKey[Any, Any] = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT
    )
    action: models.CharField[str, str] = models.CharField(max_length=100)
    target_type: models.CharField[str, str] = models.CharField(max_length=64)
    target_id: models.CharField[str, str] = models.CharField(max_length=64)
    before: models.JSONField[dict[str, Any], dict[str, Any]] = models.JSONField(default=dict)
    after: models.JSONField[dict[str, Any], dict[str, Any]] = models.JSONField(default=dict)
    recorded_at: models.DateTimeField[Any, Any] = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["actor", "-recorded_at"], name="audit_actor_time_idx"),
            models.Index(
                fields=["target_type", "target_id", "-recorded_at"],
                name="audit_target_time_idx",
            ),
        ]


class OutboxEvent(models.Model):
    class PublishState(models.TextChoices):
        PENDING = "PENDING"
        PUBLISHED = "PUBLISHED"
        DEAD_LETTER = "DEAD_LETTER"

    event_id: models.UUIDField[Any, Any] = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False
    )
    event_type: models.CharField[str, str] = models.CharField(max_length=100)
    schema_version: models.PositiveIntegerField[int, int] = models.PositiveIntegerField(
        default=1, db_default=1
    )
    aggregate_type: models.CharField[str, str] = models.CharField(max_length=64)
    aggregate_id: models.CharField[str, str] = models.CharField(max_length=64)
    aggregate_version: models.PositiveIntegerField[int, int] = models.PositiveIntegerField()
    payload: models.JSONField[dict[str, Any], dict[str, Any]] = models.JSONField(default=dict)
    created_at: models.DateTimeField[Any, Any] = models.DateTimeField(auto_now_add=True)
    request_id: models.CharField[str, str] = models.CharField(
        max_length=64, default="", db_default=""
    )
    correlation_id: models.CharField[str, str] = models.CharField(
        max_length=64, default="", db_default=""
    )
    publish_state: models.CharField[str, str] = models.CharField(
        max_length=16,
        choices=PublishState.choices,
        default=PublishState.PENDING,
        db_default="PENDING",
    )
    published_at: models.DateTimeField[Any, Any] = models.DateTimeField(null=True, blank=True)
    lease_expires_at: models.DateTimeField[Any, Any] = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["aggregate_type", "aggregate_id", "aggregate_version"],
                name="audit_outbox_aggregate_version_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(schema_version__gte=1),
                name="audit_outbox_schema_version_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(aggregate_version__gte=1),
                name="audit_outbox_aggregate_version_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(publish_state__in=["PENDING", "PUBLISHED", "DEAD_LETTER"]),
                name="audit_outbox_publish_state_valid",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=["publish_state", "created_at", "id"],
                name="audit_outbox_pending_idx",
            )
        ]
