from __future__ import annotations

from uuid import UUID

from core.error_codes import NOT_FOUND
from core.errors import IdentityAPIError
from notifications.application.dependencies import NotificationDependencies
from notifications.application.dto import Inbox, NotificationItem


class InboxService:
    def __init__(self, dependencies: NotificationDependencies) -> None:
        self._dependencies = dependencies

    def list(self, recipient_id: int) -> Inbox:
        return self._dependencies.notifications.inbox(recipient_id)

    def mark_read(self, recipient_id: int, public_id: UUID) -> NotificationItem:
        with self._dependencies.unit_of_work_factory():
            row = self._dependencies.notifications.mark_read(
                recipient_id, public_id, self._dependencies.clock.now()
            )
            if row is None:
                raise IdentityAPIError(NOT_FOUND, status_code=404)
        inbox = self._dependencies.notifications.inbox(recipient_id)
        return next(item for item in inbox.items if item.public_id == public_id)
