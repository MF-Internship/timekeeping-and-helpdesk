import pytest

from attendance.models import Attendance, AttendanceAttempt, AttendanceSession
from tests.integration.api.attendance.helpers import (
    create_reference_data,
    gps_payload,
    helpdesk_client,
)

pytestmark = pytest.mark.django_db


def test_two_same_day_sessions_follow_strict_alternation() -> None:
    _, locations = create_reference_data(location_count=2)
    locations[1].latitude = "10.001000000000000"
    locations[1].save(update_fields=["latitude"])
    client, user = helpdesk_client("multiple-sessions")
    urls = ["check-in", "check-out", "check-in", "check-out"]
    payloads = [gps_payload(), gps_payload(latitude="10.001000000000000")] * 2
    responses = [
        client.post(f"/api/v1/attendance/{action}", payload, format="json")
        for action, payload in zip(urls, payloads, strict=True)
    ]
    assert [response.status_code for response in responses] == [201, 201, 201, 201]
    assert [response.json()["punch_index"] for response in responses] == [1, 2, 3, 4]
    assert list(
        Attendance.objects.filter(user=user).order_by("id").values_list("kind", flat=True)
    ) == ["IN", "OUT", "IN", "OUT"]
    assert AttendanceSession.objects.filter(user=user, check_out__isnull=False).count() == 2
    sessions = AttendanceSession.objects.filter(user=user).order_by("id")
    assert [(item.check_in.location_id, item.check_out.location_id) for item in sessions] == [
        (locations[0].pk, locations[1].pk),
        (locations[0].pk, locations[1].pk),
    ]
    assert AttendanceAttempt.objects.filter(user=user, outcome="ACCEPTED").count() == 4


def test_rejected_next_pair_does_not_mutate_completed_sessions() -> None:
    create_reference_data()
    client, user = helpdesk_client("multiple-sessions-rejected")
    for action in ("check-in", "check-out", "check-in", "check-out"):
        assert (
            client.post(f"/api/v1/attendance/{action}", gps_payload(), format="json").status_code
            == 201
        )
    before = list(
        AttendanceSession.objects.filter(user=user)
        .order_by("id")
        .values_list("check_in_id", "check_out_id", "duration_minutes")
    )
    outside = client.post(
        "/api/v1/attendance/check-in",
        gps_payload(latitude="10.001000000000000"),
        format="json",
    )
    invalid = client.post(
        "/api/v1/attendance/check-in",
        gps_payload(selected_location_id=999999),
        format="json",
    )
    assert outside.json()["error_code"] == "OUTSIDE_RADIUS"
    assert invalid.json()["error_code"] == "INVALID_LOCATION_CHOICE"
    after = list(
        AttendanceSession.objects.filter(user=user)
        .order_by("id")
        .values_list("check_in_id", "check_out_id", "duration_minutes")
    )
    assert after == before and Attendance.objects.filter(user=user).count() == 4
