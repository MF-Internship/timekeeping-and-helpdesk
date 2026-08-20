from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass


class SubscriptionValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SubscriptionMaterial:
    endpoint: str
    p256dh: str
    auth: str


def validate_browser_key(value: str) -> str:
    if not value or any(character.isspace() for character in value):
        raise SubscriptionValidationError("invalid browser key")
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, TypeError) as error:
        raise SubscriptionValidationError("invalid browser key") from error
    if not decoded:
        raise SubscriptionValidationError("invalid browser key")
    return value.rstrip("=")


def endpoint_hash(endpoint: str) -> str:
    return hashlib.sha256(endpoint.encode("utf-8")).hexdigest()
