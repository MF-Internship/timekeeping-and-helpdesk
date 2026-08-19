from typing import Any

from rest_framework.permissions import BasePermission

from core.error_codes import INVALID_TOKEN
from core.errors import IdentityAPIError


class CanonicalOperationsPermission(BasePermission):
    def has_permission(self, request: Any, view: Any) -> bool:
        user = request.user
        if user is None or not getattr(user, "is_authenticated", False):
            raise IdentityAPIError(INVALID_TOKEN, status_code=401)
        return True
