from __future__ import annotations

import pytest

from core.event_payload import (
    ProtectedPayloadError,
    sanitize_failure_reason,
    validate_event_payload,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("payload", "path"),
    [
        ({"password": "hidden"}, "$.password"),
        ({"nested": {"access_token": "hidden"}}, "$.nested.access_token"),
        ({"items": [{"cookie": "hidden"}]}, "$.items[0].cookie"),
        ({"photo": {"image_data": "base64"}}, "$.photo.image_data"),
        ({"object_key": "private/evidence.jpg"}, "$.object_key"),
        ({"latitude": 10.785850}, "$.latitude"),
        ({"longitude": 106.692600}, "$.longitude"),
        ({"url": "https://example.invalid/signed?token=hidden"}, "$.url"),
        ({"generated_password": "hidden"}, "$.generated_password"),
        ({"nested": {"jti": "hidden"}}, "$.nested.jti"),
        ({"items": [{"credential": "hidden"}]}, "$.items[0].credential"),
        ({"diagnostic": "scheme://hidden"}, "$.diagnostic"),
    ],
)
def test_protected_payload_reports_path_only(payload: object, path: str) -> None:
    with pytest.raises(ProtectedPayloadError) as raised:
        validate_event_payload(payload)

    assert raised.value.path == path
    assert "hidden" not in str(raised.value)
    assert "example.invalid" not in str(raised.value)


@pytest.mark.unit
def test_forbidden_keys_match_exactly_not_by_substring() -> None:
    validate_event_payload(
        {
            "token_count": 2,
            "password_policy": "configured",
            "must_change_password": True,
            "active_refresh_sessions": 3,
        }
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "reason",
    [
        "restore failed at https://example.invalid/private?token=secret",
        "password=secret token=secret Bearer secret-value",
        "cookie=session-secret object_key=private/photo.jpg",
        "image=data:image/png;base64,AAAA",
        "coordinate 10.785850,106.692600 unavailable",
    ],
)
def test_sanitizer_removes_protected_values(reason: str) -> None:
    sanitized = sanitize_failure_reason(reason)

    assert sanitized
    assert "example.invalid" not in sanitized
    assert "secret" not in sanitized
    assert "private/photo.jpg" not in sanitized
    assert "AAAA" not in sanitized
    assert "10.785850" not in sanitized
    assert "106.692600" not in sanitized


@pytest.mark.unit
def test_sanitizer_is_bounded_and_keeps_safe_diagnostic_text() -> None:
    sanitized = sanitize_failure_reason("restore probe failed " + ("x" * 500), max_length=64)

    assert sanitized.startswith("restore probe failed")
    assert len(sanitized) <= 64


@pytest.mark.unit
def test_sanitizer_returns_safe_no_value_diagnostic() -> None:
    assert sanitize_failure_reason("token=secret") == "diagnostic unavailable"
