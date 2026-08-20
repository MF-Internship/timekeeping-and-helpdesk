from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from operations.ports.retention import RetentionRepository

PROCESSED_EVENT_RETENTION_DAYS = 30
OUTBOX_PUBLISHED_RETENTION_DAYS = 30
OUTBOX_DEAD_LETTER_RETENTION_DAYS = 90


@dataclass(frozen=True, slots=True)
class RetentionResult:
    processed_event: int
    outbox_published: int
    outbox_dead_letter: int


def prune_retention(
    repository: RetentionRepository,
    *,
    now: datetime,
    batch_size: int,
) -> RetentionResult:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    return RetentionResult(
        _prune(
            lambda: repository.delete_processed_events(
                older_than=now - timedelta(days=PROCESSED_EVENT_RETENTION_DAYS),
                limit=batch_size,
            ),
            batch_size,
        ),
        _prune(
            lambda: repository.delete_published_outbox(
                older_than=now - timedelta(days=OUTBOX_PUBLISHED_RETENTION_DAYS),
                limit=batch_size,
            ),
            batch_size,
        ),
        _prune(
            lambda: repository.delete_dead_letter_outbox(
                older_than=now - timedelta(days=OUTBOX_DEAD_LETTER_RETENTION_DAYS),
                limit=batch_size,
            ),
            batch_size,
        ),
    )


def _prune(delete_batch: Callable[[], int], batch_size: int) -> int:
    total = 0
    while True:
        deleted = delete_batch()
        total += deleted
        if deleted < batch_size:
            return total
