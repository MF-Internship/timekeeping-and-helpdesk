import json
from uuid import uuid4

from notifications.adapters.security.subscription_cipher import SubscriptionMaterial
from notifications.adapters.web_push import (
    TransportDisposition,
    WebPushRequest,
    WebPushTransport,
)
from notifications.domain.events import NotificationEventType


def test_transport_emits_only_generic_payload_and_protocol_headers() -> None:
    captured: dict[str, object] = {}

    def sender(**kwargs: object) -> None:
        captured.update(kwargs)

    reference = uuid4()
    result = WebPushTransport(
        vapid_private_key="private",
        vapid_subject="mailto:ops@example.test",
        sender=sender,
    ).send(
        WebPushRequest(
            SubscriptionMaterial("https://push.example.test/x", "key", "auth"),
            NotificationEventType.TASK_ASSIGNED,
            reference,
            120,
            "collapse",
        )
    )
    assert result.disposition is TransportDisposition.ACCEPTED
    assert json.loads(str(captured["data"])) == {
        "version": 1,
        "reference": str(reference),
    }
    assert captured["ttl"] == 120
    assert captured["headers"] == {"Topic": "collapse"}
    assert captured["timeout"] == 5.0
