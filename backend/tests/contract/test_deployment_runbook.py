from __future__ import annotations

from pathlib import Path


def test_feature003_reference_data_release_order_is_mandatory() -> None:
    text = Path("docs/TRIEN_KHAI.md").read_text(encoding="utf-8")
    positions = [
        text.index(value)
        for value in (
            "migration before rollout",
            "initialize_location_config",
            "seed_locations",
            "verify_location_reference_ready",
            "enable route/UI Feature 003",
        )
    ]
    assert positions == sorted(positions)
    assert "Chỉ exit code `0`" in text


def test_feature004_attendance_enablement_reuses_read_only_readiness_gate() -> None:
    text = Path("docs/TRIEN_KHAI.md").read_text(encoding="utf-8")
    assert text.index("verify_location_reference_ready") < text.index(
        "enable route/UI Feature 004 Attendance"
    )
    assert "không sửa Config, Location hoặc Attendance" in text
