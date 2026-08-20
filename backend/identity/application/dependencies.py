from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from audit.ports.recording import AuditRecorder
from identity.ports.credentials import PasswordService
from identity.ports.push_subscriptions import NoopPushSubscriptionRevoker, PushSubscriptionRevoker
from identity.ports.sessions import SessionRepository
from identity.ports.unit_of_work import UnitOfWork
from identity.ports.users import MutableUserRepository


@dataclass(frozen=True, slots=True)
class IdentityDependencies:
    users: MutableUserRepository
    passwords: PasswordService
    sessions: SessionRepository
    unit_of_work_factory: Callable[[], UnitOfWork]
    audit: AuditRecorder
    push_subscriptions: PushSubscriptionRevoker = field(default_factory=NoopPushSubscriptionRevoker)
