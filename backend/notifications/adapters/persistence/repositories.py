from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

from django.db import connection, models
from django.db.models import Q
from django.utils import timezone

from notifications.application.dto import (
    DeliveryFailure,
    DeliveryPlan,
    Inbox,
    NotificationItem,
    StoredNotification,
    SubscriptionResult,
    SubscriptionUpsert,
)
from notifications.domain.delivery import PushDeliveryState, lease_expiry
from notifications.domain.events import NotificationEventType, NotificationTargetType, Occurrence
from notifications.models import Notification, PushDelivery, PushSubscription


def _stored(row: Notification) -> StoredNotification:
    return StoredNotification(
        id=row.pk,
        public_id=row.public_id,
        recipient_id=int(row.recipient_id),  # type: ignore[attr-defined]
        event_type=NotificationEventType(row.event_type),
        target_type=NotificationTargetType(row.target_type),
        target_id=row.target_id,
        created_at=row.created_at,
        read_at=row.read_at,
    )


class DjangoNotificationRepository:
    def insert_occurrence(self, occurrence: Occurrence) -> tuple[StoredNotification, bool]:
        public_id = uuid.uuid4()
        if connection.vendor == "postgresql":
            return self._insert_postgresql(occurrence, public_id)
        return self._insert_portable(occurrence, public_id)

    @staticmethod
    def _insert_postgresql(
        occurrence: Occurrence, public_id: uuid.UUID
    ) -> tuple[StoredNotification, bool]:
        table = connection.ops.quote_name(Notification._meta.db_table)
        sql = f"""INSERT INTO {table}
                (public_id, recipient_id, event_type, target_type, target_id, dedupe_key,
                 title, occurred_at, created_at, read_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NULL)
                ON CONFLICT ON CONSTRAINT notifications_notification_dedupe_key_key DO NOTHING
                RETURNING id"""
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                [
                    public_id,
                    occurrence.recipient_id,
                    occurrence.event_type.value,
                    occurrence.target_type.value,
                    occurrence.target_id,
                    occurrence.dedupe_key,
                    occurrence.title,
                    occurrence.occurred_at,
                    timezone.now(),
                ],
            )
            result = cursor.fetchone()
        if result:
            return _stored(Notification.objects.get(pk=result[0])), True
        return _stored(Notification.objects.get(dedupe_key=occurrence.dedupe_key)), False

    @staticmethod
    def _insert_portable(
        occurrence: Occurrence, public_id: uuid.UUID
    ) -> tuple[StoredNotification, bool]:
        row, created = Notification.objects.get_or_create(
            dedupe_key=occurrence.dedupe_key,
            defaults={
                "public_id": public_id,
                "recipient_id": occurrence.recipient_id,
                "event_type": occurrence.event_type.value,
                "target_type": occurrence.target_type.value,
                "target_id": occurrence.target_id,
                "title": occurrence.title,
                "occurred_at": occurrence.occurred_at,
            },
        )
        return _stored(row), created

    def inbox(self, recipient_id: int) -> Inbox:
        rows = list(
            Notification.objects.filter(recipient_id=recipient_id).order_by("-created_at", "-id")
        )
        return Inbox(
            tuple(
                NotificationItem(
                    row.public_id,
                    NotificationEventType(row.event_type),
                    row.title,
                    row.created_at,
                    row.read_at,
                )
                for row in rows
            ),
            sum(row.read_at is None for row in rows),
        )

    def get_owned(self, recipient_id: int, public_id: UUID) -> StoredNotification | None:
        row = Notification.objects.filter(recipient_id=recipient_id, public_id=public_id).first()
        return _stored(row) if row else None

    def mark_read(
        self, recipient_id: int, public_id: UUID, read_at: datetime
    ) -> StoredNotification | None:
        Notification.objects.filter(
            recipient_id=recipient_id, public_id=public_id, read_at__isnull=True
        ).update(read_at=read_at)
        return self.get_owned(recipient_id, public_id)


