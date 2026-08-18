from decimal import Decimal

import pytest

from attendance.domain.attendance import is_inside, passes_accuracy


@pytest.mark.parametrize(
    ("accuracy", "threshold", "accepted"),
    [("25", "25", True), ("25.001", "25", False), ("-0.001", "25", False)],
)
def test_accuracy_gate_is_inclusive_and_independent(
    accuracy: str, threshold: str, accepted: bool
) -> None:
    assert passes_accuracy(Decimal(accuracy), Decimal(threshold)) is accepted


@pytest.mark.parametrize(
    ("distance", "radius", "accepted"),
    [("50", "50", True), ("60", "50", False), ("40", "50", True)],
)
def test_radius_gate_uses_distance_only(distance: str, radius: str, accepted: bool) -> None:
    assert is_inside(Decimal(distance), Decimal(radius)) is accepted


def test_chot_truth_table_does_not_subtract_accuracy_from_radius() -> None:
    assert passes_accuracy(Decimal("20"), Decimal("25"))
    assert is_inside(Decimal("40"), Decimal("50"))
    assert passes_accuracy(Decimal("5"), Decimal("25"))
    assert not is_inside(Decimal("60"), Decimal("50"))
