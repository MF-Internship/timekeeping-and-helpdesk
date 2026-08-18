from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class AttendanceKind(StrEnum):
    IN = "IN"
    OUT = "OUT"


class LocationValidationResult(StrEnum):
    INSIDE_GEOFENCE = "INSIDE_GEOFENCE"


class AttendanceResolutionMethod(StrEnum):
    AUTO_SINGLE = "AUTO_SINGLE"
    USER_SELECTED = "USER_SELECTED"


class AttendanceAnomalyReason(StrEnum):
    LATE_CHECK_IN = "LATE_CHECK_IN"
    EARLY_CHECK_OUT = "EARLY_CHECK_OUT"
    LATE_CHECK_OUT = "LATE_CHECK_OUT"
    MISSING_CHECK_OUT = "MISSING_CHECK_OUT"


@dataclass(frozen=True, slots=True)
class LocationSnapshot:
    id: int
    code: str
    name: str
    address: str
    latitude: Decimal
    longitude: Decimal
    radius_m: Decimal
    is_active: bool


@dataclass(frozen=True, slots=True)
class LocationMatch:
    location: LocationSnapshot
    distance_m: Decimal


def passes_accuracy(accuracy_m: Decimal, threshold_m: Decimal) -> bool:
    return accuracy_m.is_finite() and accuracy_m >= 0 and accuracy_m <= threshold_m


def is_inside(distance_m: Decimal, radius_m: Decimal) -> bool:
    return (
        distance_m.is_finite()
        and radius_m.is_finite()
        and distance_m >= 0
        and radius_m > 0
        and distance_m <= radius_m
    )


def resolve_location(
    candidates: tuple[LocationMatch, ...], selected_location_id: int | None
) -> tuple[LocationMatch | None, AttendanceResolutionMethod | None]:
    if not candidates:
        return None, None
    if len(candidates) == 1 and selected_location_id is None:
        return candidates[0], AttendanceResolutionMethod.AUTO_SINGLE
    if selected_location_id is None:
        return None, None
    selected = next(
        (candidate for candidate in candidates if candidate.location.id == selected_location_id),
        None,
    )
    return (
        (selected, AttendanceResolutionMethod.USER_SELECTED)
        if selected is not None
        else (None, None)
    )


def decimal_distance(value: float) -> Decimal:
    if not math.isfinite(value) or value < 0:
        raise ValueError("distance_m")
    return Decimal(str(value)).quantize(Decimal("0.001"))
