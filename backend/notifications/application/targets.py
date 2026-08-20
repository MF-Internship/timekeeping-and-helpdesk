from __future__ import annotations

from uuid import UUID

from core.error_codes import NOT_FOUND
from core.errors import IdentityAPIError
from notifications.application.dependencies import NotificationDependencies
from notifications.application.dto import TargetResolution
from notifications.domain.events import NotificationTargetType


class TargetResolver:
    def __init__(self, dependencies: NotificationDependencies) -> None:
        self._dependencies = dependencies

    def resolve(self, actor_id: int, public_id: UUID) -> TargetResolution:
        notification = self._dependencies.notifications.get_owned(actor_id, public_id)
        if notification is None:
            raise IdentityAPIError(NOT_FOUND, status_code=404)
        if notification.target_type is NotificationTargetType.TASK and self._dependencies.tasks:
            result = self._dependencies.tasks.resolve(actor_id, notification.target_id)
        elif (
            notification.target_type is NotificationTargetType.ATTENDANCE_SESSION
            and self._dependencies.attendance
        ):
            result = self._dependencies.attendance.resolve(actor_id, notification.target_id)
        else:
            result = None
        if result is None:
            raise IdentityAPIError(NOT_FOUND, status_code=404)
        return result
