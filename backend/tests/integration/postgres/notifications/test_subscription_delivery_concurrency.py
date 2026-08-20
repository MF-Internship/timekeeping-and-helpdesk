from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from types import SimpleNamespace

import pytest
from django.db import close_old_connections, transaction

from identity.domain.authorization import Role
from identity.models import User
from notifications.adapters.persistence.repositories import (
    DjangoDeliveryRepository,
    DjangoNotificationRepository,
    DjangoSubscriptionRepository,
)
from notifications.adapters.persistence.unit_of_work import DjangoUnitOfWork
from notifications.application.dependencies import NotificationDependencies
from notifications.application.dto import SubscriptionUpsert
from notifications.application.occurrences import OccurrenceService
from notifications.domain.delivery import PushDeliveryState
from notifications.domain.events import NotificationEventType, NotificationTargetType, Occurrence
from notifications.models import Notification, PushDelivery, PushSubscription

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]
NOW = datetime(2026, 8, 21, 10, tzinfo=UTC)


def _user(name: str) -> User:
    return User.objects.create_user(
        username=name,
        password="test-password",
        full_name=name,
        role=Role.HELPDESK.value,
        must_change_password=False,
    )


def test_same_endpoint_registration_is_serialized_without_precheck_race() -> None:
    owner = _user("subscription-race-owner")
    barrier = Barrier(2)

    def register(ciphertext: bytes) -> str:
        close_old_connections()
        barrier.wait(timeout=5)
        try:
            with transaction.atomic():
                result = DjangoSubscriptionRepository().upsert(
                    SubscriptionUpsert(owner.pk, "a" * 64, ciphertext, "TEST", NOW)
                )
                return str(result.public_id)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        public_ids = list(pool.map(register, (b"first", b"second")))

    assert public_ids[0] == public_ids[1]
    assert PushSubscription.objects.filter(endpoint_hash="a" * 64, is_active=True).count() == 1


def test_competing_delivery_workers_only_claim_once() -> None:
    owner = _user("delivery-race-owner")
    notification = Notification.objects.create(
        recipient=owner,
        event_type="TASK_ASSIGNED",
        target_type="TASK",
        target_id=1,
        dedupe_key="delivery-race",
        title="Bạn có công việc mới được giao",
        occurred_at=NOW,
    )
    subscription = PushSubscription.objects.create(
        user=owner,
        endpoint_hash="b" * 64,
        encrypted_subscription=b"encrypted",
        user_agent_family="TEST",
    )
    delivery = PushDelivery.objects.create(
        notification=notification,
        subscription=subscription,
        not_before=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(hours=1),
        next_attempt_at=NOW - timedelta(minutes=1),
        collapse_key="task-assigned",
    )
    barrier = Barrier(2)

    def claim(worker_id: str) -> bool:
        close_old_connections()
        barrier.wait(timeout=5)
        try:
            with transaction.atomic():
                return DjangoDeliveryRepository().claim(delivery.pk, worker_id, NOW) is not None
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(claim, ("worker-a", "worker-b")))

    assert sorted(claims) == [False, True]


def test_competing_read_updates_preserve_the_first_read_timestamp() -> None:
    owner = _user("read-race-owner")
    row = Notification.objects.create(
        recipient=owner,
        event_type="TASK_ASSIGNED",
        target_type="TASK",
        target_id=2,
        dedupe_key="read-race",
        title="Bạn có công việc mới được giao",
        occurred_at=NOW,
    )
    barrier = Barrier(2)
    candidates = (NOW + timedelta(seconds=1), NOW + timedelta(seconds=2))

    def mark_read(read_at: datetime) -> None:
        close_old_connections()
        barrier.wait(timeout=5)
        try:
            with transaction.atomic():
                DjangoNotificationRepository().mark_read(owner.pk, row.public_id, read_at)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(mark_read, candidates))

    row.refresh_from_db()
    assert row.read_at in candidates


