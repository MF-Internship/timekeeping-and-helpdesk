from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from audit.ports.recording import AuditRecorder
from identity.application.authentication import AuthenticationService
from identity.application.queries import UserQueryService
from identity.application.self_service import SelfService
from identity.application.user_admin import UserAdminService
from identity.ports.credentials import PasswordService
from identity.ports.sessions import SessionRepository
from identity.ports.unit_of_work import UnitOfWork
from identity.ports.users import MutableUserRepository


@dataclass(frozen=True, slots=True)
class IdentityContainer:
    users: MutableUserRepository
    passwords: PasswordService
    sessions: SessionRepository
    unit_of_work_factory: Callable[[], UnitOfWork]
    audit: AuditRecorder
    authentication: AuthenticationService
    self_service: SelfService
    queries: UserQueryService
    user_admin: UserAdminService
