from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from locations.domain.locations import LocationKind

CENTER_HEADERS = frozenset({"Mã TTKD", "Tên", "ADDRESS", "LATITUDE", "LONGITUDE"})
SHOP_HEADERS = frozenset({"SHOP_CODE", "NAME", "ADDRESS", "LATITUDE", "LONGITUDE"})


@dataclass(frozen=True, slots=True)
class SourceLocation:
    code: str
    name: str
    address: str
    latitude: Decimal
    longitude: Decimal
    kind: LocationKind
    parent_code: str | None


class LocationSource(Protocol):
    def load(self, center_path: Path, shop_path: Path) -> tuple[SourceLocation, ...]: ...
