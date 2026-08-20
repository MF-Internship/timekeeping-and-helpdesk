from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from identity.domain.authorization import JobHealthAccessScope, PermissionAction

__all__ = [
    "AuthorizationGateway",
    "AuthorizationResult",
    "JobHealthAccessScope",
    "PermissionAction",
]


@dataclass(frozen=True, slots=True)
class AuthorizationResult:
    requested_action: PermissionAction
    allowed: bool
    granted_by: PermissionAction | None


class AuthorizationGateway(Protocol):
    def authorize(self, actor_id: int, action: PermissionAction) -> AuthorizationResult: ...

    def authorize_job_health(self, actor_id: int) -> JobHealthAccessScope: ...
