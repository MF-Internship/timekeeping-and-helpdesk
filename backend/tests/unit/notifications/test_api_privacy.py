from datetime import UTC, datetime
from uuid import uuid4

from notifications.adapters.api.serializers import notification_payload
from notifications.application.dto import NotificationItem
from notifications.domain.events import NotificationEventType


def test_notification_projection_omits_recipient_target_and_delivery_metadata() -> None:
    payload = notification_payload(
        NotificationItem(
            uuid4(),
            NotificationEventType.TASK_ASSIGNED,
            "Bạn có công việc mới được giao",
            datetime(2026, 8, 21, tzinfo=UTC),
            None,
        )
    )
    assert set(payload) == {
        "public_id",
        "event_type",
        "title",
        "created_at",
        "read_at",
        "is_unread",
    }
    assert not ({"recipient_id", "target_id", "dedupe_key", "endpoint"} & set(payload))
