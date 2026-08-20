from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from notifications.ports.accounts import AccountEligibilityPort
from notifications.ports.clock import Clock
from notifications.ports.repositories import NotificationRepository, SubscriptionRepository
from notifications.ports.targets import AttendanceFactsPort, TaskFactsPort
from notifications.ports.unit_of_work import UnitOfWork


class AuthorizationPort(Protocol):
    def authorize(self, actor_id: int, action: object) -> object: ...


@dataclass(frozen=True, slots=True)
class NotificationDependencies:
    notifications: NotificationRepository
    subscriptions: SubscriptionRepository
    deliveries: Any
    clock: Clock
    unit_of_work_factory: Callable[[], UnitOfWork]
    accounts: AccountEligibilityPort | None = None
    tasks: TaskFactsPort | None = None
    attendance: AttendanceFactsPort | None = None
    authorization: AuthorizationPort | None = None
    cipher: Any | None = None
    endpoint_policy: Any | None = None
    transport: Any | None = None
