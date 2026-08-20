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
    processed = _prune_processed(repository, now, batch_size)
    published = _prune_published(repository, now, batch_size)
    dead_letter = _prune_dead_letter(repository, now, batch_size)
    return RetentionResult(processed, published, dead_letter)


def _prune_processed(repository: RetentionRepository, now: datetime, batch_size: int) -> int:
    cutoff = now - timedelta(days=PROCESSED_EVENT_RETENTION_DAYS)
    return _prune(
        lambda: repository.delete_processed_events(older_than=cutoff, limit=batch_size),
        batch_size,
    )


def _prune_published(repository: RetentionRepository, now: datetime, batch_size: int) -> int:
    cutoff = now - timedelta(days=OUTBOX_PUBLISHED_RETENTION_DAYS)
    return _prune(
        lambda: repository.delete_published_outbox(older_than=cutoff, limit=batch_size),
        batch_size,
    )


def _prune_dead_letter(repository: RetentionRepository, now: datetime, batch_size: int) -> int:
    cutoff = now - timedelta(days=OUTBOX_DEAD_LETTER_RETENTION_DAYS)
    return _prune(
        lambda: repository.delete_dead_letter_outbox(older_than=cutoff, limit=batch_size),
        batch_size,
    )


def _prune(delete_batch: Callable[[], int], batch_size: int) -> int:
    total = 0
    while True:
        deleted = delete_batch()
        total += deleted
        if deleted < batch_size:
            return total