class DjangoSubscriptionRepository:
    def active_for_user(self, user_id: int) -> tuple[PushSubscription, ...]:
        return tuple(
            PushSubscription.objects.filter(user_id=user_id, is_active=True).order_by("id")
        )

    def upsert(self, value: SubscriptionUpsert) -> SubscriptionResult:
        self._lock_endpoint(value.endpoint_hash)
        rows = list(
            PushSubscription.objects.select_for_update()
            .filter(endpoint_hash=value.endpoint_hash)
            .order_by("id")
        )
        for locked_row in rows:
            if locked_row.is_active and locked_row.user_id != value.user_id:  # type: ignore[attr-defined]
                self._revoke_row(locked_row, value.now)
        selected = next(
            (
                item
                for item in rows
                if item.user_id == value.user_id  # type: ignore[attr-defined]
            ),
            None,
        )
        selected = self._activate(value, selected)
        return SubscriptionResult(selected.public_id, selected.is_active, selected.created_at)

    @staticmethod
    def _lock_endpoint(endpoint_hash: str) -> None:
        """Serialize an endpoint even when no row exists yet."""
        if connection.vendor != "postgresql":
            return
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", [endpoint_hash])

    @staticmethod
    def _activate(value: SubscriptionUpsert, selected: PushSubscription | None) -> PushSubscription:
        if selected is None:
            return PushSubscription.objects.create(
                user_id=value.user_id,
                endpoint_hash=value.endpoint_hash,
                encrypted_subscription=value.encrypted_subscription,
                user_agent_family=value.user_agent_family,
            )
        selected.encrypted_subscription = value.encrypted_subscription
        selected.user_agent_family = value.user_agent_family
        selected.is_active = True
        selected.revoked_at = None
        selected.save(
            update_fields=["encrypted_subscription", "user_agent_family", "is_active", "revoked_at"]
        )
        return selected

    def revoke_owned(self, user_id: int, public_id: UUID, now: datetime) -> bool:
        row = (
            PushSubscription.objects.select_for_update()
            .filter(user_id=user_id, public_id=public_id)
            .first()
        )
        if row is None:
            return False
        if row.is_active:
            self._revoke_row(row, now)
        return True

    def revoke_all(self, user_id: int, now: datetime) -> int:
        rows = PushSubscription.objects.select_for_update().filter(user_id=user_id, is_active=True)
        count = 0
        for row in rows:
            self._revoke_row(row, now)
            count += 1
        return count

    @staticmethod
    def _revoke_row(row: PushSubscription, now: datetime) -> None:
        row.is_active = False
        row.revoked_at = now
        row.save(update_fields=["is_active", "revoked_at"])
        PushDelivery.objects.filter(
            subscription=row,
            state__in=[PushDeliveryState.PENDING.value, PushDeliveryState.LEASED.value],
        ).update(state=PushDeliveryState.SUPPRESSED.value, lease_expires_at=None, leased_by=None)


