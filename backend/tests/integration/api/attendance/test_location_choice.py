import pytest

from attendance.models import AttendanceAttempt
from tests.integration.api.attendance.helpers import (
    create_reference_data,
    gps_payload,
    helpdesk_client,
)

pytestmark = pytest.mark.django_db


def test_multiple_candidates_require_and_revalidate_choice() -> None:
    _, locations = create_reference_data(location_count=2)
    client, user = helpdesk_client("location-choice")
    required = client.post("/api/v1/attendance/check-in", gps_payload(), format="json")
    assert (required.status_code, required.json()["error_code"]) == (
        409,
        "LOCATION_CHOICE_REQUIRED",
    )
    assert len(required.json()["location_candidates"]) == 2
    invalid = client.post(
        "/api/v1/attendance/check-in", gps_payload(selected_location_id=999999), format="json"
    )
    assert (invalid.status_code, invalid.json()["error_code"]) == (
        422,
        "INVALID_LOCATION_CHOICE",
    )
    accepted = client.post(
        "/api/v1/attendance/check-in",
        gps_payload(selected_location_id=locations[1].pk),
        format="json",
    )
    assert accepted.status_code == 201
    assert accepted.json()["attendance"]["location"]["id"] == locations[1].pk
    assert accepted.json()["attendance"]["resolution_method"] == "USER_SELECTED"
    assert list(AttendanceAttempt.objects.filter(user=user).values_list("outcome", flat=True)) == [
        "LOCATION_CHOICE_REQUIRED",
        "INVALID_LOCATION_CHOICE",
        "ACCEPTED",
    ]
    assert not hasattr(AttendanceAttempt, "location_candidates")


def test_zero_candidates_has_outside_precedence_over_supplied_choice() -> None:
    create_reference_data(location_count=2)
    client, user = helpdesk_client("location-choice-outside")
    response = client.post(
        "/api/v1/attendance/check-in",
        gps_payload(latitude="10.001000000000000", selected_location_id=999999),
        format="json",
    )
    assert (response.status_code, response.json()["error_code"]) == (422, "OUTSIDE_RADIUS")
    assert "location_candidates" not in response.json()
    attempt = AttendanceAttempt.objects.get(user=user)
    assert attempt.candidate_count == 0 and attempt.outcome == "OUTSIDE_RADIUS"
