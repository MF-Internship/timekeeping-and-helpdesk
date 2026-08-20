from __future__ import annotations

import json
from collections.abc import Callable

from notifications.domain.delivery import PushFailureCode
from notifications.ports.delivery import (
    TransportDisposition,
    TransportResult,
    WebPushRequest,
)

Sender = Callable[..., object]


class WebPushTransport:
    def __init__(
        self,
        *,
        vapid_private_key: str,
        vapid_subject: str,
        sender: Sender | None = None,
    ) -> None:
        self._private_key = vapid_private_key
        self._subject = vapid_subject
        self._timeout_seconds = 5.0
        self._sender = sender

    def send(self, request: WebPushRequest) -> TransportResult:
        try:
            sender = self._sender or self._default_sender
            sender(
                subscription_info=self._subscription_info(request),
                data=self._payload(request),
                vapid_private_key=self._private_key,
                vapid_claims={"sub": self._subject},
                ttl=request.ttl_seconds,
                headers={"Topic": request.collapse_key},
                timeout=self._timeout_seconds,
            )
            return TransportResult(TransportDisposition.ACCEPTED)
        except TimeoutError:
            return TransportResult(
                TransportDisposition.TRANSIENT, PushFailureCode.TRANSPORT_TIMEOUT
            )
        except Exception as error:  # provider details are intentionally discarded
            return self._failure(error)

    @staticmethod
    def _payload(request: WebPushRequest) -> str:
        return json.dumps(
            {"version": 1, "reference": str(request.reference)}, separators=(",", ":")
        )

    @staticmethod
    def _subscription_info(request: WebPushRequest) -> dict[str, object]:
        return {
            "endpoint": request.material.endpoint,
            "keys": {"p256dh": request.material.p256dh, "auth": request.material.auth},
        }

    @staticmethod
    def _failure(error: Exception) -> TransportResult:
        status = getattr(getattr(error, "response", None), "status_code", None)
        if status in {404, 410}:
            return TransportResult(
                TransportDisposition.PERMANENT, PushFailureCode.SUBSCRIPTION_GONE
            )
        return TransportResult(
            TransportDisposition.TRANSIENT, PushFailureCode.TRANSIENT_PROVIDER_FAILURE
        )

    @staticmethod
    def _default_sender(**kwargs: object) -> object:
        from pywebpush import webpush  # type: ignore[import-untyped]

        return webpush(**kwargs)
