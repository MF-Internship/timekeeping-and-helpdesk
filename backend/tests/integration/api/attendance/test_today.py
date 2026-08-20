import pytest

from attendance.models import AttendanceSession
from tests.integration.api.attendance.helpers import (
    create_reference_data,
    gps_payload,
    helpdesk_client,
)
from tests.integration.api.identity.helpers import authenticated_client, create_user

pytestmark = pytest.mark.django_db


def test_today_is_actor_scoped_and_projects_next_action() -> None:
    create_reference_data()
    client, actor = helpdesk_client("today-actor")
    other, other_user = helpdesk_client("today-other")
    assert (
        client.post("/api/v1/attendance/check-in", gps_payload(), format="json").status_code == 201
    )
    assert (
        other.post("/api/v1/attendance/check-in", gps_payload(), format="json").status_code == 201
    )
    response = client.get("/api/v1/attendance/today")
    assert response.status_code == 200, response.json()
    assert response.json()["has_open_session"] is True
    assert [item["punch_index"] for item in response.json()["punches"]] == [1]
    assert len(response.json()["sessions"]) == 1
    assert response.json()["punches"][0]["id"] != other_user.attendance_set.get().pk
    assert actor.attendance_set.get().pk == response.json()["punches"][0]["id"]


def test_today_does_not_accept_client_user_scope() -> None:
    client, _ = helpdesk_client("today-scope")
    response = client.get("/api/v1/attendance/today?user_id=999")
    assert response.status_code == 400
    body = client.generic(
        "GET", "/api/v1/attendance/today", {"user_id": 999}, content_type="application/json"
    )
    assert body.status_code == 400


def test_today_projects_job_closed_without_counting_duration_or_open_state() -> None:
    create_reference_data()
    client, user = helpdesk_client("today-job-closed")
    assert (
        client.post("/api/v1/attendance/check-in", gps_payload(), format="json").status_code == 201
    )
    AttendanceSession.objects.filter(user=user).update(closed_by_job=True)
    response = client.get("/api/v1/attendance/today")
    assert response.status_code == 200
    assert response.json()["has_open_session"] is False
    assert response.json()["total_duration_minutes"] == "0.000000"
    assert response.json()["sessions"][0]["closed_by_job"] is True


@pytest.mark.parametrize("role", ["MANAGER", "LEADER"])
def test_today_view_all_implication_still_rejects_client_object_scope(role: str) -> None:
    client = authenticated_client(create_user(f"today-{role.lower()}", role))
    response = client.get("/api/v1/attendance/today?user_id=1")
    assert response.status_code == 400


def test_today_account_state_precedes_client_scope_validation() -> None:
    inactive = create_user("today-inactive", "HELPDESK")
    forced = create_user("today-forced", "HELPDESK")
    inactive_client = authenticated_client(inactive)
    forced_client = authenticated_client(forced)
    inactive.is_active = False
    inactive.save(update_fields=["is_active"])
    forced.must_change_password = True
    forced.save(update_fields=["must_change_password"])
    inactive_response = inactive_client.get("/api/v1/attendance/today?user_id=1")
    forced_response = forced_client.get("/api/v1/attendance/today?user_id=1")
    assert (inactive_response.status_code, inactive_response.json()["error_code"]) == (
        401,
        "ACCOUNT_INACTIVE",
    )
    assert (forced_response.status_code, forced_response.json()["error_code"]) == (
        403,
        "PASSWORD_CHANGE_REQUIRED",
    )
