from datetime import timedelta

import pytest
from django.utils import timezone

from attendance.models import Attendance, AttendanceAttempt
from tests.integration.api.attendance.helpers import (
    create_reference_data,
    gps_payload,
    helpdesk_client,
)

pytestmark = pytest.mark.django_db


def test_quality_and_radius_are_independent_and_attempted() -> None:
    create_reference_data()
    client, user = helpdesk_client("gps-gates")
    weak = client.post(
        "/api/v1/attendance/check-in", gps_payload(accuracy_m="25.001"), format="json"
    )
    outside = client.post(
        "/api/v1/attendance/check-in",
        gps_payload(latitude="10.001000000000000", accuracy_m="5"),
        format="json",
    )
    assert (weak.status_code, weak.json()["error_code"]) == (422, "WEAK_GPS")
    assert (outside.status_code, outside.json()["error_code"]) == (422, "OUTSIDE_RADIUS")
    assert Attendance.objects.filter(user=user).count() == 0
    attempts = list(AttendanceAttempt.objects.filter(user=user).order_by("id"))
    assert [(item.outcome, item.candidate_count) for item in attempts] == [
        ("WEAK_GPS", None),
        ("OUTSIDE_RADIUS", 0),
    ]


def test_malformed_and_stale_samples_are_pre_boundary() -> None:
    create_reference_data()
    client, user = helpdesk_client("gps-pre-boundary")
    malformed = client.post(
        "/api/v1/attendance/check-in", gps_payload(latitude="NaN"), format="json"
    )
    stale = client.post(
        "/api/v1/attendance/check-in",
        gps_payload(captured_at=(timezone.now() - timedelta(seconds=61)).isoformat()),
        format="json",
    )
    assert malformed.status_code == stale.status_code == 400
    assert not AttendanceAttempt.objects.filter(user=user).exists()


def test_second_pair_repeats_quality_and_radius_gates() -> None:
    create_reference_data()
    client, user = helpdesk_client("gps-second-pair")
    for action in ("check-in", "check-out"):
        assert (
            client.post(f"/api/v1/attendance/{action}", gps_payload(), format="json").status_code
            == 201
        )
    weak = client.post(
        "/api/v1/attendance/check-in", gps_payload(accuracy_m="25.001"), format="json"
    )
    outside = client.post(
        "/api/v1/attendance/check-in",
        gps_payload(latitude="10.001000000000000"),
        format="json",
    )
    assert [weak.json()["error_code"], outside.json()["error_code"]] == [
        "WEAK_GPS",
        "OUTSIDE_RADIUS",
    ]
    assert Attendance.objects.filter(user=user).count() == 2
