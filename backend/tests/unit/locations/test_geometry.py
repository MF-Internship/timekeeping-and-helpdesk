from decimal import Decimal

import pytest

from locations.domain.geofence import haversine_distance_m
from locations.domain.locations import Coordinates


def point(latitude: str, longitude: str) -> Coordinates:
    return Coordinates(Decimal(latitude), Decimal(longitude))


def test_haversine_zero_symmetry_antimeridian_and_known_distance() -> None:
    origin = point("10", "106")
    destination = point("11", "106")
    assert haversine_distance_m(origin, origin) == 0
    assert haversine_distance_m(origin, destination) == pytest.approx(
        haversine_distance_m(destination, origin)
    )
    assert haversine_distance_m(point("0", "179.9"), point("0", "-179.9")) < 23_000
    assert haversine_distance_m(point("0", "0"), point("1", "0")) == pytest.approx(111_195, abs=10)
