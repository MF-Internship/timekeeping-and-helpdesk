from __future__ import annotations

from typing import Any
from uuid import UUID

from django.db import connection, models, transaction
from django.utils import timezone

from audit.domain.relay import (
    OutboxMessage,
    OutboxPublishState,
    RelayConfig,
    lease_expires_at,
    retry_after,
    safe_transport_error,
)
from audit.models import OutboxEvent, ProcessedEvent


def _message(row: OutboxEvent) -> OutboxMessage:
    if row.leased_by is None or row.lease_expires_at is None:
        raise ValueError("outbox event is not leased")
    return OutboxMessage(
        row_id=row.pk,
        event_id=row.event_id,
        event_type=row.event_type,
        schema_version=row.schema_version,
        aggregate_type=row.aggregate_type,
        aggregate_id=row.aggregate_id,
        aggregate_version=row.aggregate_version,
        payload=row.payload,
        request_id=row.request_id,
        correlation_id=row.correlation_id,
        attempt_count=row.attempt_count,
        leased_by=row.leased_by,
        lease_expires_at=row.lease_expires_at,
    )


class DjangoOutboxRelayRepository:
    def claim_batch(self, *, worker_id: str, config: RelayConfig) -> tuple[OutboxMessage, ...]:
        now = timezone.now()
        expires_at = lease_expires_at(now, config)
        with transaction.atomic():
            rows = list(
                OutboxEvent.objects.select_for_update(skip_locked=True)
                .filter(publish_state=OutboxPublishState.PENDING.value)
                .filter(models.Q(next_attempt_at__isnull=True) | models.Q(next_attempt_at__lte=now))
                .filter(
                    models.Q(lease_expires_at__isnull=True)
                    | models.Q(lease_expires_at__lte=now)
                )
                .order_by("created_at", "id")[: config.batch_size]
            )
            ids = [row.pk for row in rows]
            if ids:
                OutboxEvent.objects.filter(pk__in=ids).update(
                    leased_by=worker_id,
                    lease_expires_at=expires_at,
                    attempt_count=models.F("attempt_count") + 1,
                    last_error="",
                )
            locked = list(OutboxEvent.objects.filter(pk__in=ids).order_by("created_at", "id"))
            return tuple(_message(row) for row in locked)

    def mark_published(self, message: OutboxMessage) -> bool:
        now = timezone.now()
        return bool(
            OutboxEvent.objects.filter(
                pk=message.row_id,
                publish_state=OutboxPublishState.PENDING.value,
                leased_by=message.leased_by,
                lease_expires_at=message.lease_expires_at,
            ).update(
                publish_state=OutboxPublishState.PUBLISHED.value,
                published_at=now,
                leased_by=None,
                lease_expires_at=None,
                last_error="",
            )
        )

    def mark_failed(self, message: OutboxMessage, reason: object, config: RelayConfig) -> bool:
        now = timezone.now()
        update: dict[str, Any] = {
            "leased_by": None,
            "lease_expires_at": None,
            "last_error": safe_transport_error(reason),
        }
        if message.attempt_count >= config.max_attempts:
            update["publish_state"] = OutboxPublishState.DEAD_LETTER.value
            update["next_attempt_at"] = None
        else:
            update["publish_state"] = OutboxPublishState.PENDING.value
            update["next_attempt_at"] = retry_after(now, message.attempt_count, config)
        return bool(
            OutboxEvent.objects.filter(
                pk=message.row_id,
                publish_state=OutboxPublishState.PENDING.value,
                leased_by=message.leased_by,
                lease_expires_at=message.lease_expires_at,
            ).update(**update)
        )

    def mark_processed(self, *, consumer: str, event_id: UUID) -> bool:
        if connection.vendor == "postgresql":
            return self._mark_processed_postgresql(consumer, event_id)
        _, created = ProcessedEvent.objects.get_or_create(consumer=consumer, event_id=event_id)
        return created

    @staticmethod
    def _mark_processed_postgresql(consumer: str, event_id: UUID) -> bool:
        table = connection.ops.quote_name(ProcessedEvent._meta.db_table)
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO {table} (consumer, event_id, processed_at)
                VALUES (%s, %s, %s)
                ON CONFLICT ON CONSTRAINT audit_processed_event_unique DO NOTHING
                RETURNING id
                """,
                [consumer, event_id, timezone.now()],
            )
            return cursor.fetchone() is not None
