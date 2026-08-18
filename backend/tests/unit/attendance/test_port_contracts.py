from collections.abc import Callable
from dataclasses import fields

import pytest

from attendance.application.dependencies import AttendanceDependencies
from attendance.application.dto import AttendanceCommand, TodayAttendance


@pytest.mark.unit
def test_dependencies_expose_all_approved_boundaries() -> None:
    assert {field.name for field in fields(AttendanceDependencies)} == {
        "authorization",
        "clock",
        "reference_data",
        "repository",
        "attempts",
        "audit",
        "unit_of_work_factory",
    }
    assert Callable


@pytest.mark.unit
def test_command_and_today_dtos_do_not_accept_server_owned_identity() -> None:
    assert {field.name for field in fields(AttendanceCommand)} == {
        "latitude",
        "longitude",
        "accuracy_m",
        "captured_at",
        "selected_location_id",
        "device_metadata",
        "request_ip",
    }
    assert "user_id" not in {field.name for field in fields(TodayAttendance)}
