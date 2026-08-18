from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class UpdateLocationRequest:
    version: int
    name: str | None = None
    address: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    radius_m: Decimal | None = None
    is_active: bool | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class LocationFilters:
    kind: str | None = None
    parent_id: int | None = None
    is_active: bool | None = None


@dataclass(frozen=True, slots=True)
class CreateHolidayRequest:
    date: date
    name: str
