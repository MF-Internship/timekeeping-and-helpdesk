from decimal import Decimal

import pytest

from locations.domain.geofence import ValidatedPosition


@pytest.mark.parametrize(
    ("latitude", "longitude", "accuracy"),
    [
        ("NaN", "0", "0"),
        ("Infinity", "0", "0"),
        ("91", "0", "0"),
        ("0", "181", "0"),
        ("0", "0", "-1"),
    ],
)
def test_invalid_positions_are_rejected(latitude: str, longitude: str, accuracy: str) -> None:
    with pytest.raises(ValueError):
        ValidatedPosition(Decimal(latitude), Decimal(longitude), Decimal(accuracy))


@pytest.mark.parametrize(("latitude", "longitude"), [("-90", "-180"), ("90", "180")])
def test_inclusive_boundaries_and_zero_accuracy_are_valid(latitude: str, longitude: str) -> None:
    assert ValidatedPosition(Decimal(latitude), Decimal(longitude), Decimal("0"))
