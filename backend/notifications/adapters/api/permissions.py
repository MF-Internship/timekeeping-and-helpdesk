from typing import Any

from rest_framework.permissions import BasePermission

from core.error_codes import INVALID_TOKEN
from core.errors import IdentityAPIError
from identity.domain.authorization import PermissionAction


class NotificationActionPermission(BasePermission):
    def has_permission(self, request: Any, view: Any) -> bool:
        user = request.user
        if user is None or not getattr(user, "is_authenticated", False):
            raise IdentityAPIError(INVALID_TOKEN, status_code=401)
        action = PermissionAction(view.action)
        view.container().dependencies.authorization.authorize(int(user.pk), action)
        return True
