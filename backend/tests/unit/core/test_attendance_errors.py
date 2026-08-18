import pytest

from core.error_codes import (
    INVALID_LOCATION_CHOICE,
    LOCATION_CHOICE_REQUIRED,
    NO_OPEN_SESSION,
    OUTSIDE_RADIUS,
    SESSION_ALREADY_OPEN,
    WEAK_GPS,
)
from core.errors import build_error_envelope


@pytest.mark.unit
@pytest.mark.parametrize(
    "code",
    [
        WEAK_GPS,
        OUTSIDE_RADIUS,
        LOCATION_CHOICE_REQUIRED,
        INVALID_LOCATION_CHOICE,
        NO_OPEN_SESSION,
        SESSION_ALREADY_OPEN,
    ],
)
def test_attendance_error_codes_use_canonical_envelope(code: str) -> None:
    payload = build_error_envelope(code, "request-id")
    assert payload["error_code"] == payload["error"] == code
    assert payload["message"]
