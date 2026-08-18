import pytest

from attendance.models import Attendance, AttendanceAttempt, AttendanceSession
from audit.models import AuditLog, OutboxEvent
from tests.integration.api.attendance.helpers import (
    create_reference_data,
    gps_payload,
    helpdesk_client,
)

pytestmark = pytest.mark.django_db


def test_check_in_duplicate_check_in_and_check_out_lifecycle() -> None:
    create_reference_data()
    client, user = helpdesk_client()

    check_in = client.post("/api/v1/attendance/check-in", gps_payload(), format="json")
    assert check_in.status_code == 201, check_in.json()
    body = check_in.json()
    assert body["attendance"]["kind"] == "IN"
    assert body["attendance"]["resolution_method"] == "AUTO_SINGLE"
    assert body["attendance"]["resolved_address"] == "Test Address 1"
    assert body["attendance"]["maps_url"].endswith("q=10.000000000000000%2C106.000000000000000")
    assert body["punch_index"] == 1

    duplicate = client.post("/api/v1/attendance/check-in", gps_payload(), format="json")
    assert duplicate.status_code == 409
    assert duplicate.json()["error_code"] == "SESSION_ALREADY_OPEN"

    check_out = client.post("/api/v1/attendance/check-out", gps_payload(), format="json")
    assert check_out.status_code == 201, check_out.json()
    assert check_out.json()["punch_index"] == 2
    assert check_out.json()["session"]["check_out_at"] is not None
    assert Attendance.objects.filter(user=user).count() == 2
    assert AttendanceSession.objects.filter(user=user, check_out__isnull=False).count() == 1
    assert AttendanceAttempt.objects.filter(user=user).count() == 3
    assert AuditLog.objects.filter(actor=user).count() == 2
    assert OutboxEvent.objects.count() == 0


def test_check_out_without_session_is_rejected_and_attempted() -> None:
    create_reference_data()
    client, user = helpdesk_client("no-open-session")
    response = client.post("/api/v1/attendance/check-out", gps_payload(), format="json")
    assert response.status_code == 409
    assert response.json()["error_code"] == "NO_OPEN_SESSION"
    assert Attendance.objects.filter(user=user).count() == 0
    assert AttendanceAttempt.objects.get(user=user).outcome == "NO_OPEN_SESSION"
