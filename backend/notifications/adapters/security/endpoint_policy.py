from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from notifications.domain.subscriptions import (
    SubscriptionValidationError,
    endpoint_hash,
    validate_browser_key,
)

__all__ = [
    "ExactEndpointPolicy",
    "SubscriptionValidationError",
    "endpoint_hash",
    "validate_browser_key",
]


class ExactEndpointPolicy:
    def __init__(self, allowed_origins: tuple[str, ...]) -> None:
        self._allowed_origins = frozenset(self._origin(origin) for origin in allowed_origins)

    def validate(self, endpoint: str) -> str:
        try:
            parts = urlsplit(endpoint)
            origin = self._origin(endpoint)
            _ = parts.port
        except (ValueError, UnicodeError) as error:
            raise SubscriptionValidationError("invalid push endpoint") from error
        if parts.username or parts.password or parts.fragment or not parts.path:
            raise SubscriptionValidationError("invalid push endpoint")
        if origin not in self._allowed_origins:
            raise SubscriptionValidationError("push endpoint origin is not allowed")
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, ""))

    @staticmethod
    def _origin(value: str) -> str:
        parts = urlsplit(value)
        if parts.scheme.lower() != "https" or not parts.hostname:
            raise SubscriptionValidationError("HTTPS endpoint required")
        port = parts.port
        host = parts.hostname.lower()
        return f"https://{host}" if port in (None, 443) else f"https://{host}:{port}"
