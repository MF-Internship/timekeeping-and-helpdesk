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
