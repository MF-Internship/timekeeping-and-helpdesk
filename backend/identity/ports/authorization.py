from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from identity.domain.authorization import PermissionAction

__all__ = ["AuthorizationGateway", "AuthorizationResult", "PermissionAction"]


@dataclass(frozen=True, slots=True)
class AuthorizationResult:
    requested_action: PermissionAction
    allowed: bool
    granted_by: PermissionAction | None


class AuthorizationGateway(Protocol):
    def authorize(self, actor_id: int, action: PermissionAction) -> AuthorizationResult: ...
