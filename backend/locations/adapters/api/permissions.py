from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission

from core.error_codes import INVALID_TOKEN
from core.errors import IdentityAPIError


class CanonicalLocationPermission(BasePermission):
    def has_permission(self, request: Any, view: Any) -> bool:
        # Unsupported methods are deliberately absent from the Location
        # contract. Let APIView reach the view's 404 handler instead of
        # treating a nonexistent operation as an RBAC-protected action.
        if request.method not in view.allowed_methods:
            return True
        user = request.user
        if user is None or not getattr(user, "is_authenticated", False):
            raise IdentityAPIError(INVALID_TOKEN, status_code=401)
        action = view.permission_action(request.method)
        view.container().authorization.authorize(int(user.pk), action)
        return True
