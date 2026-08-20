from __future__ import annotations

import logging
from dataclasses import dataclass

from audit.domain.relay import OutboxMessage
from core.event_payload import sanitize_failure_reason

LOGGER = logging.getLogger("operations.outbox")


class DisabledOutboxTransport:
    def publish(self, message: OutboxMessage) -> None:
        del message
        raise RuntimeError("OUTBOX_RELAY_TRANSPORT disabled")


class LoggingOutboxTransport:
    def publish(self, message: OutboxMessage) -> None:
        LOGGER.info(
            "outbox event published event_id=%s aggregate=%s/%s version=%s",
            message.event_id,
            message.aggregate_type,
            message.aggregate_id,
            message.aggregate_version,
        )


@dataclass(frozen=True, slots=True)
class LoggingOutboxAlertSink:
    logger: logging.Logger = LOGGER

    def dead_letter(self, message: OutboxMessage, reason: str) -> None:
        self.logger.warning(
            "outbox dead_letter event_id=%s aggregate=%s/%s version=%s attempts=%s reason=%s",
            message.event_id,
            message.aggregate_type,
            message.aggregate_id,
            message.aggregate_version,
            message.attempt_count,
            sanitize_failure_reason(reason),
        )


def transport_from_name(name: str) -> DisabledOutboxTransport | LoggingOutboxTransport:
    if name == "disabled":
        return DisabledOutboxTransport()
    if name == "logging":
        return LoggingOutboxTransport()
    raise ValueError("OUTBOX_RELAY_TRANSPORT")
