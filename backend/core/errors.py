from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from core.error_codes import AUTHORIZED_FOUNDATION_ERROR_CODES, VALIDATION_FAILED
from core.event_payload import (
    ProtectedPayloadError,
    sanitize_failure_reason,
    validate_event_payload,
)
from core.messages import ERROR_MESSAGES

_CANONICAL_FIELDS = frozenset({"error_code", "message", "details", "request_id", "error"})


class IdentityAPIError(Exception):
    def __init__(
        self,
        error_code: str,
        *,
        status_code: int,
        details: Mapping[str, object] | None = None,
    ) -> None:
        self.error_code = error_code
        self.status_code = status_code
        self.details = dict(details or {})
        self.headers: dict[str, str] = {}
        super().__init__(error_code)


def build_error_envelope(
    error_code: str,
    request_id: str,
    details: Mapping[str, object] | None = None,
) -> dict[str, Any]:
    if error_code not in AUTHORIZED_FOUNDATION_ERROR_CODES:
        raise ValueError("unauthorized foundation error code")
    structured_details = dict(details or {})
    _validate_details(structured_details)
    payload: dict[str, Any] = {
        "error_code": error_code,
        "message": ERROR_MESSAGES[error_code],
        "details": structured_details,
        "request_id": request_id,
        "error": error_code,
    }
    for field, messages in structured_details.items():
        if field not in _CANONICAL_FIELDS:
            payload[field] = messages
    return payload


def validation_details(detail: object) -> dict[str, object]:
    if isinstance(detail, Mapping):
        normalized: dict[str, object] = {
            str(key): _normalize_messages(value) for key, value in detail.items()
        }
        try:
            validate_event_payload(normalized)
        except ProtectedPayloadError:
            return {"fields": ["Giá trị đầu vào được bảo vệ không hợp lệ."]}
        return normalized
    return {}


def drf_exception_handler(exception: Exception, context: dict[str, object]) -> object:
    from rest_framework.exceptions import ValidationError
    from rest_framework.response import Response
    from rest_framework.views import exception_handler

    if isinstance(exception, IdentityAPIError):
        from core.correlation import get_request_id

        return Response(
            build_error_envelope(
                exception.error_code,
                get_request_id(),
                exception.details,
            ),
            status=exception.status_code,
            headers=exception.headers,
        )
    if isinstance(exception, ValidationError):
        from core.correlation import get_request_id

        return Response(
            build_error_envelope(
                VALIDATION_FAILED,
                get_request_id(),
                validation_details(exception.detail),
            ),
            status=400,
        )
    return exception_handler(exception, context)


def _normalize_messages(value: object) -> list[str]:
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [str(item) for item in value]
    return [str(value)]


def _validate_details(details: Mapping[str, object]) -> None:
    try:
        validate_event_payload(details)
    except ProtectedPayloadError as error:
        raise ValueError(str(error)) from error
    _validate_safe_strings(details, "$")


def _validate_safe_strings(value: object, path: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            _validate_safe_strings(item, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        for index, item in enumerate(value):
            _validate_safe_strings(item, f"{path}[{index}]")
    elif isinstance(value, str) and sanitize_failure_reason(value) != value:
        raise ValueError(f"protected payload at {path}")
