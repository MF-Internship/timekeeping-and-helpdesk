from __future__ import annotations

from typing import Any

from notifications.application.dependencies import NotificationDependencies
from notifications.application.dto import DeliveryFailure
from notifications.domain.delivery import (
    PushFailureCode,
    is_quiet_hour,
    next_delivery_time,
    remaining_ttl_seconds,
    retry_at,
)
from notifications.domain.events import NotificationEventType, NotificationTargetType
from notifications.ports.delivery import TransportDisposition, WebPushRequest


class DeliveryService:
    def __init__(self, dependencies: NotificationDependencies) -> None:
        self._dependencies = dependencies

    def deliver_one(self, worker_id: str) -> bool:
        now = self._dependencies.clock.now()
        delivery_id = self._dependencies.deliveries.candidate_id(now)
        if delivery_id is None:
            return False
        leased = self._claim(delivery_id, worker_id, now)
        if leased is None:
            return True
        self._send_and_finalize(leased, worker_id, now)
        return True

    def _claim(self, delivery_id: int, worker_id: str, now: Any) -> Any | None:
        with self._dependencies.unit_of_work_factory():
            candidate = self._dependencies.deliveries.get(delivery_id)
            if candidate is None:
                return None
            if self._apply_timing_policy(candidate, delivery_id, now):
                return None
            if not self._is_eligible(candidate):
                self._dependencies.deliveries.suppress(delivery_id)
                return None
            return self._dependencies.deliveries.claim(delivery_id, worker_id, now)

    def _send_and_finalize(self, leased: Any, worker_id: str, now: Any) -> None:
        if self._dependencies.cipher is None or self._dependencies.transport is None:
            with self._dependencies.unit_of_work_factory():
                self._dependencies.deliveries.suppress(leased.id)
            return
        material = self._dependencies.cipher.decrypt(
            bytes(leased.subscription.encrypted_subscription)
        )
        result = self._dependencies.transport.send(
            WebPushRequest(
                material,
                NotificationEventType(leased.notification.event_type),
                leased.notification.public_id,
                remaining_ttl_seconds(now, leased.expires_at),
                leased.collapse_key,
            )
        )
        self._finalize(leased, worker_id, result)

    def _finalize(self, leased: Any, worker_id: str, result: Any) -> None:
        finalized_at = self._dependencies.clock.now()
        with self._dependencies.unit_of_work_factory():
            if result.disposition is TransportDisposition.ACCEPTED:
                self._dependencies.deliveries.finalize_success(leased.id, worker_id, finalized_at)
            elif result.disposition is TransportDisposition.PERMANENT:
                self._dependencies.deliveries.finalize_failure(
                    DeliveryFailure(
                        leased.id,
                        worker_id,
                        finalized_at,
                        result.failure_code or PushFailureCode.SUBSCRIPTION_GONE,
                        None,
                    )
                )
                self._dependencies.deliveries.revoke_permanent(leased.subscription_id, finalized_at)
            else:
                self._dependencies.deliveries.finalize_failure(
                    DeliveryFailure(
                        leased.id,
                        worker_id,
                        finalized_at,
                        result.failure_code or PushFailureCode.TRANSIENT_PROVIDER_FAILURE,
                        retry_at(finalized_at, leased.attempt_count + 1, leased.expires_at),
                    )
                )

    def _apply_timing_policy(self, candidate: Any, delivery_id: int, now: Any) -> bool:
        if candidate.expires_at <= now:
            self._dependencies.deliveries.expire_id(delivery_id)
            return True
        if not is_quiet_hour(now):
            return False
        release_at = next_delivery_time(now)
        if release_at >= candidate.expires_at:
            self._dependencies.deliveries.expire_id(delivery_id)
        else:
            self._dependencies.deliveries.defer_quiet(delivery_id, release_at)
        return True

    def _is_eligible(self, candidate: Any) -> bool:
        if not candidate.subscription.is_active:
            return False
        if candidate.subscription.user_id != candidate.notification.recipient_id:
            return False
        if self._dependencies.accounts is not None:
            account = self._dependencies.accounts.get_eligibility(
                candidate.notification.recipient_id
            )
            if account is None or not account.is_active:
                return False
        target_type = NotificationTargetType(candidate.notification.target_type)
        port: Any = (
            self._dependencies.tasks
            if target_type is NotificationTargetType.TASK
            else self._dependencies.attendance
        )
        return bool(
            port
            and port.revalidate(
                candidate.notification.target_id,
                candidate.notification.recipient_id,
                candidate.notification.event_type,
            )
        )
