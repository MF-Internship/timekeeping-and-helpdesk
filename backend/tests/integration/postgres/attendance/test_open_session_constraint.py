from datetime import UTC, datetime
from decimal import Decimal

import pytest
from django.db import connection

from attendance.models import Attendance, AttendanceSession
from tests.integration.api.attendance.helpers import create_reference_data
from tests.integration.api.identity.helpers import create_user

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


def test_partial_unique_predicate_and_attempt_indexes_are_exact() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT indexname, indexdef FROM pg_indexes "
            "WHERE tablename IN ('attendance_attendancesession', 'attendance_attendanceattempt')"
        )
        indexes = dict(cursor.fetchall())
    assert "uniq_open_session_per_user" in indexes
    predicate = indexes["uniq_open_session_per_user"]
    assert "check_out_id IS NULL" in predicate and "NOT closed_by_job" in predicate
    assert {
        "attendance_attempt_time_idx",
        "attendance_attempt_outcome_idx",
        "attendance_attempt_nearest_idx",
    } <= indexes.keys()


def test_job_closed_null_checkout_does_not_block_new_open_session() -> None:
    _, (location,) = create_reference_data()
    user = create_user("job-closed", "HELPDESK")
    first = _attendance(user, location.pk, "IN")
    AttendanceSession.objects.create(
        user=user, work_date=first.work_date, check_in=first, closed_by_job=True
    )
    second = _attendance(user, location.pk, "IN")
    AttendanceSession.objects.create(user=user, work_date=second.work_date, check_in=second)
    assert AttendanceSession.objects.filter(user=user).count() == 2


def _attendance(user: object, location_id: int, kind: str) -> Attendance:
    now = datetime(2026, 8, 18, 4, tzinfo=UTC)
    return Attendance.objects.create(
        user=user,
        kind=kind,
        work_date=now.date(),
        recorded_at=now,
        captured_latitude=Decimal("10"),
        captured_longitude=Decimal("106"),
        accuracy_m=Decimal("5"),
        location_id=location_id,
        distance_m=Decimal("0"),
        validation_result="INSIDE_GEOFENCE",
        resolution_method="AUTO_SINGLE",
    )
