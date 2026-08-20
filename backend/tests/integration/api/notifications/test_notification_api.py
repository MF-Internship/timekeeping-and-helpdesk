from datetime import UTC, datetime

import pytest

from identity.domain.authorization import Role
from notifications.models import Notification
from tests.integration.api.identity.helpers import authenticated_client, create_user

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


def _notification(owner_id: int, *, key: str, target_id: int = 1) -> Notification:
    return Notification.objects.create(
        recipient_id=owner_id,
        event_type="TASK_ASSIGNED",
        target_type="TASK",
        target_id=target_id,
        dedupe_key=key,
        title="Bạn có công việc mới được giao",
        occurred_at=datetime(2026, 8, 21, tzinfo=UTC),
    )


def test_inbox_is_self_only_private_and_read_is_explicit_idempotent() -> None:
    owner = create_user("notification-api-owner", Role.HELPDESK.value)
    foreign = create_user("notification-api-foreign", Role.HELPDESK.value)
    own = _notification(owner.pk, key="api-own")
    _notification(foreign.pk, key="api-foreign")
    client = authenticated_client(owner)

    inbox = client.get("/api/v1/notifications/")
    assert inbox.status_code == 200
    assert inbox["Cache-Control"] == "private, no-store"
    assert inbox.json()["unread_count"] == 1
    assert [item["public_id"] for item in inbox.json()["items"]] == [str(own.public_id)]
    assert not ({"recipient_id", "target_id", "dedupe_key"} & set(inbox.json()["items"][0]))

    first = client.patch(f"/api/v1/notifications/{own.public_id}/read", {}, format="json")
    repeated = client.patch(f"/api/v1/notifications/{own.public_id}/read", {}, format="json")
    assert first.status_code == repeated.status_code == 200
    assert first.json()["read_at"] == repeated.json()["read_at"]
    assert first.json()["is_unread"] is False


def test_read_rejects_server_owned_fields_and_foreign_reference_without_mutation() -> None:
    owner = create_user("notification-api-read-owner", Role.HELPDESK.value)
    foreign = create_user("notification-api-read-foreign", Role.HELPDESK.value)
    own = _notification(owner.pk, key="api-read-own")
    foreign_row = _notification(foreign.pk, key="api-read-foreign")
    client = authenticated_client(owner)

    rejected = client.patch(
        f"/api/v1/notifications/{own.public_id}/read",
        {"read_at": "2026-08-21T00:00:00Z"},
        format="json",
    )
    hidden = client.patch(f"/api/v1/notifications/{foreign_row.public_id}/read", {}, format="json")
    assert rejected.status_code == 400
    assert rejected.json()["error_code"] == "SERVER_OWNED_FIELD"
    assert hidden.status_code == 404
    own.refresh_from_db()
    foreign_row.refresh_from_db()
    assert own.read_at is None and foreign_row.read_at is None


def test_disabled_push_returns_safe_503_and_stale_target_is_non_disclosing() -> None:
    owner = create_user("notification-api-disabled-owner", Role.HELPDESK.value)
    stale = _notification(owner.pk, key="api-stale-target", target_id=999999)
    client = authenticated_client(owner)
    subscription = client.post(
        "/api/v1/push-subscriptions/",
        {
            "endpoint": "https://push.example.invalid/send/opaque",
            "p256dh": "cDI1NmRo",
            "auth": "YXV0aA",
        },
        format="json",
    )
    target = client.get(f"/api/v1/notifications/{stale.public_id}/target")
    assert subscription.status_code == 503
    assert subscription.json()["error_code"] == "SERVICE_UNAVAILABLE"
    assert "endpoint" not in str(subscription.json())
    assert target.status_code == 404
    stale.refresh_from_db()
    assert stale.read_at is None
