from collections.abc import Mapping
from typing import Any, cast

from rest_framework import serializers

from core.error_codes import SERVER_OWNED_FIELD
from core.errors import IdentityAPIError
from notifications.application.dto import NotificationItem


class NotificationItemSerializer(serializers.Serializer[Any]):
    public_id = serializers.UUIDField()
    event_type = serializers.ChoiceField(
        choices=(
            "TASK_ASSIGNED",
            "TASK_UPCOMING",
            "TASK_OVERDUE",
            "ATTENDANCE_SESSION_OPEN_NEAR_SHIFT_END",
            "MULTI_ASSIGNEE_TASK_COMPLETED",
        )
    )
    title = serializers.CharField()
    created_at = serializers.DateTimeField()
    read_at = serializers.DateTimeField(allow_null=True)
    is_unread = serializers.BooleanField()


class InboxSerializer(serializers.Serializer[Any]):
    items = NotificationItemSerializer(many=True)
    unread_count = serializers.IntegerField(min_value=0)


class EmptyReadSerializer(serializers.Serializer[Any]):
    def to_internal_value(self, data: object) -> dict[str, object]:
        if data in (None, b"", ""):
            return {}
        if not isinstance(data, Mapping):
            raise serializers.ValidationError({"body": ["Expected an empty JSON object."]})
        if data:
            raise IdentityAPIError(
                SERVER_OWNED_FIELD,
                status_code=400,
                details={"fields": sorted(str(key) for key in data)},
            )
        return {}


class PushSubscriptionInputSerializer(serializers.Serializer[Any]):
    endpoint = serializers.URLField(max_length=2048)
    p256dh = serializers.CharField(max_length=512, trim_whitespace=False)
    auth = serializers.CharField(max_length=256, trim_whitespace=False)

    def to_internal_value(self, data: object) -> dict[str, object]:
        if isinstance(data, Mapping):
            allowed = {"endpoint", "p256dh", "auth"}
            forbidden = sorted(str(key) for key in data if key not in allowed)
            if forbidden:
                raise IdentityAPIError(
                    SERVER_OWNED_FIELD, status_code=400, details={"fields": forbidden}
                )
        return cast(dict[str, object], super().to_internal_value(data))


class PushSubscriptionResultSerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField(source="public_id")
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()


class TargetSerializer(serializers.Serializer[Any]):
    destination = serializers.ChoiceField(choices=("TASK", "ATTENDANCE"))
    target_id = serializers.IntegerField(allow_null=True, min_value=1)


def notification_payload(item: NotificationItem) -> dict[str, object]:
    return {
        "public_id": item.public_id,
        "event_type": item.event_type.value,
        "title": item.title,
        "created_at": item.created_at,
        "read_at": item.read_at,
        "is_unread": item.is_unread,
    }
