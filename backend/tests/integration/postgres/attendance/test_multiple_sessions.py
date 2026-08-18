import pytest
from django.db import connection

from attendance.models import Attendance, AttendanceSession
from tests.integration.api.attendance.helpers import (
    create_reference_data,
    gps_payload,
    helpdesk_client,
)

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
