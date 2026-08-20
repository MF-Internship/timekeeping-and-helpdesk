from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from locations.domain.locations import Coordinates

EARTH_RADIUS_M = 6_371_008.8


class LocationValidationResult(StrEnum):
    INSIDE_GEOFENCE = "INSIDE_GEOFENCE"
    OUTSIDE_GEOFENCE = "OUTSIDE_GEOFENCE"


@dataclass(frozen=True, slots=True)
class ValidatedPosition:
    latitude: Decimal
    longitude: Decimal
    accuracy_m: Decimal

    def __post_init__(self) -> None:
        Coordinates(self.latitude, self.longitude)
        if not self.accuracy_m.is_finite() or self.accuracy_m < 0:
            raise ValueError("accuracy_m")

    @property
    def coordinates(self) -> Coordinates:
        return Coordinates(self.latitude, self.longitude)


def haversine_distance_m(origin: Coordinates, destination: Coordinates) -> float:
    lat1, lon1 = math.radians(float(origin.latitude)), math.radians(float(origin.longitude))
    lat2, lon2 = (
        math.radians(float(destination.latitude)),
        math.radians(float(destination.longitude)),
    )
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return EARTH_RADIUS_M * 2 * math.asin(min(1.0, math.sqrt(value)))


def classify_geofence(distance_m: float, radius_m: Decimal) -> LocationValidationResult:
    if not math.isfinite(distance_m) or distance_m < 0:
        raise ValueError("distance_m")
    if not radius_m.is_finite() or radius_m <= 0:
        raise ValueError("radius_m")
    return (
        LocationValidationResult.INSIDE_GEOFENCE
        if distance_m <= float(radius_m)
        else LocationValidationResult.OUTSIDE_GEOFENCE
    )


def geofences_overlap(
    first: Coordinates, first_radius_m: Decimal, second: Coordinates, second_radius_m: Decimal
) -> bool:
    return haversine_distance_m(first, second) <= float(first_radius_m + second_radius_m)
