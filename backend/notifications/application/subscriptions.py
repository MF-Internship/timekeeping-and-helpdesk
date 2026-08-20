from __future__ import annotations

from uuid import UUID

from core.error_codes import NOT_FOUND, SERVICE_UNAVAILABLE
from core.errors import IdentityAPIError
from notifications.application.dependencies import NotificationDependencies
from notifications.application.dto import (
    SubscriptionInput,
    SubscriptionResult,
    SubscriptionUpsert,
)
from notifications.domain.subscriptions import (
    SubscriptionMaterial,
    endpoint_hash,
    validate_browser_key,
)


class SubscriptionService:
    def __init__(self, dependencies: NotificationDependencies) -> None:
        self._dependencies = dependencies

    def upsert(
        self, user_id: int, value: SubscriptionInput, user_agent_family: str
    ) -> SubscriptionResult:
        if self._dependencies.endpoint_policy is None or self._dependencies.cipher is None:
            raise IdentityAPIError(SERVICE_UNAVAILABLE, status_code=503)
        endpoint = self._dependencies.endpoint_policy.validate(value.endpoint)
        material = SubscriptionMaterial(
            endpoint, validate_browser_key(value.p256dh), validate_browser_key(value.auth)
        )
        ciphertext = self._dependencies.cipher.encrypt(material)
        with self._dependencies.unit_of_work_factory():
            return self._dependencies.subscriptions.upsert(
                SubscriptionUpsert(
                    user_id,
                    endpoint_hash(endpoint),
                    ciphertext,
                    user_agent_family[:32] or "UNKNOWN",
                    self._dependencies.clock.now(),
                )
            )

    def revoke(self, user_id: int, public_id: UUID) -> None:
        with self._dependencies.unit_of_work_factory():
            if not self._dependencies.subscriptions.revoke_owned(
                user_id, public_id, self._dependencies.clock.now()
            ):
                raise IdentityAPIError(NOT_FOUND, status_code=404)

    def revoke_all(self, user_id: int, reason: object | None = None) -> int:
        del reason
        with self._dependencies.unit_of_work_factory():
            return self._dependencies.subscriptions.revoke_all(
                user_id, self._dependencies.clock.now()
            )
