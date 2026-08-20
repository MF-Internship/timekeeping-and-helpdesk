from datetime import UTC, datetime

import pytest
from django.db import IntegrityError, connection, transaction

from identity.domain.authorization import Role
from identity.models import User
from notifications.models import Notification

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


def _user(name: str) -> User:
    return User.objects.create_user(
        username=name,
        password="test-password",
        full_name=name,
        role=Role.HELPDESK.value,
        must_change_password=False,
    )


def test_closed_values_positive_target_and_dedupe_unique_are_database_guards() -> None:
    owner = _user("notification-constraint-owner")
    values = {
        "recipient": owner,
        "event_type": "TASK_ASSIGNED",
        "target_type": "TASK",
        "target_id": 9,
        "dedupe_key": "v1:TASK_ASSIGNED:9:1:1",
        "title": "Bạn có công việc mới được giao",
        "occurred_at": datetime(2026, 8, 21, tzinfo=UTC),
    }
    Notification.objects.create(**values)
    for changes in (
        {"dedupe_key": "v1:TASK_ASSIGNED:9:1:1"},
        {"dedupe_key": "unique-event", "event_type": "PASSWORD_RESET"},
        {"dedupe_key": "unique-target", "target_type": "ACCOUNT"},
        {"dedupe_key": "unique-id", "target_id": 0},
    ):
        with pytest.raises(IntegrityError), transaction.atomic():
            Notification.objects.create(**(values | changes))


def test_notification_indexes_and_foreign_key_protection_exist_in_postgresql() -> None:
    owner = _user("notification-catalog-owner")
    Notification.objects.create(
        recipient=owner,
        event_type="TASK_ASSIGNED",
        target_type="TASK",
        target_id=1,
        dedupe_key="catalog-event",
        title="Bạn có công việc mới được giao",
        occurred_at=datetime(2026, 8, 21, tzinfo=UTC),
    )
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, Notification._meta.db_table)
    assert constraints["notif_owner_created_idx"]["index"] is True
    assert constraints["notif_owner_unread_idx"]["index"] is True
    with pytest.raises(IntegrityError), transaction.atomic():
        owner.delete()
