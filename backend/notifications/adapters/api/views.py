from __future__ import annotations

from typing import Any
from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.error_codes import NOT_FOUND
from core.errors import IdentityAPIError
from notifications.adapters.api.permissions import NotificationActionPermission
from notifications.adapters.api.serializers import (
    EmptyReadSerializer,
    InboxSerializer,
    NotificationItemSerializer,
    PushSubscriptionInputSerializer,
    PushSubscriptionResultSerializer,
    TargetSerializer,
    notification_payload,
)
from notifications.application.dto import SubscriptionInput


def _private(response: Response) -> Response:
    response["Cache-Control"] = "private, no-store"
    return response


def _uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except (ValueError, TypeError) as error:
        raise IdentityAPIError(NOT_FOUND, status_code=404) from error


class NotificationViewBase(APIView):
    permission_classes = (NotificationActionPermission,)
    action = "notification.view.self"

    @staticmethod
    def container() -> Any:
        from config import composition

        return composition.notification_container()


class NotificationInboxView(NotificationViewBase):
    @extend_schema(operation_id="notifications_list", responses=InboxSerializer)
    def get(self, request: Request) -> Response:
        if request.query_params:
            raise serializers.ValidationError({"query": sorted(request.query_params)})
        inbox = self.container().inbox.list(_actor_id(request))
        payload = {
            "items": [notification_payload(item) for item in inbox.items],
            "unread_count": inbox.unread_count,
        }
        return _private(Response(payload))


class NotificationReadView(NotificationViewBase):
    action = "notification.update.self"

    @extend_schema(
        operation_id="notifications_mark_read",
        request=EmptyReadSerializer,
        responses=NotificationItemSerializer,
    )
    def patch(self, request: Request, public_id: str) -> Response:
        serializer = EmptyReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = self.container().inbox.mark_read(_actor_id(request), _uuid(public_id))
        return _private(Response(notification_payload(item)))


class PushSubscriptionCollectionView(NotificationViewBase):
    action = "push_subscription.manage.self"

    @extend_schema(
        operation_id="push_subscriptions_upsert",
        request=PushSubscriptionInputSerializer,
        responses=PushSubscriptionResultSerializer,
    )
    def post(self, request: Request) -> Response:
        serializer = PushSubscriptionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            result = self.container().subscriptions.upsert(
                _actor_id(request),
                SubscriptionInput(str(data["endpoint"]), str(data["p256dh"]), str(data["auth"])),
                _user_agent_family(request.headers.get("User-Agent", "")),
            )
        except ValueError as error:
            raise serializers.ValidationError(
                {"subscription": ["Invalid push subscription."]}
            ) from error
        return _private(Response(PushSubscriptionResultSerializer(result).data))


class PushSubscriptionDetailView(NotificationViewBase):
    action = "push_subscription.manage.self"

    @extend_schema(operation_id="push_subscriptions_revoke", responses={204: None})
    def delete(self, request: Request, public_id: str) -> Response:
        self.container().subscriptions.revoke(_actor_id(request), _uuid(public_id))
        return _private(Response(status=status.HTTP_204_NO_CONTENT))


class NotificationTargetView(NotificationViewBase):
    @extend_schema(operation_id="notifications_resolve_target", responses=TargetSerializer)
    def get(self, request: Request, public_id: str) -> Response:
        result = self.container().targets.resolve(_actor_id(request), _uuid(public_id))
        return _private(
            Response({"destination": result.destination, "target_id": result.target_id})
        )


def _user_agent_family(user_agent: str) -> str:
    lowered = user_agent.lower()
    for marker, family in (
        ("edg/", "EDGE"),
        ("firefox/", "FIREFOX"),
        ("chrome/", "CHROME"),
        ("safari/", "SAFARI"),
    ):
        if marker in lowered:
            return family
    return "OTHER"


def _actor_id(request: Request) -> int:
    return int(str(request.user.pk))
