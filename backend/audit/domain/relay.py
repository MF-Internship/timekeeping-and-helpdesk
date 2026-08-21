from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

from core.event_payload import sanitize_failure_reason


class OutboxPublishState(StrEnum):
    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"
    DEAD_LETTER = "DEAD_LETTER"


@dataclass(frozen=True, slots=True)
class RelayConfig:
    batch_size: int = 100
    lease_seconds: int = 60
    max_attempts: int = 12
    backoff_base_seconds: int = 30
    backoff_max_seconds: int = 3600

    def __post_init__(self) -> None:
        for name, value in (
            ("batch_size", self.batch_size),
            ("lease_seconds", self.lease_seconds),
            ("max_attempts", self.max_attempts),
            ("backoff_base_seconds", self.backoff_base_seconds),
            ("backoff_max_seconds", self.backoff_max_seconds),
        ):
            if value < 1:
                raise ValueError(f"{name} must be positive")


@dataclass(frozen=True, slots=True)
class OutboxMessage:
    row_id: int
    event_id: UUID
    event_type: str
    schema_version: int
    aggregate_type: str
    aggregate_id: str
    aggregate_version: int
    payload: dict[str, Any]
    request_id: str
    correlation_id: str
    attempt_count: int
    leased_by: str
    lease_expires_at: datetime


def lease_expires_at(now: datetime, config: RelayConfig) -> datetime:
    return now + timedelta(seconds=config.lease_seconds)


def retry_after(now: datetime, attempt_count: int, config: RelayConfig) -> datetime:
    delay = min(
        config.backoff_base_seconds * (2 ** max(0, attempt_count - 1)),
        config.backoff_max_seconds,
    )
    return now + timedelta(seconds=delay)


def safe_transport_error(reason: object) -> str:
    return sanitize_failure_reason(reason)
