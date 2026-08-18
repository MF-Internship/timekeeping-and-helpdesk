from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from audit.ports.recording import AuditEntry, AuditRecorder, OutboxRecord


@dataclass(frozen=True, slots=True)
class EvidenceRequest:
    actor_id: int
    event_type: StrEnum
    aggregate_type: str
    aggregate_id: int | str
    before: dict[str, Any]
    after: dict[str, Any]
    outbox_payload: dict[str, Any]


def location_outbox_payload(
    location: Any,
    changed_fields: list[str],
    warning_codes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "location_id": location.id,
        "code": location.code,
        "version": location.version,
        "changed_fields": sorted(changed_fields),
        "warning_codes": sorted(warning_codes or []),
    }


def config_outbox_payload(
    changed_fields: list[str], warning_codes: list[str] | None = None
) -> dict[str, Any]:
    return {
        "config_id": 1,
        "changed_fields": sorted(changed_fields),
        "warning_codes": sorted(warning_codes or []),
        "schema_version": 1,
    }


def holiday_outbox_payload(holiday_id: int, holiday_date: str) -> dict[str, Any]:
    return {"holiday_id": holiday_id, "date": holiday_date}


def append_evidence(recorder: AuditRecorder, request: EvidenceRequest) -> None:
    target_id = str(request.aggregate_id)
    recorder.append_audit_entry(
        AuditEntry(
            request.actor_id,
            request.event_type,
            request.aggregate_type,
            target_id,
            request.before,
            request.after,
        )
    )
    recorder.append_outbox_event(
        OutboxRecord(
            request.event_type,
            request.aggregate_type,
            target_id,
            {"action": request.event_type.value, **request.outbox_payload},
        )
    )
