from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import pytest

from locations.adapters.source_data.csv_source import CsvLocationSource, SourceDataError

ROOT = Path(__file__).parents[4]


def _copy_with_change(source: Path, target: Path, field: str, value: str) -> None:
    with source.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
        headers = list(rows[0])
    rows[0][field] = value
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


@pytest.mark.unit
def test_preflight_rejects_cross_file_duplicate_code_and_invalid_coordinate(tmp_path: Path) -> None:
    center = ROOT / "docs/dia_chi_ttkd.csv"
    shop = ROOT / "docs/dia_chi_cua_hang.csv"
    duplicate = tmp_path / "duplicate.csv"
    _copy_with_change(shop, duplicate, "SHOP_CODE", "HCM020000")
    with pytest.raises(SourceDataError, match="duplicate code"):
        CsvLocationSource().load(center, duplicate)
    invalid = tmp_path / "invalid.csv"
    _copy_with_change(shop, invalid, "LATITUDE", "91")
    with pytest.raises(SourceDataError, match="invalid coordinate"):
        CsvLocationSource().load(center, invalid)


@pytest.mark.unit
def test_preflight_accepts_duplicate_coordinates_and_unmatched_parent() -> None:
    rows = CsvLocationSource().load(
        ROOT / "docs/dia_chi_ttkd.csv", ROOT / "docs/dia_chi_cua_hang.csv"
    )
    assert len(rows) == 76
    assert any(value > 1 for value in Counter((r.latitude, r.longitude) for r in rows).values())
    assert next(row for row in rows if row.code == "HCM000079").parent_code == "HCM000000"
