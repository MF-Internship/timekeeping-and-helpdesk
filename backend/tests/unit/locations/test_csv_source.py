from collections import Counter
from pathlib import Path

import pytest

from locations.adapters.source_data.csv_source import CsvLocationSource, SourceDataError
from locations.domain.locations import LocationKind

ROOT = Path(__file__).parents[4]


def test_canonical_csvs_use_separate_mappings_and_exact_counts() -> None:
    rows = CsvLocationSource().load(
        ROOT / "docs/dia_chi_ttkd.csv", ROOT / "docs/dia_chi_cua_hang.csv"
    )
    centers = [row for row in rows if row.kind is LocationKind.BUSINESS_CENTER]
    shops = [row for row in rows if row.kind is LocationKind.SHOP]
    assert (len(centers), len(shops), len(rows)) == (7, 69, 76)
    assert next(row for row in shops if row.code == "HCM020129").parent_code == "HCM020000"
    coordinates = Counter((row.latitude, row.longitude) for row in rows)
    assert any(count > 1 for count in coordinates.values())


def test_missing_header_is_rejected_before_rows(tmp_path: Path) -> None:
    center = tmp_path / "center.csv"
    center.write_text("Mã TTKD,Tên,ADDRESS,LATITUDE\n", encoding="utf-8")
    with pytest.raises(SourceDataError, match="LONGITUDE"):
        CsvLocationSource().load(center, ROOT / "docs/dia_chi_cua_hang.csv")
