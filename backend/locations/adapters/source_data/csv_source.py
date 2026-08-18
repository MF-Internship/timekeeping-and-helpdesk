from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from locations.domain.locations import Coordinates, LocationKind
from locations.ports.source_data import CENTER_HEADERS, SHOP_HEADERS, SourceLocation


class SourceDataError(ValueError):
    pass


class CsvLocationSource:
    def load(self, center_path: Path, shop_path: Path) -> tuple[SourceLocation, ...]:
        centers = self._read(center_path, CENTER_HEADERS, LocationKind.BUSINESS_CENTER)
        shops = self._read(shop_path, SHOP_HEADERS, LocationKind.SHOP)
        if len(centers) != 7:
            raise SourceDataError(f"{center_path.name}: expected 7 rows")
        if len(shops) != 69:
            raise SourceDataError(f"{shop_path.name}: expected 69 rows")
        rows = centers + shops
        codes = [row.code for row in rows]
        duplicates = sorted({code for code in codes if codes.count(code) > 1})
        if duplicates:
            raise SourceDataError(f"duplicate code: {duplicates[0]}")
        return tuple(rows)

    def _read(
        self, path: Path, required: frozenset[str], kind: LocationKind
    ) -> list[SourceLocation]:
        try:
            stream = path.open(encoding="utf-8-sig", newline="")
        except OSError as error:
            raise SourceDataError(f"{path.name}: unreadable") from error
        with stream:
            reader = csv.DictReader(stream)
            headers = set(reader.fieldnames or ())
            missing = sorted(required - headers)
            if missing:
                raise SourceDataError(f"{path.name}: missing header {missing[0]}")
            return [self._map_row(path, index, row, kind) for index, row in enumerate(reader, 2)]

    @staticmethod
    def _map_row(
        path: Path, index: int, row: dict[str, str | None], kind: LocationKind
    ) -> SourceLocation:
        code_key, name_key = (
            ("Mã TTKD", "Tên") if kind is LocationKind.BUSINESS_CENTER else ("SHOP_CODE", "NAME")
        )
        code = (row.get(code_key) or "").strip()
        name = (row.get(name_key) or "").strip()
        address = (row.get("ADDRESS") or "").strip()
        if not code or not name or not address:
            raise SourceDataError(f"{path.name}: invalid row {index}")
        try:
            latitude = Decimal((row.get("LATITUDE") or "").strip())
            longitude = Decimal((row.get("LONGITUDE") or "").strip())
            Coordinates(latitude, longitude)
        except (InvalidOperation, ValueError) as error:
            raise SourceDataError(f"{path.name}: invalid coordinate at row {index}") from error
        parent_code = None if kind is LocationKind.BUSINESS_CENTER else f"{code[:5]}0000"
        return SourceLocation(code, name, address, latitude, longitude, kind, parent_code)
