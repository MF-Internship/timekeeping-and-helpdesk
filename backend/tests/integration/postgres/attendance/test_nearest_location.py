import pytest

from attendance.models import AttendanceAttempt
from tests.integration.api.attendance.helpers import (
    create_reference_data,
    gps_payload,
    helpdesk_client,
)

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


def test_equal_distance_nearest_uses_code_and_returns_both_candidates() -> None:
    _, locations = create_reference_data(
        location_count=2, location_codes=("HCM010005", "HCM000079")
    )
    client, user = helpdesk_client("nearest-code-tie")
    response = client.post("/api/v1/attendance/check-in", gps_payload(), format="json")
    assert response.json()["error_code"] == "LOCATION_CHOICE_REQUIRED"
    assert {item["code"] for item in response.json()["location_candidates"]} == {
        "HCM000079",
        "HCM010005",
    }
    assert AttendanceAttempt.objects.get(user=user).nearest_location.code == "HCM000079"


def test_inactive_nearest_is_diagnostic_only_and_never_a_candidate() -> None:
    _, locations = create_reference_data(
        location_count=2, location_codes=("HCM000079", "HCM010005")
    )
    locations[0].is_active = False
    locations[0].save(update_fields=["is_active"])
    client, user = helpdesk_client("inactive-nearest")
    response = client.post("/api/v1/attendance/check-in", gps_payload(), format="json")
    assert response.status_code == 201
    assert response.json()["attendance"]["location"]["code"] == "HCM010005"
    assert AttendanceAttempt.objects.get(user=user).nearest_location.code == "HCM000079"
