from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import close_old_connections
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from attendance.models import Attendance, AttendanceAttempt, AttendanceSession
from identity.models import User
from tests.integration.api.attendance.helpers import create_reference_data, gps_payload
from tests.integration.api.identity.helpers import ORIGIN

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


def test_concurrent_check_out_has_one_winner_and_one_no_session() -> None:
    create_reference_data()
    user = User.objects.create(
        username="concurrent-check-out",
        full_name="Concurrent Check Out",
        role="HELPDESK",
        password="!",
        must_change_password=False,
    )
    authorization = f"Bearer {AccessToken.for_user(user)}"
    assert _post(authorization, "check-in")[0] == 201
    results = _race(authorization)
    assert results == [(201, "ACCEPTED"), (409, "NO_OPEN_SESSION")]
    session = AttendanceSession.objects.get(user=user)
    assert session.check_out_id is not None and session.duration_minutes is not None
    assert Attendance.objects.filter(user=user, kind="OUT").count() == 1
    assert sorted(
        AttendanceAttempt.objects.filter(user=user).values_list("outcome", flat=True)
    ) == ["ACCEPTED", "ACCEPTED", "NO_OPEN_SESSION"]


def _race(authorization: str) -> list[tuple[int, str]]:
    barrier = Barrier(2)

    def punch() -> tuple[int, str]:
        close_old_connections()
        try:
            barrier.wait()
            return _post(authorization, "check-out")
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(punch) for _ in range(2)]
        return sorted(future.result() for future in futures)


def _post(authorization: str, action: str) -> tuple[int, str]:
    client = APIClient(
        HTTP_X_ORIGIN_CREDENTIAL=ORIGIN,
        HTTP_AUTHORIZATION=authorization,
    )
    response = client.post(f"/api/v1/attendance/{action}", gps_payload(), format="json")
    return response.status_code, response.json().get("error_code", "ACCEPTED")
