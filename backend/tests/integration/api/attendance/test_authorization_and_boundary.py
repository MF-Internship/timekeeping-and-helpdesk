import pytest

from attendance.models import Attendance, AttendanceAttempt
from tests.integration.api.attendance.helpers import gps_payload
from tests.integration.api.identity.helpers import api_client, authenticated_client, create_user

pytestmark = pytest.mark.django_db

URL = "/api/v1/attendance/check-in"


def counts() -> tuple[int, int]:
    return Attendance.objects.count(), AttendanceAttempt.objects.count()


def test_unauthenticated_is_rejected_before_boundary() -> None:
    response = api_client().post(URL, gps_payload(), format="json")
    assert response.status_code == 401
    assert counts() == (0, 0)


@pytest.mark.parametrize("role", ["MANAGER", "LEADER"])
def test_non_helpdesk_role_is_denied_before_body_processing(role: str) -> None:
    client = authenticated_client(create_user(f"denied-{role.lower()}", role))
    response = client.post(URL, {"user_id": 12}, format="json")
    assert response.status_code == 403
    assert counts() == (0, 0)


def test_inactive_and_password_change_required_are_denied_before_boundary() -> None:
    inactive = create_user("inactive-attendance", "HELPDESK")
    forced = create_user("forced-attendance", "HELPDESK")
    inactive_client = authenticated_client(inactive)
    forced_client = authenticated_client(forced)
    inactive.is_active = False
    inactive.save(update_fields=["is_active"])
    forced.must_change_password = True
    forced.save(update_fields=["must_change_password"])
    inactive_response = inactive_client.post(URL, gps_payload(), format="json")
    forced_response = forced_client.post(URL, gps_payload(), format="json")
    assert (inactive_response.status_code, inactive_response.json()["error_code"]) == (
        401,
        "ACCOUNT_INACTIVE",
    )
    assert (forced_response.status_code, forced_response.json()["error_code"]) == (
        403,
        "PASSWORD_CHANGE_REQUIRED",
    )
    assert counts() == (0, 0)


@pytest.mark.parametrize("payload", [{}, {"user_id": 1}, {"kind": "OUT"}])
def test_invalid_or_server_owned_body_is_rejected_before_boundary(
    payload: dict[str, object],
) -> None:
    client = authenticated_client(
        create_user(f"body-{len(payload)}-{next(iter(payload), 'empty')}", "HELPDESK")
    )
    response = client.post(URL, payload, format="json")
    assert response.status_code == 400
    assert counts() == (0, 0)
