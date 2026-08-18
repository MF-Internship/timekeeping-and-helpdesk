import pytest
from django.db.models import UniqueConstraint

from attendance.models import Attendance, AttendanceAnomaly, AttendanceAttempt, AttendanceSession


@pytest.mark.unit
def test_attendance_models_have_expected_core_fields() -> None:
    assert {field.name for field in Attendance._meta.fields} >= {
        "user",
        "kind",
        "work_date",
        "recorded_at",
        "captured_latitude",
        "captured_longitude",
        "accuracy_m",
        "location",
        "distance_m",
        "validation_result",
        "resolution_method",
    }
    assert AttendanceSession._meta.get_field("closed_by_job").db_default is not None
    assert AttendanceAttempt._meta.get_field("device_metadata").db_default is not None
    assert AttendanceAnomaly._meta.get_field("metadata").db_default is not None


@pytest.mark.unit
def test_no_daily_kind_uniqueness_and_attempt_link_is_one_to_one() -> None:
    unique_fields = {
        tuple(constraint.fields)
        for constraint in Attendance._meta.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert ("user", "work_date", "kind") not in unique_fields
    assert AttendanceAttempt._meta.get_field("attendance").one_to_one
