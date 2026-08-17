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
        "image",
        "image_data",
        "latitude",
        "longitude",
        "object_key",
        "password",
        "presigned_url",
        "refresh_token",
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


def validate_event_payload(value: Any, *, path: str = "$") -> None:
    if isinstance(value, Mapping):
        _validate_mapping(value, path)
        return
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        for index, item in enumerate(value):
            validate_event_payload(item, path=f"{path}[{index}]")


def _validate_mapping(value: Mapping[object, Any], path: str) -> None:
    for raw_key, item in value.items():
        key = str(raw_key)
        item_path = f"{path}.{key}"
        if key.casefold() in _FORBIDDEN_KEYS:
            raise ProtectedPayloadError(item_path)
        validate_event_payload(item, path=item_path)


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
