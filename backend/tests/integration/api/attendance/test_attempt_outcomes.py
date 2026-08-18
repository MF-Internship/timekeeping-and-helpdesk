import pytest

from attendance.models import AttendanceAttempt
from tests.integration.api.attendance.helpers import (
    create_reference_data,
    gps_payload,
    helpdesk_client,
)

pytestmark = pytest.mark.django_db


def test_all_seven_post_boundary_outcomes_and_pre_boundary_zero() -> None:
    _, locations = create_reference_data(location_count=2)
    selected = locations[0].pk
    accepted, _ = helpdesk_client("attempt-accepted")
    weak, _ = helpdesk_client("attempt-weak")
    outside, _ = helpdesk_client("attempt-outside")
    choice, _ = helpdesk_client("attempt-choice")
    invalid, _ = helpdesk_client("attempt-invalid")
    no_open, _ = helpdesk_client("attempt-no-open")
    session, session_user = helpdesk_client("attempt-session")
    assert (
        accepted.post(
            "/api/v1/attendance/check-in", gps_payload(selected_location_id=selected), format="json"
        ).status_code
        == 201
    )
    weak.post("/api/v1/attendance/check-in", gps_payload(accuracy_m="26"), format="json")
    outside.post("/api/v1/attendance/check-in", gps_payload(latitude="10.001"), format="json")
    choice.post("/api/v1/attendance/check-in", gps_payload(), format="json")
    invalid.post(
        "/api/v1/attendance/check-in", gps_payload(selected_location_id=999999), format="json"
    )
    no_open.post("/api/v1/attendance/check-out", gps_payload(), format="json")
    session.post(
        "/api/v1/attendance/check-in", gps_payload(selected_location_id=selected), format="json"
    )
    session.post(
        "/api/v1/attendance/check-in", gps_payload(selected_location_id=selected), format="json"
    )
    attempts = AttendanceAttempt.objects.order_by("outcome")
    assert set(attempts.values_list("outcome", flat=True)) == {
        "ACCEPTED",
        "WEAK_GPS",
        "OUTSIDE_RADIUS",
        "LOCATION_CHOICE_REQUIRED",
        "INVALID_LOCATION_CHOICE",
        "NO_OPEN_SESSION",
        "SESSION_ALREADY_OPEN",
    }
    assert attempts.filter(outcome="ACCEPTED", attendance__isnull=False).count() == 2
    assert not attempts.exclude(outcome="ACCEPTED").filter(attendance__isnull=False).exists()
    before = AttendanceAttempt.objects.count()
    session.post("/api/v1/attendance/check-in", {"user_id": session_user.pk}, format="json")
    assert AttendanceAttempt.objects.count() == before
