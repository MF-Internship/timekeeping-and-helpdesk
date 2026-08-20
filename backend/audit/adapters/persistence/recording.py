from __future__ import annotations

from django.db.models import Max

from audit.domain.records import AuditEntry, OutboxRecord
from audit.models import AuditLog, OutboxEvent
from core.correlation import get_correlation
from core.event_payload import validate_event_payload


class DjangoAuditRecorder:
    def append_audit_entry(self, entry: AuditEntry) -> None:
        validate_event_payload(entry.before)
        validate_event_payload(entry.after)
        AuditLog.objects.create(
            actor_id=entry.actor_id,
            action=entry.action.value,
            target_type=entry.target_type,
            target_id=entry.target_id,
            before=entry.before,
            after=entry.after,
        )

    def append_outbox_event(self, event: OutboxRecord) -> None:
        validate_event_payload(event.payload)
        request_id, correlation_id = get_correlation()
        latest = (
            OutboxEvent.objects.filter(
                aggregate_type=event.aggregate_type,
                aggregate_id=event.aggregate_id,
            ).aggregate(value=Max("aggregate_version"))["value"]
            or 0
        )
        OutboxEvent.objects.create(
            event_type=event.event_type.value,
            schema_version=event.schema_version,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            aggregate_version=latest + 1,
            payload=event.payload,
            request_id=request_id,
            correlation_id=correlation_id,
        )
