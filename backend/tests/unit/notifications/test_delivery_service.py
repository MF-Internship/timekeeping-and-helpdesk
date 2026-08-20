from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from notifications.application.delivery import DeliveryService
from notifications.application.dependencies import NotificationDependencies
from notifications.domain.delivery import PushDeliveryState, PushFailureCode
from notifications.domain.subscriptions import SubscriptionMaterial
from notifications.ports.delivery import TransportDisposition, TransportResult

NOW = datetime(2026, 8, 21, 3, tzinfo=UTC)  # 10:00 Asia/Ho_Chi_Minh


class UnitOfWork(AbstractContextManager["UnitOfWork"]):
    def __init__(self, state: SimpleNamespace) -> None:
        self.state = state

    def __enter__(self) -> UnitOfWork:
        self.state.depth += 1
        return self

    def __exit__(self, *args: object) -> None:
        self.state.depth -= 1


class DeliveryRepository:
    def __init__(self, row: SimpleNamespace) -> None:
        self.row = row
        self.calls: list[tuple[str, Any]] = []

    def candidate_id(self, now: datetime) -> int:
        return self.row.id

    def get(self, delivery_id: int) -> SimpleNamespace:
        return self.row

    def claim(self, delivery_id: int, worker_id: str, now: datetime) -> SimpleNamespace:
        self.calls.append(("claim", worker_id))
        return self.row

    def suppress(self, delivery_id: int) -> None:
        self.calls.append(("suppress", delivery_id))

    def defer_quiet(self, delivery_id: int, release_at: datetime) -> None:
        self.calls.append(("defer", release_at))

    def expire_id(self, delivery_id: int) -> None:
        self.calls.append(("expire", delivery_id))

    def finalize_success(self, delivery_id: int, worker_id: str, now: datetime) -> None:
        self.calls.append(("success", worker_id))

    def finalize_failure(self, failure: Any) -> None:
        self.calls.append(("failure", failure))

    def revoke_permanent(self, subscription_id: int, now: datetime) -> None:
        self.calls.append(("revoke", subscription_id))


def _row(now: datetime = NOW) -> SimpleNamespace:
    return SimpleNamespace(
        id=7,
        expires_at=now + timedelta(hours=1),
        not_before=now - timedelta(minutes=1),
        next_attempt_at=now - timedelta(minutes=1),
        attempt_count=0,
        collapse_key="task-assigned",
        subscription_id=8,
        subscription=SimpleNamespace(
            is_active=True,
            user_id=1,
            encrypted_subscription=b"ciphertext",
        ),
        notification=SimpleNamespace(
            recipient_id=1,
            target_type="TASK",
            target_id=9,
            event_type="TASK_ASSIGNED",
            public_id=uuid4(),
        ),
    )


def _dependencies(
    repository: DeliveryRepository,
    state: SimpleNamespace,
    transport: Any,
    *,
    eligible: bool = True,
) -> NotificationDependencies:
    return NotificationDependencies(
        notifications=SimpleNamespace(),
        subscriptions=SimpleNamespace(),
        deliveries=repository,
        clock=SimpleNamespace(now=lambda: NOW),
        unit_of_work_factory=lambda: UnitOfWork(state),
        tasks=SimpleNamespace(revalidate=lambda *args: eligible),
        cipher=SimpleNamespace(
            decrypt=lambda value: SubscriptionMaterial(
                "https://push.example.invalid/send/opaque", "cDI1NmRo", "YXV0aA"
            )
        ),
        transport=transport,
    )


@pytest.mark.unit
def test_delivery_revalidates_and_suppresses_stale_target_without_network() -> None:
    row = _row()
    repository = DeliveryRepository(row)
    state = SimpleNamespace(depth=0)
    transport = SimpleNamespace(send=lambda request: pytest.fail("network must not be called"))

    assert DeliveryService(_dependencies(repository, state, transport, eligible=False)).deliver_one(
        "worker"
    )
    assert repository.calls == [("suppress", row.id)]


@pytest.mark.unit
def test_quiet_hours_defer_until_release_without_claiming() -> None:
    quiet_now = datetime(2026, 8, 21, 15, tzinfo=UTC)  # 22:00 local
    row = _row(quiet_now)
    row.expires_at = quiet_now + timedelta(hours=16)
    repository = DeliveryRepository(row)
    dependencies = _dependencies(
        repository, SimpleNamespace(depth=0), SimpleNamespace(send=lambda request: None)
    )
    object.__setattr__(dependencies, "clock", SimpleNamespace(now=lambda: quiet_now))

    assert DeliveryService(dependencies).deliver_one("worker")
    assert repository.calls[0][0] == "defer"
    assert all(call[0] != "claim" for call in repository.calls)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("disposition", "expected"),
    [
        (TransportDisposition.ACCEPTED, "success"),
        (TransportDisposition.TRANSIENT, "failure"),
        (TransportDisposition.PERMANENT, "revoke"),
    ],
)
def test_provider_outcomes_finalize_after_network_outside_transaction(
    disposition: TransportDisposition, expected: str
) -> None:
    row = _row()
    repository = DeliveryRepository(row)
    state = SimpleNamespace(depth=0)

    def send(request: object) -> TransportResult:
        assert state.depth == 0
        return TransportResult(
            disposition,
            PushFailureCode.SUBSCRIPTION_GONE
            if disposition is TransportDisposition.PERMANENT
            else None,
        )

    assert DeliveryService(
        _dependencies(repository, state, SimpleNamespace(send=send))
    ).deliver_one("worker")
    assert expected in [call[0] for call in repository.calls]
    assert state.depth == 0


@pytest.mark.unit
def test_ttl_equality_expires_before_provider_call() -> None:
    row = _row()
    row.expires_at = NOW
    repository = DeliveryRepository(row)
    state = SimpleNamespace(depth=0)
    transport = SimpleNamespace(send=lambda request: pytest.fail("network must not be called"))

    assert DeliveryService(_dependencies(repository, state, transport)).deliver_one("worker")
    assert repository.calls == [("expire", row.id)]
    assert PushDeliveryState.EXPIRED.value == "EXPIRED"
