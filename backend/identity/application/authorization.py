from __future__ import annotations

from core.error_codes import (
    ACCOUNT_INACTIVE,
    INVALID_TOKEN,
    PASSWORD_CHANGE_REQUIRED,
    PERMISSION_DENIED,
)
from core.errors import IdentityAPIError
from identity.domain.authorization import PermissionAction, Role, decide_permission
from identity.models import User
from identity.ports.authorization import AuthorizationResult


class DjangoAuthorizationGateway:
    def authorize(self, actor_id: int, action: PermissionAction) -> AuthorizationResult:
        try:
            user = User.objects.get(pk=actor_id)
        except User.DoesNotExist as error:
            raise IdentityAPIError(INVALID_TOKEN, status_code=401) from error
        if not user.is_active:
            raise IdentityAPIError(ACCOUNT_INACTIVE, status_code=401)
        decision = decide_permission(Role(user.role), action)
        if not decision.allowed:
            raise IdentityAPIError(PERMISSION_DENIED, status_code=403)
        if user.must_change_password:
            raise IdentityAPIError(PASSWORD_CHANGE_REQUIRED, status_code=403)
        return AuthorizationResult(action, True, decision.granted_by)
