from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class LocationKind(StrEnum):
    BUSINESS_CENTER = "BUSINESS_CENTER"
    SHOP = "SHOP"


class LocationWarning(StrEnum):
    GEOFENCE_OVERLAP = "GEOFENCE_OVERLAP"
    RADIUS_BELOW_ATTENDANCE_ACCURACY = "RADIUS_BELOW_ATTENDANCE_ACCURACY"


@dataclass(frozen=True, slots=True)
class LocationWarningDetail:
    code: LocationWarning
    related_location_ids: tuple[int, ...] = ()
    related_location_codes: tuple[str, ...] = ()
    radius_m: Decimal | None = None
    threshold_m: Decimal | None = None


@dataclass(frozen=True, slots=True)
class Coordinates:
    latitude: Decimal
    longitude: Decimal

    def __post_init__(self) -> None:
        if not self.latitude.is_finite() or not Decimal("-90") <= self.latitude <= Decimal("90"):
            raise ValueError("latitude")
        if not self.longitude.is_finite() or not Decimal("-180") <= self.longitude <= Decimal(
            "180"
        ):
            raise ValueError("longitude")


@dataclass(frozen=True, slots=True)
class LocationSnapshot:
    id: int
    code: str
    name: str
    kind: LocationKind
    parent_id: int | None
    parent_code: str | None
    address: str
    latitude: Decimal
    longitude: Decimal
    radius_m: Decimal
    is_active: bool
    version: int


@dataclass(frozen=True, slots=True)
class LocationCandidate:
    name: str
    address: str
    latitude: Decimal
    longitude: Decimal
    radius_m: Decimal
    is_active: bool


def validate_location_candidate(candidate: LocationCandidate, max_radius_m: Decimal) -> None:
    Coordinates(candidate.latitude, candidate.longitude)
    if not candidate.name.strip():
        raise ValueError("name")
    if not candidate.address.strip():
        raise ValueError("address")
    if not candidate.radius_m.is_finite() or candidate.radius_m <= 0:
        raise ValueError("radius_m")
    if candidate.radius_m > max_radius_m:
        raise ValueError("radius_m")