def _delivery(owner: User, suffix: str) -> PushDelivery:
    notification = Notification.objects.create(
        recipient=owner,
        event_type="TASK_OVERDUE",
        target_type="TASK",
        target_id=30,
        dedupe_key=f"delivery-{suffix}",
        title="Bạn có công việc quá hạn",
        occurred_at=NOW,
    )
    subscription = PushSubscription.objects.create(
        user=owner,
        endpoint_hash=suffix * 64,
        encrypted_subscription=b"encrypted",
        user_agent_family="TEST",
    )
    return PushDelivery.objects.create(
        notification=notification,
        subscription=subscription,
        not_before=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(hours=1),
        next_attempt_at=NOW - timedelta(minutes=1),
        collapse_key="task-overdue",
    )


def test_expired_lease_is_reclaimed_but_live_lease_is_not() -> None:
    owner = _user("lease-reclaim-owner")
    delivery = _delivery(owner, "c")
    delivery.state = PushDeliveryState.LEASED.value
    delivery.leased_by = "dead-worker"
    delivery.lease_expires_at = NOW - timedelta(seconds=1)
    delivery.save(update_fields=["state", "leased_by", "lease_expires_at"])

    with transaction.atomic():
        claimed = DjangoDeliveryRepository().claim(delivery.pk, "new-worker", NOW)
    assert claimed is not None
    delivery.refresh_from_db()
    assert delivery.leased_by == "new-worker"

    with transaction.atomic():
        assert DjangoDeliveryRepository().claim(delivery.pk, "third-worker", NOW) is None


@pytest.mark.parametrize("action", ["revoke", "suppress"])
def test_revocation_or_source_suppression_wins_against_an_existing_lease(action: str) -> None:
    owner = _user(f"delivery-{action}-owner")
    delivery = _delivery(owner, "d" if action == "revoke" else "e")
    with transaction.atomic():
        assert DjangoDeliveryRepository().claim(delivery.pk, "worker", NOW) is not None
    with transaction.atomic():
        if action == "revoke":
            DjangoSubscriptionRepository().revoke_all(owner.pk, NOW)
        else:
            DjangoDeliveryRepository().suppress_target("TASK", 30, (owner.pk,))

    delivery.refresh_from_db()
    assert delivery.state == PushDeliveryState.SUPPRESSED.value
    assert delivery.leased_by is None


def test_endpoint_account_switch_leaves_exactly_one_active_owner() -> None:
    first_owner = _user("endpoint-first-owner")
    second_owner = _user("endpoint-second-owner")
    repository = DjangoSubscriptionRepository()
    with transaction.atomic():
        repository.upsert(SubscriptionUpsert(first_owner.pk, "f" * 64, b"first", "TEST", NOW))
    with transaction.atomic():
        repository.upsert(SubscriptionUpsert(second_owner.pk, "f" * 64, b"second", "TEST", NOW))

    active = PushSubscription.objects.get(endpoint_hash="f" * 64, is_active=True)
    assert active.user_id == second_owner.pk
    assert PushSubscription.objects.filter(endpoint_hash="f" * 64, is_active=True).count() == 1


def test_source_transaction_rollback_removes_notification_and_delivery() -> None:
    owner = _user("notification-rollback-owner")
    PushSubscription.objects.create(
        user=owner,
        endpoint_hash="9" * 64,
        encrypted_subscription=b"encrypted",
        user_agent_family="TEST",
    )
    service = OccurrenceService(
        NotificationDependencies(
            notifications=DjangoNotificationRepository(),
            subscriptions=DjangoSubscriptionRepository(),
            deliveries=DjangoDeliveryRepository(),
            clock=SimpleNamespace(now=lambda: NOW),
            unit_of_work_factory=DjangoUnitOfWork,
        )
    )
    occurrence = Occurrence(
        NotificationEventType.TASK_ASSIGNED,
        NotificationTargetType.TASK,
        99,
        owner.pk,
        NOW,
        assignment_version=1,
    )

    with pytest.raises(RuntimeError, match="rollback"), transaction.atomic():
        service.record(occurrence)
        raise RuntimeError("rollback")

    assert not Notification.objects.filter(dedupe_key=occurrence.dedupe_key).exists()
    assert not PushDelivery.objects.exists()
