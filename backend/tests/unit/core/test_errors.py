from __future__ import annotations

import pytest


def test_authorized_codes_are_closed() -> None:
    from core.error_codes import AUTHORIZED_FOUNDATION_ERROR_CODES

    assert (
        frozenset(
            {
                "VALIDATION_FAILED",
                "PERMISSION_DENIED",
                "INVALID_CREDENTIALS",
                "INVALID_TOKEN",
                "ACCOUNT_INACTIVE",
                "PASSWORD_CHANGE_REQUIRED",
                "SERVER_OWNED_FIELD",
                "NOT_FOUND",
                "LOCATION_VERSION_CONFLICT",
                "THROTTLED",
                "SERVICE_UNAVAILABLE",
                "WEAK_GPS",
                "OUTSIDE_RADIUS",
                "LOCATION_CHOICE_REQUIRED",
                "INVALID_LOCATION_CHOICE",
                "NO_OPEN_SESSION",
                "SESSION_ALREADY_OPEN",
                "INACTIVE_ASSIGNEE",
                "BLOCK_REASON_REQUIRED",
                "TASK_ALREADY_COMPLETED",
                "EVIDENCE_UPLOAD_INVALID",
                "EVIDENCE_UPLOAD_NOT_READY",
                "IDEMPOTENCY_CONFLICT",
            }
        )
        == AUTHORIZED_FOUNDATION_ERROR_CODES
    )


def test_envelope_has_canonical_fields_and_valid_mirrors() -> None:
    from core.errors import build_error_envelope

    payload = build_error_envelope(
        "VALIDATION_FAILED",
        "00000000-0000-4000-8000-000000000000",
        {"field_name": ["Giá trị không hợp lệ."]},
    )
    assert payload["error"] == payload["error_code"] == "VALIDATION_FAILED"
    assert payload["details"] == {"field_name": ["Giá trị không hợp lệ."]}
    assert payload["field_name"] == payload["details"]["field_name"]


def test_canonical_keys_cannot_be_overwritten_by_details() -> None:
    from core.errors import build_error_envelope

    payload = build_error_envelope(
        "PERMISSION_DENIED",
        "00000000-0000-4000-8000-000000000000",
        {"message": ["collision"], "request_id": ["collision"]},
    )
    assert payload["message"] != ["collision"]
    assert payload["request_id"] == "00000000-0000-4000-8000-000000000000"
    assert payload["details"]["message"] == ["collision"]


@pytest.mark.parametrize("code", ["METHOD_NOT_ALLOWED", "INTERNAL_ERROR"])
def test_unauthorized_codes_are_rejected(code: str) -> None:
    from core.errors import build_error_envelope

    with pytest.raises(ValueError):
        build_error_envelope(code, "00000000-0000-4000-8000-000000000000")


def test_protected_detail_is_rejected_without_value_in_error() -> None:
    from core.errors import build_error_envelope

    secret = "https://user:password@example.invalid/object"
    with pytest.raises(ValueError) as captured:
        build_error_envelope(
            "VALIDATION_FAILED",
            "00000000-0000-4000-8000-000000000000",
            {"field_name": [secret]},
        )
    assert secret not in str(captured.value)


def test_protected_validation_details_are_redacted_before_envelope_validation() -> None:
    from core.errors import build_error_envelope, validation_details

    details = validation_details({"latitude": ["Ensure that there are no more than 9 digits."]})
    payload = build_error_envelope(
        "VALIDATION_FAILED", "00000000-0000-4000-8000-000000000000", details
    )

    assert payload["details"] == {"fields": ["Giá trị đầu vào được bảo vệ không hợp lệ."]}
    assert "latitude" not in str(payload)
