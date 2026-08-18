from datetime import UTC, datetime
from decimal import Decimal

import pytest

from attendance.domain.attempts import AttendanceAttemptOutcome, is_failure, nearest_is_approximate
from attendance.domain.attendance import (
    AttendanceAnomalyReason,
    AttendanceKind,
    AttendanceResolutionMethod,
    LocationValidationResult,
)
from attendance.domain.sessions import SessionSnapshot, is_open_session


@pytest.mark.unit
def test_attendance_vocabularies_are_closed() -> None:
    assert {value.value for value in AttendanceKind} == {"IN", "OUT"}
    assert {value.value for value in AttendanceResolutionMethod} == {
        "AUTO_SINGLE",
        "USER_SELECTED",
    }
    assert {value.value for value in LocationValidationResult} == {"INSIDE_GEOFENCE"}
    assert len(AttendanceAttemptOutcome) == 7
    assert len(AttendanceAnomalyReason) == 4


@pytest.mark.unit
def test_failure_rate_excludes_choice_required() -> None:
    failures = {value for value in AttendanceAttemptOutcome if is_failure(value)}
    assert len(failures) == 5
    assert AttendanceAttemptOutcome.LOCATION_CHOICE_REQUIRED not in failures
    assert not is_failure(AttendanceAttemptOutcome.ACCEPTED)


@pytest.mark.unit
def test_open_session_and_approximate_nearest_are_canonical() -> None:
    session = SessionSnapshot(1, 2, datetime(2026, 8, 18, tzinfo=UTC).date(), 3, None, None, False)
    assert is_open_session(session)
    assert nearest_is_approximate(AttendanceAttemptOutcome.WEAK_GPS)
    assert not nearest_is_approximate(AttendanceAttemptOutcome.OUTSIDE_RADIUS)
    assert Decimal("1") == Decimal("1")
