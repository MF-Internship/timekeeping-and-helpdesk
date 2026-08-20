from typing import Protocol

from audit.domain.records import (
    AuditAction,
    AuditEntry,
    IdentityEventType,
    OutboxRecord,
)

__all__ = [
    "AuditAction",
    "AuditEntry",
    "AuditRecorder",
    "IdentityEventType",
    "OutboxRecord",
]


class AuditRecorder(Protocol):
    def append_audit_entry(self, entry: AuditEntry) -> None: ...

    def append_outbox_event(self, event: OutboxRecord) -> None: ...
