from __future__ import annotations

from dataclasses import dataclass

from notifications.application.delivery import DeliveryService
from notifications.application.dependencies import NotificationDependencies
from notifications.application.dispatch import OccurrenceDispatcher
from notifications.application.inbox import InboxService
from notifications.application.occurrences import OccurrenceService
from notifications.application.subscriptions import SubscriptionService
from notifications.application.targets import TargetResolver


@dataclass(frozen=True, slots=True)
class NotificationContainer:
    dependencies: NotificationDependencies
    occurrences: OccurrenceService
    dispatch: OccurrenceDispatcher
    inbox: InboxService
    subscriptions: SubscriptionService
    delivery: DeliveryService
    targets: TargetResolver


def build_notification_container(dependencies: NotificationDependencies) -> NotificationContainer:
    occurrences = OccurrenceService(dependencies)
    return NotificationContainer(
        dependencies=dependencies,
        occurrences=occurrences,
        dispatch=OccurrenceDispatcher(dependencies, occurrences),
        inbox=InboxService(dependencies),
        subscriptions=SubscriptionService(dependencies),
        delivery=DeliveryService(dependencies),
        targets=TargetResolver(dependencies),
    )
