from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from notifications.domain.delivery import PushFailureCode
from notifications.domain.events import NotificationEventType, NotificationTargetType


@dataclass(frozen=True, slots=True)
class NotificationItem:
    public_id: UUID
    event_type: NotificationEventType
    title: str
    created_at: datetime
    read_at: datetime | None

    @property
    def is_unread(self) -> bool:
        return self.read_at is None


@dataclass(frozen=True, slots=True)
class Inbox:
    items: tuple[NotificationItem, ...]
    unread_count: int


@dataclass(frozen=True, slots=True)
class StoredNotification:
    id: int
    public_id: UUID
    recipient_id: int
    event_type: NotificationEventType
    target_type: NotificationTargetType
    target_id: int
    created_at: datetime
    read_at: datetime | None


@dataclass(frozen=True, slots=True)
class AccountEligibility:
    user_id: int
    is_active: bool


@dataclass(frozen=True, slots=True)
class TaskCandidate:
    task_id: int
    recipient_ids: tuple[int, ...]
    assigned_date: date
    assignment_version: int
    is_completed: bool


@dataclass(frozen=True, slots=True)
class AttendanceCandidate:
    session_id: int
    recipient_id: int
    reminder_at: datetime
    is_open: bool


@dataclass(frozen=True, slots=True)
class TargetResolution:
    destination: str
    target_id: int | None


@dataclass(frozen=True, slots=True)
class SubscriptionInput:
    endpoint: str
    p256dh: str
    auth: str


@dataclass(frozen=True, slots=True)
class SubscriptionResult:
    public_id: UUID
    is_active: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SubscriptionUpsert:
    user_id: int
    endpoint_hash: str
    encrypted_subscription: bytes
    user_agent_family: str
    now: datetime


@dataclass(frozen=True, slots=True)
class DeliveryPlan:
    notification_id: int
    subscription_id: int
    not_before: datetime
    expires_at: datetime
    collapse_key: str


@dataclass(frozen=True, slots=True)
class DeliveryFailure:
    delivery_id: int
    worker_id: str
    attempted_at: datetime
    failure_code: PushFailureCode
    next_attempt_at: datetime | None
