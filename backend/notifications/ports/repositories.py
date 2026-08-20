from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from notifications.application.dto import (
    Inbox,
    StoredNotification,
    SubscriptionResult,
    SubscriptionUpsert,
)
from notifications.domain.events import Occurrence


class NotificationRepository(Protocol):
    def insert_occurrence(self, occurrence: Occurrence) -> tuple[StoredNotification, bool]: ...
    def inbox(self, recipient_id: int) -> Inbox: ...
    def get_owned(self, recipient_id: int, public_id: UUID) -> StoredNotification | None: ...
    def mark_read(
        self, recipient_id: int, public_id: UUID, read_at: datetime
    ) -> StoredNotification | None: ...


class SubscriptionRepository(Protocol):
    def active_for_user(self, user_id: int) -> tuple[Any, ...]: ...
    def upsert(self, value: SubscriptionUpsert) -> SubscriptionResult: ...
    def revoke_owned(self, user_id: int, public_id: UUID, now: datetime) -> bool: ...
    def revoke_all(self, user_id: int, now: datetime) -> int: ...
