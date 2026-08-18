from __future__ import annotations

import pytest

from core.errors import build_error_envelope


@pytest.mark.unit
@pytest.mark.parametrize("code", ["NOT_FOUND", "LOCATION_VERSION_CONFLICT"])
def test_location_errors_use_canonical_envelope(code: str) -> None:
    payload = build_error_envelope(code, "request-1", {"version": ["2"]})
    assert payload["error"] == payload["error_code"] == code
    assert payload["request_id"] == "request-1"
    assert payload["details"] == {"version": ["2"]}


@pytest.mark.unit
def test_location_error_rejects_unsafe_details() -> None:
    with pytest.raises(ValueError):
        build_error_envelope("NOT_FOUND", "request-1", {"latitude": ["10.123456789"]})
