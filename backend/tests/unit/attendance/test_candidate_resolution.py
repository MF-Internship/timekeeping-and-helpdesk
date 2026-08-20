from decimal import Decimal

import pytest

from attendance.domain.attempts import AttendanceAttemptOutcome, nearest_is_approximate
from attendance.domain.attendance import (
    AttendanceResolutionMethod,
    LocationMatch,
    LocationSnapshot,
    resolve_location,
)


def match(identifier: int, code: str, distance: str, *, active: bool = True) -> LocationMatch:
    location = LocationSnapshot(
        identifier, code, code, code, Decimal("10"), Decimal("106"), Decimal("50"), active
    )
    return LocationMatch(location, Decimal(distance))


def test_zero_one_many_and_selected_resolution_are_closed() -> None:
    first, second = match(1, "A", "1"), match(2, "B", "2")
    assert resolve_location((), None) == (None, None)
    assert resolve_location((first,), None) == (first, AttendanceResolutionMethod.AUTO_SINGLE)
    assert resolve_location((first, second), None) == (None, None)
    assert resolve_location((first, second), 2) == (
        second,
        AttendanceResolutionMethod.USER_SELECTED,
    )
    assert resolve_location((first, second), 99) == (None, None)


def test_diagnostic_nearest_uses_distance_then_code_even_when_inactive() -> None:
    values = (match(2, "HCM010005", "0"), match(1, "HCM000079", "0", active=False))
    nearest = min(values, key=lambda item: (item.distance_m, item.location.code))
    assert nearest.location.code == "HCM000079" and not nearest.location.is_active


@pytest.mark.parametrize("outcome", AttendanceAttemptOutcome)
def test_nearest_is_approximate_only_for_weak_gps(outcome: AttendanceAttemptOutcome) -> None:
    assert nearest_is_approximate(outcome) is (outcome is AttendanceAttemptOutcome.WEAK_GPS)
