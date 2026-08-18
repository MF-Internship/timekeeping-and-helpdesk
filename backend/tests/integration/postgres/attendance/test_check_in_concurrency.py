from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import close_old_connections
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from attendance.models import AttendanceAttempt, AttendanceSession
from identity.models import User
from tests.integration.api.attendance.helpers import create_reference_data, gps_payload
from tests.integration.api.identity.helpers import ORIGIN

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


def test_concurrent_double_tap_has_one_winner_and_one_state_rejection() -> None:
    create_reference_data()
    for trial in range(100):
        _assert_trial(trial)


def _assert_trial(trial: int) -> None:
    user = User.objects.create(
        username=f"concurrent-check-in-{trial}",
        full_name=f"Concurrent {trial}",
        role="HELPDESK",
        password="!",
        must_change_password=False,
    )
    authorization = f"Bearer {AccessToken.for_user(user)}"
    results = _race(authorization)
    assert results == [(201, "ACCEPTED"), (409, "SESSION_ALREADY_OPEN")]
    assert AttendanceSession.objects.filter(user=user, check_out__isnull=True).count() == 1
    assert sorted(
        AttendanceAttempt.objects.filter(user=user).values_list("outcome", flat=True)
    ) == ["ACCEPTED", "SESSION_ALREADY_OPEN"]


def _race(authorization: str) -> list[tuple[int, str]]:
    barrier = Barrier(2)

    def punch() -> tuple[int, str]:
        close_old_connections()
        try:
            client = APIClient(
                HTTP_X_ORIGIN_CREDENTIAL=ORIGIN,
                HTTP_AUTHORIZATION=authorization,
            )
            barrier.wait()
            response = client.post("/api/v1/attendance/check-in", gps_payload(), format="json")
            return response.status_code, response.json().get("error_code", "ACCEPTED")
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(punch) for _ in range(2)]
        return sorted(future.result() for future in futures)
