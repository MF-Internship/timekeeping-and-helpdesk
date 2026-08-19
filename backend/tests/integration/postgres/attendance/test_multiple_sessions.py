from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from django.db import connection

from attendance.adapters.persistence.repositories import DjangoAttendanceRepository
from attendance.models import Attendance, AttendanceSession
from tests.integration.api.attendance.helpers import (
    create_reference_data,
    gps_payload,
    helpdesk_client,
)
from tests.integration.api.identity.helpers import create_user

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


def test_two_pairs_are_allowed_without_any_daily_kind_unique_constraint() -> None:
    create_reference_data()
    client, user = helpdesk_client("postgres-multiple-sessions")
    for action in ("check-in", "check-out", "check-in", "check-out"):
        response = client.post(f"/api/v1/attendance/{action}", gps_payload(), format="json")
        assert response.status_code == 201
    assert Attendance.objects.filter(user=user, kind="IN").count() == 2
    assert Attendance.objects.filter(user=user, kind="OUT").count() == 2
    assert AttendanceSession.objects.filter(user=user).count() == 2
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conrelid = 'attendance_attendance'::regclass AND contype = 'u'"
        )
        definitions = [row[0] for row in cursor.fetchall()]
    assert all("work_date" not in value or "kind" not in value for value in definitions)


@pytest.mark.parametrize("completed_count", range(1, 21))
def test_total_sums_only_completed_rows_for_one_to_twenty_sessions(
    completed_count: int,
) -> None:
    _, locations = create_reference_data()
    user = create_user(f"postgres-total-{completed_count}", "HELPDESK")
    work_date = date(2026, 8, 18)
    base = datetime(2026, 8, 18, tzinfo=UTC)
    for index in range(completed_count):
        check_in = _attendance(user.pk, locations[0].pk, base, "IN")
        check_out = _attendance(
            user.pk,
            locations[0].pk,
            base + timedelta(minutes=index + 1),
            "OUT",
        )
        AttendanceSession.objects.create(
            user=user,
            work_date=work_date,
            check_in=check_in,
            check_out=check_out,
            duration_minutes=Decimal(index + 1),
        )
    open_in = _attendance(user.pk, locations[0].pk, base, "IN")
    AttendanceSession.objects.create(user=user, work_date=work_date, check_in=open_in)
    closed_in = _attendance(user.pk, locations[0].pk, base, "IN")
    AttendanceSession.objects.create(
        user=user,
        work_date=work_date,
        check_in=closed_in,
        closed_by_job=True,
    )

    repository = DjangoAttendanceRepository()
    assert repository.total_duration(user.pk, work_date) == Decimal(
        completed_count * (completed_count + 1) // 2
    )
    assert len(repository.sessions(user.pk, work_date)) == completed_count + 2


def _attendance(
    user_id: int,
    location_id: int,
    recorded_at: datetime,
    kind: str,
) -> Attendance:
    return Attendance.objects.create(
        user_id=user_id,
        kind=kind,
        work_date=recorded_at.date(),
        recorded_at=recorded_at,
        captured_latitude=Decimal("10"),
        captured_longitude=Decimal("106"),
        accuracy_m=Decimal("5"),
        location_id=location_id,
        distance_m=Decimal("0"),
        validation_result="INSIDE_GEOFENCE",
        resolution_method="AUTO_SINGLE",
    )
