from notifications.adapters.api.serializers import (
    NotificationItemSerializer,
    PushSubscriptionResultSerializer,
    TargetSerializer,
)


def test_public_notification_and_subscription_schemas_are_minimal_and_private() -> None:
    assert set(NotificationItemSerializer().fields) == {
        "public_id",
        "event_type",
        "title",
        "created_at",
        "read_at",
        "is_unread",
    }
    assert set(PushSubscriptionResultSerializer().fields) == {
        "id",
        "is_active",
        "created_at",
    }
    forbidden = {
        "user_id",
        "target_id",
        "dedupe_key",
        "endpoint",
        "endpoint_hash",
        "encrypted_subscription",
        "p256dh",
        "auth",
        "failure_code",
    }
    assert not forbidden & set(NotificationItemSerializer().fields)
    assert not forbidden & set(PushSubscriptionResultSerializer().fields)


def test_target_contract_has_closed_minimal_union() -> None:
    serializer = TargetSerializer(data={"destination": "TASK", "target_id": 5})
    assert serializer.is_valid(), serializer.errors
    assert set(serializer.validated_data) == {"destination", "target_id"}
    invalid = TargetSerializer(data={"destination": "USER", "target_id": 5})
    assert not invalid.is_valid()
