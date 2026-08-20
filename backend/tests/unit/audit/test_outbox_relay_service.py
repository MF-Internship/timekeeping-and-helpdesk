from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from audit.application.relay import OutboxRelayService
from audit.domain.relay import OutboxMessage, RelayConfig


def message(row_id: int, attempt_count: int = 1) -> OutboxMessage:
    return OutboxMessage(
        row_id=row_id,
        event_id=uuid4(),
        event_type="identity.user.created",
        schema_version=1,
        aggregate_type="User",
        aggregate_id=str(row_id),
        aggregate_version=1,
        payload={},
        request_id="",
        correlation_id="",
        attempt_count=attempt_count,
        leased_by="worker",
        lease_expires_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


@dataclass
class FakeRepository:
    claimed: tuple[OutboxMessage, ...]
    published: list[int] = field(default_factory=list)
    failed: list[int] = field(default_factory=list)

    def claim_batch(self, *, worker_id: str, config: RelayConfig) -> tuple[OutboxMessage, ...]:
        del worker_id, config
        return self.claimed

    def mark_published(self, message: OutboxMessage) -> bool:
        self.published.append(message.row_id)
        return True

    def mark_failed(self, message: OutboxMessage, reason: object, config: RelayConfig) -> bool:
        del reason, config
        self.failed.append(message.row_id)
        return True

    def mark_processed(self, *, consumer: str, event_id: UUID) -> bool:
        del consumer, event_id
        return True


@dataclass
class FakeTransport:
    failing_ids: set[int]

    def publish(self, message: OutboxMessage) -> None:
        if message.row_id in self.failing_ids:
            raise RuntimeError("transport failed")


@dataclass
class FakeAlerts:
    dead_letters: list[int] = field(default_factory=list)

    def dead_letter(self, message: OutboxMessage, reason: str) -> None:
        del reason
        self.dead_letters.append(message.row_id)


def test_failed_event_does_not_abort_rest_of_batch() -> None:
    repo = FakeRepository((message(1), message(2), message(3)))
    alerts = FakeAlerts()
    result = OutboxRelayService(
        repo,
        FakeTransport({2}),
        alerts,
        RelayConfig(max_attempts=3),
    ).run_once("worker")
    assert result.claimed == 3
    assert result.published == 2
    assert result.failed == 1
    assert repo.published == [1, 3]
    assert repo.failed == [2]
    assert alerts.dead_letters == []


def test_exhausted_attempt_emits_dead_letter_alert() -> None:
    repo = FakeRepository((message(1, attempt_count=3),))
    alerts = FakeAlerts()
    result = OutboxRelayService(
        repo,
        FakeTransport({1}),
        alerts,
        RelayConfig(max_attempts=3),
    ).run_once("worker")
    assert result.failed == 1
    assert alerts.dead_letters == [1]
