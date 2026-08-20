from __future__ import annotations

import uuid
from typing import Any, ClassVar

from django.conf import settings
from django.db import models

from notifications.domain.delivery import PushDeliveryState, PushFailureCode
from notifications.domain.events import NotificationEventType, NotificationTargetType


class Notification(models.Model):
    public_id: models.UUIDField[uuid.UUID, uuid.UUID] = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False
    )
    recipient: models.ForeignKey[Any, Any] = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="notifications"
    )
    event_type: models.CharField[str, str] = models.CharField(
        max_length=64, choices=[(value.value, value.value) for value in NotificationEventType]
    )
    target_type: models.CharField[str, str] = models.CharField(
        max_length=32, choices=[(value.value, value.value) for value in NotificationTargetType]
    )
    target_id: models.PositiveBigIntegerField[int, int] = models.PositiveBigIntegerField()
    dedupe_key: models.CharField[str, str] = models.CharField(max_length=255, unique=True)
    title: models.CharField[str, str] = models.CharField(max_length=160)
    occurred_at: models.DateTimeField[Any, Any] = models.DateTimeField()
    created_at: models.DateTimeField[Any, Any] = models.DateTimeField(auto_now_add=True)
    read_at: models.DateTimeField[Any, Any] = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=models.Q(event_type__in=[value.value for value in NotificationEventType]),
                name="notification_event_type_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    target_type__in=[value.value for value in NotificationTargetType]
                ),
                name="notification_target_type_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(target_id__gt=0), name="notification_target_id_positive"
            ),
            models.CheckConstraint(
                condition=~models.Q(dedupe_key__regex=r"^\s*$"), name="notification_dedupe_nonblank"
            ),
            models.CheckConstraint(
                condition=~models.Q(title__regex=r"^\s*$"), name="notification_title_nonblank"
            ),
            models.CheckConstraint(
                condition=models.Q(read_at__isnull=True)
                | models.Q(read_at__gte=models.F("created_at")),
                name="notification_read_time_valid",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=["recipient", "-created_at", "-id"], name="notif_owner_created_idx"
            ),
            models.Index(
                fields=["recipient", "-created_at", "-id"],
                condition=models.Q(read_at__isnull=True),
                name="notif_owner_unread_idx",
            ),
            models.Index(
                fields=["target_type", "target_id", "recipient"], name="notif_target_owner_idx"
            ),
        ]


class PushSubscription(models.Model):
    public_id: models.UUIDField[uuid.UUID, uuid.UUID] = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False
    )
    user: models.ForeignKey[Any, Any] = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="push_subscriptions"
    )
    endpoint_hash: models.CharField[str, str] = models.CharField(max_length=64)
    encrypted_subscription: models.BinaryField[bytes, bytes] = models.BinaryField()
    user_agent_family: models.CharField[str, str] = models.CharField(max_length=32)
    is_active: models.BooleanField[bool, bool] = models.BooleanField(default=True, db_default=True)
    revoked_at: models.DateTimeField[Any, Any] = models.DateTimeField(null=True, blank=True)
    last_used_at: models.DateTimeField[Any, Any] = models.DateTimeField(null=True, blank=True)
    created_at: models.DateTimeField[Any, Any] = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["endpoint_hash"],
                condition=models.Q(is_active=True),
                name="push_subscription_active_endpoint_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(endpoint_hash__regex=r"^[0-9a-f]{64}$"),
                name="push_subscription_hash_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(is_active=True, revoked_at__isnull=True)
                    | models.Q(is_active=False, revoked_at__isnull=False)
                ),
                name="push_subscription_state_valid",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["user", "is_active", "id"], name="push_sub_owner_active_idx"),
            models.Index(fields=["endpoint_hash"], name="push_sub_endpoint_hash_idx"),
        ]


class PushDelivery(models.Model):
    notification: models.ForeignKey[Notification, Notification] = models.ForeignKey(
        Notification, on_delete=models.PROTECT, related_name="push_deliveries"
    )
    subscription: models.ForeignKey[PushSubscription, PushSubscription] = models.ForeignKey(
        PushSubscription, on_delete=models.PROTECT, related_name="deliveries"
    )
    state: models.CharField[str, str] = models.CharField(
        max_length=16,
        choices=[(value.value, value.value) for value in PushDeliveryState],
        default=PushDeliveryState.PENDING.value,
        db_default=PushDeliveryState.PENDING.value,
    )
    not_before: models.DateTimeField[Any, Any] = models.DateTimeField()
    expires_at: models.DateTimeField[Any, Any] = models.DateTimeField()
    collapse_key: models.CharField[str, str] = models.CharField(max_length=32)
    attempt_count: models.PositiveIntegerField[int, int] = models.PositiveIntegerField(
        default=0, db_default=0
    )
    next_attempt_at: models.DateTimeField[Any, Any] = models.DateTimeField()
    lease_expires_at: models.DateTimeField[Any, Any] = models.DateTimeField(null=True, blank=True)
    leased_by: models.CharField[str | None, str | None] = models.CharField(
        max_length=64, null=True, blank=True
    )
    attempted_at: models.DateTimeField[Any, Any] = models.DateTimeField(null=True, blank=True)
    failure_code: models.CharField[str | None, str | None] = models.CharField(
        max_length=40,
        choices=[(value.value, value.value) for value in PushFailureCode],
        null=True,
        blank=True,
    )
    created_at: models.DateTimeField[Any, Any] = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["notification", "subscription"],
                name="push_delivery_notification_subscription_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(state__in=[value.value for value in PushDeliveryState]),
                name="push_delivery_state_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(not_before__lt=models.F("expires_at")),
                name="push_delivery_window_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(next_attempt_at__lte=models.F("expires_at")),
                name="push_delivery_retry_time_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        state=PushDeliveryState.LEASED.value,
                        lease_expires_at__isnull=False,
                        leased_by__isnull=False,
                    )
                    | (
                        ~models.Q(state=PushDeliveryState.LEASED.value)
                        & models.Q(lease_expires_at__isnull=True, leased_by__isnull=True)
                    )
                ),
                name="push_delivery_lease_shape_valid",
            ),
            models.CheckConstraint(
                condition=~models.Q(state=PushDeliveryState.DELIVERED.value)
                | models.Q(attempted_at__isnull=False),
                name="push_delivery_delivered_attempt_valid",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=["state", "next_attempt_at", "expires_at", "id"],
                name="push_delivery_due_idx",
            ),
            models.Index(
                fields=["subscription", "state", "id"], name="push_delivery_sub_state_idx"
            ),
            models.Index(
                fields=["notification", "state", "id"], name="push_delivery_notif_state_idx"
            ),
        ]