class DjangoDeliveryRepository:
    def get(self, delivery_id: int) -> PushDelivery | None:
        return (
            PushDelivery.objects.select_related("notification", "subscription")
            .filter(pk=delivery_id)
            .first()
        )

    def materialize(self, plan: DeliveryPlan) -> None:
        PushDelivery.objects.get_or_create(
            notification_id=plan.notification_id,
            subscription_id=plan.subscription_id,
            defaults={
                "not_before": plan.not_before,
                "expires_at": plan.expires_at,
                "next_attempt_at": plan.not_before,
                "collapse_key": plan.collapse_key,
            },
        )

    def candidate_id(self, now: datetime) -> int | None:
        return (
            PushDelivery.objects.filter(
                Q(state=PushDeliveryState.PENDING.value)
                | Q(state=PushDeliveryState.LEASED.value, lease_expires_at__lte=now),
                not_before__lte=now,
                next_attempt_at__lte=now,
            )
            .order_by("id")
            .values_list("id", flat=True)
            .first()
        )

    def claim(self, delivery_id: int, worker_id: str, now: datetime) -> PushDelivery | None:
        row = (
            PushDelivery.objects.select_for_update(skip_locked=True).filter(pk=delivery_id).first()
        )
        if (
            row is None
            or row.expires_at <= now
            or row.not_before > now
            or row.next_attempt_at > now
        ):
            if row is not None and row.expires_at <= now:
                self.expire(row)
            return None
        if (
            row.state == PushDeliveryState.LEASED.value
            and row.lease_expires_at
            and row.lease_expires_at > now
        ):
            return None
        if row.state not in {PushDeliveryState.PENDING.value, PushDeliveryState.LEASED.value}:
            return None
        row.state = PushDeliveryState.LEASED.value
        row.leased_by = worker_id
        row.lease_expires_at = lease_expiry(now)
        row.save(update_fields=["state", "leased_by", "lease_expires_at"])
        return row

    def suppress(self, delivery_id: int) -> None:
        PushDelivery.objects.filter(
            pk=delivery_id,
            state__in=[PushDeliveryState.PENDING.value, PushDeliveryState.LEASED.value],
        ).update(state=PushDeliveryState.SUPPRESSED.value, leased_by=None, lease_expires_at=None)

    def suppress_target(
        self, target_type: str, target_id: int, recipient_ids: tuple[int, ...] = ()
    ) -> int:
        query = PushDelivery.objects.filter(
            notification__target_type=target_type,
            notification__target_id=target_id,
            state__in=[PushDeliveryState.PENDING.value, PushDeliveryState.LEASED.value],
        )
        if recipient_ids:
            query = query.filter(notification__recipient_id__in=recipient_ids)
        return query.update(
            state=PushDeliveryState.SUPPRESSED.value, leased_by=None, lease_expires_at=None
        )

    @staticmethod
    def expire(row: PushDelivery) -> None:
        row.state = PushDeliveryState.EXPIRED.value
        row.leased_by = None
        row.lease_expires_at = None
        row.save(update_fields=["state", "leased_by", "lease_expires_at"])

    def finalize_success(self, delivery_id: int, worker_id: str, attempted_at: datetime) -> bool:
        count = PushDelivery.objects.filter(
            pk=delivery_id, state=PushDeliveryState.LEASED.value, leased_by=worker_id
        ).update(
            state=PushDeliveryState.DELIVERED.value,
            attempted_at=attempted_at,
            leased_by=None,
            lease_expires_at=None,
            failure_code=None,
        )
        if count:
            row = PushDelivery.objects.get(pk=delivery_id)
            PushSubscription.objects.filter(
                pk=row.subscription_id  # type: ignore[attr-defined]
            ).update(last_used_at=attempted_at)
        return bool(count)

    def defer_quiet(self, delivery_id: int, release_at: datetime) -> None:
        PushDelivery.objects.filter(
            pk=delivery_id,
            state__in=[PushDeliveryState.PENDING.value, PushDeliveryState.LEASED.value],
        ).update(
            state=PushDeliveryState.PENDING.value,
            not_before=release_at,
            next_attempt_at=release_at,
            leased_by=None,
            lease_expires_at=None,
        )

    def expire_id(self, delivery_id: int) -> None:
        PushDelivery.objects.filter(
            pk=delivery_id,
            state__in=[PushDeliveryState.PENDING.value, PushDeliveryState.LEASED.value],
        ).update(
            state=PushDeliveryState.EXPIRED.value,
            leased_by=None,
            lease_expires_at=None,
        )

    def finalize_failure(self, failure: DeliveryFailure) -> bool:
        update: dict[str, Any] = {
            "attempted_at": failure.attempted_at,
            "failure_code": failure.failure_code.value,
            "leased_by": None,
            "lease_expires_at": None,
            "attempt_count": models.F("attempt_count") + 1,
        }
        update["state"] = (
            PushDeliveryState.PENDING.value
            if failure.next_attempt_at
            else PushDeliveryState.SUPPRESSED.value
        )
        if failure.next_attempt_at:
            update["next_attempt_at"] = failure.next_attempt_at
        return bool(
            PushDelivery.objects.filter(
                pk=failure.delivery_id,
                state=PushDeliveryState.LEASED.value,
                leased_by=failure.worker_id,
            ).update(**update)
        )

    def revoke_permanent(self, subscription_id: int, now: datetime) -> None:
        row = PushSubscription.objects.select_for_update().filter(pk=subscription_id).first()
        if row is not None and row.is_active:
            DjangoSubscriptionRepository._revoke_row(row, now)
