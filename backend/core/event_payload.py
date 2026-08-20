from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

DEFAULT_DIAGNOSTIC_MAX_LENGTH = 256
SAFE_EMPTY_DIAGNOSTIC = "diagnostic unavailable"

_FORBIDDEN_KEYS = frozenset(
    {
        "access_token",
        "authorization",
        "cookie",
        "credential",
        "generated_password",
        "image",
        "image_data",
        "jti",
        "jwt",
        "latitude",
        "longitude",
        "object_key",
        "password",
        "password_hash",
        "presigned_url",
        "refresh_token",
        "session",
        "session_secret",
        "signature",
        "set_cookie",
        "token",
        "url",
    }
)
_URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
_BEARER_PATTERN = re.compile(r"\bBearer\s+\S+", re.IGNORECASE)
_ASSIGNMENT_PATTERN = re.compile(
    r"\b(?:access_token|authorization|cookie|image|image_data|object_key|password|"
    r"presigned_url|refresh_token|token)\s*[:=]\s*\S+",
    re.IGNORECASE,
)
_COORDINATE_PATTERN = re.compile(r"(?<!\d)-?\d{1,3}\.\d{5,}(?:\s*,\s*-?\d{1,3}\.\d{5,})?")
_WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class ProtectedPayloadError(ValueError):
    path: str

    def __str__(self) -> str:
        return f"protected payload at {self.path}"


def validate_event_payload(
    value: Any,
    *,
    path: str = "$",
    allowed_paths: frozenset[str] = frozenset(),
) -> None:
    if isinstance(value, str) and "://" in value:
        raise ProtectedPayloadError(path)
    if isinstance(value, Mapping):
        _validate_mapping(value, path, allowed_paths)
        return
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        for index, item in enumerate(value):
            validate_event_payload(
                item,
                path=f"{path}[{index}]",
                allowed_paths=allowed_paths,
            )


def _validate_mapping(
    value: Mapping[object, Any], path: str, allowed_paths: frozenset[str]
) -> None:
    for raw_key, item in value.items():
        key = str(raw_key)
        item_path = f"{path}.{key}"
        if key.casefold() in _FORBIDDEN_KEYS and item_path not in allowed_paths:
            raise ProtectedPayloadError(item_path)
        validate_event_payload(item, path=item_path, allowed_paths=allowed_paths)


def sanitize_failure_reason(
    reason: object,
    *,
    max_length: int = DEFAULT_DIAGNOSTIC_MAX_LENGTH,
) -> str:
    if max_length < 1:
        raise ValueError("max_length must be positive")
    text = str(reason)
    text = _URL_PATTERN.sub("", text)
    text = _BEARER_PATTERN.sub("", text)
    text = _ASSIGNMENT_PATTERN.sub("", text)
    text = _COORDINATE_PATTERN.sub("", text)
    text = _WHITESPACE_PATTERN.sub(" ", text).strip(" ,;:-")
    if not text:
        return SAFE_EMPTY_DIAGNOSTIC[:max_length]
    return text[:max_length].rstrip()
