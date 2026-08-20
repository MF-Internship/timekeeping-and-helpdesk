from __future__ import annotations

from typing import Protocol
from uuid import UUID

from audit.domain.relay import OutboxMessage, RelayConfig


class OutboxRelayRepository(Protocol):
    def claim_batch(self, *, worker_id: str, config: RelayConfig) -> tuple[OutboxMessage, ...]: ...

    def mark_published(self, message: OutboxMessage) -> bool: ...

    def mark_failed(self, message: OutboxMessage, reason: object, config: RelayConfig) -> bool: ...

    def mark_processed(self, *, consumer: str, event_id: UUID) -> bool: ...


class OutboxTransport(Protocol):
    def publish(self, message: OutboxMessage) -> None: ...


class OutboxAlertSink(Protocol):
    def dead_letter(self, message: OutboxMessage, reason: str) -> None: ...
