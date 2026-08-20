from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from notifications.domain.delivery import PushFailureCode
from notifications.domain.events import NotificationEventType
from notifications.domain.subscriptions import SubscriptionMaterial


class TransportDisposition(StrEnum):
    ACCEPTED = "ACCEPTED"
    TRANSIENT = "TRANSIENT"
    PERMANENT = "PERMANENT"


@dataclass(frozen=True, slots=True)
class TransportResult:
    disposition: TransportDisposition
    failure_code: PushFailureCode | None = None


@dataclass(frozen=True, slots=True)
class WebPushRequest:
    material: SubscriptionMaterial
    event_type: NotificationEventType
    reference: UUID
    ttl_seconds: int
    collapse_key: str
