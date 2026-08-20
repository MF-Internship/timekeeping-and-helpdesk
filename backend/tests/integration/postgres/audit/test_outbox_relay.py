from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from django.db import close_old_connections, transaction
from django.utils import timezone

from audit.adapters.persistence.outbox_relay import DjangoOutboxRelayRepository
from audit.domain.relay import OutboxPublishState, RelayConfig
from audit.models import OutboxEvent, ProcessedEvent


def create_event(index: int) -> OutboxEvent:
    return OutboxEvent.objects.create(
        event_type="identity.user.created",
        aggregate_type="User",
        aggregate_id=str(index),
        aggregate_version=1,
        payload={"role": "HELPDESK"},
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.integration
def test_concurrent_workers_claim_disjoint_batches_with_skip_locked() -> None:
    for index in range(6):
        create_event(index)
    barrier = Barrier(2)
    repository = DjangoOutboxRelayRepository()

    def claim(worker_id: str) -> set[int]:
        close_old_connections()
        try:
            barrier.wait()
            return {
                item.row_id
                for item in repository.claim_batch(
                    worker_id=worker_id,
                    config=RelayConfig(batch_size=3, lease_seconds=60),
                )
            }
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = list(executor.map(claim, ("worker-a", "worker-b")))

    assert first
    assert second
    assert first.isdisjoint(second)
    assert len(first | second) == 6
    assert set(OutboxEvent.objects.values_list("attempt_count", flat=True)) == {1}


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.integration
def test_expired_lease_is_reclaimable() -> None:
    event = create_event(1)
    event.leased_by = "dead-worker"
    event.lease_expires_at = timezone.now() - timedelta(minutes=5)
    event.attempt_count = 1
    event.save(update_fields=["leased_by", "lease_expires_at", "attempt_count"])

    claimed = DjangoOutboxRelayRepository().claim_batch(
        worker_id="new-worker",
        config=RelayConfig(batch_size=1, lease_seconds=60),
    )

    assert len(claimed) == 1
    event.refresh_from_db()
    assert event.leased_by == "new-worker"
    assert event.attempt_count == 2


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.integration
def test_publish_success_is_conditional_on_lease_identity() -> None:
    event = create_event(1)
    repository = DjangoOutboxRelayRepository()
    leased = repository.claim_batch(worker_id="worker", config=RelayConfig(batch_size=1))[0]
    assert repository.mark_published(leased)
    event.refresh_from_db()
    assert event.publish_state == OutboxPublishState.PUBLISHED.value
    assert event.published_at is not None
    assert event.leased_by is None
    assert not repository.mark_published(leased)


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.integration
def test_failure_retry_dead_letter_and_sanitized_error_are_persisted() -> None:
    event = create_event(1)
    repository = DjangoOutboxRelayRepository()
    config = RelayConfig(
        batch_size=1,
        max_attempts=2,
        backoff_base_seconds=10,
        backoff_max_seconds=10,
    )
    reason = "bad https://signed.example/?token=secret at 10.785850,106.700000"

    first = repository.claim_batch(worker_id="worker", config=config)[0]
    assert repository.mark_failed(first, reason, config)
    event.refresh_from_db()
    assert event.publish_state == OutboxPublishState.PENDING.value
    assert event.next_attempt_at is not None
    assert event.lease_expires_at is None and event.leased_by is None
    assert "https://" not in event.last_error
    assert "token=" not in event.last_error
    assert "10.785850" not in event.last_error

    event.next_attempt_at = timezone.now() - timedelta(seconds=1)
    event.save(update_fields=["next_attempt_at"])
    second = repository.claim_batch(worker_id="worker", config=config)[0]
    assert second.attempt_count == 2
    assert repository.mark_failed(second, reason, config)
    event.refresh_from_db()
    assert event.publish_state == OutboxPublishState.DEAD_LETTER.value
    assert event.next_attempt_at is None
    assert event.attempt_count == 2


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.integration
def test_consumer_dedupe_participates_in_caller_transaction() -> None:
    event_id = create_event(1).event_id
    repository = DjangoOutboxRelayRepository()
    with pytest.raises(RuntimeError), transaction.atomic():
        assert repository.mark_processed(consumer="notifications", event_id=event_id)
        raise RuntimeError("rollback")
    assert not ProcessedEvent.objects.exists()
    assert repository.mark_processed(consumer="notifications", event_id=event_id)
    assert not repository.mark_processed(consumer="notifications", event_id=event_id)
