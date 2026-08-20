from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2] / "locations"


@pytest.mark.architecture
def test_locations_exposes_no_attendance_or_task_workflow() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in ROOT.rglob("*.py")
        if "migrations" not in path.parts
    )
    forbidden = (
        "UNCERTAIN",
        "Attendance",
        "Task",
        "candidate_selection",
        "is_task_creator",
        "is_task_assignee",
        "owns_attendance",
    )
    assert not [term for term in forbidden if term in source]
