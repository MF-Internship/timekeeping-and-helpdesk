from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier

import pytest
from django.db import close_old_connections, transaction

from identity.domain.authorization import Role
from identity.models import User
from notifications.adapters.persistence.repositories import DjangoNotificationRepository
from notifications.domain.events import (
    NotificationEventType,
    NotificationTargetType,
    Occurrence,
)
from notifications.models import Notification

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


def test_competing_occurrence_writers_create_one_authoritative_row() -> None:
    owner = User.objects.create_user(
        username="notification-race-owner",
        password="test-password",
        full_name="Notification Race Owner",
        role=Role.HELPDESK.value,
        must_change_password=False,
    )
    occurrence = Occurrence(
        NotificationEventType.TASK_ASSIGNED,
        NotificationTargetType.TASK,
        10,
        owner.pk,
        datetime(2026, 8, 21, tzinfo=UTC),
        assignment_version=1,
    )
    barrier = Barrier(2)

    def write() -> str:
        close_old_connections()
        barrier.wait(timeout=5)
        try:
            with transaction.atomic():
                row, _ = DjangoNotificationRepository().insert_occurrence(occurrence)
                return str(row.public_id)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        public_ids = list(pool.map(lambda _: write(), range(2)))
    assert public_ids[0] == public_ids[1]
    assert Notification.objects.filter(dedupe_key=occurrence.dedupe_key).count() == 1
