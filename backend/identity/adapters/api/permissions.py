from __future__ import annotations

from collections.abc import Callable
from typing import Any

from rest_framework.permissions import BasePermission

from core.error_codes import INVALID_TOKEN, PASSWORD_CHANGE_REQUIRED, PERMISSION_DENIED
from core.errors import IdentityAPIError
from identity.domain.accounts import AccountSnapshot
from identity.domain.authorization import PermissionAction, Role, decide_permission

TargetLookup = Callable[[str], AccountSnapshot | None]


class CanonicalIdentityPermission(BasePermission):
    def has_permission(self, request: Any, view: Any) -> bool:
        user = request.user
        if user is None or not getattr(user, "is_authenticated", False):
            raise IdentityAPIError(INVALID_TOKEN, status_code=401)
        self._require_action(user, view)
        self._protect_target(view)
        if user.must_change_password and not getattr(view, "password_change_exempt", False):
            raise IdentityAPIError(PASSWORD_CHANGE_REQUIRED, status_code=403)
        return True

    @staticmethod
    def _require_action(user: Any, view: Any) -> None:
        required: PermissionAction | None = getattr(view, "required_action", None)
        if required is not None and not decide_permission(Role(user.role), required).allowed:
            raise IdentityAPIError(PERMISSION_DENIED, status_code=403)

    @staticmethod
    def _protect_target(view: Any) -> None:
        if getattr(view, "protect_manager_target", False):
            target_id = str(view.kwargs.get("user_id", ""))
            target_lookup: TargetLookup | None = view.target_lookup
            if target_lookup is None:
                raise RuntimeError("identity target lookup is not configured")
            target = target_lookup(target_id)
            if target is not None and target.role is Role.MANAGER:
                raise IdentityAPIError(PERMISSION_DENIED, status_code=403)
