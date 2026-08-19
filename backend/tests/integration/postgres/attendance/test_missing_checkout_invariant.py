from datetime import timedelta

import pytest
from django.utils import timezone

from attendance.adapters.persistence.reconciliation import DjangoReconciliationRepository
from attendance.models import AttendanceAnomaly, AttendanceSession
from tests.integration.api.attendance.helpers import (
    create_reference_data,
    gps_payload,
    helpdesk_client,
)

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


def open_session(name: str) -> AttendanceSession:
    client, user = helpdesk_client(name)
    assert (
        client.post("/api/v1/attendance/check-in", gps_payload(), format="json").status_code == 201
    )
    session = AttendanceSession.objects.get(user=user)
    session.work_date = timezone.localdate() - timedelta(days=1)
    session.save(update_fields=["work_date"])
    return session


def test_health_evidence_detects_both_mismatch_directions_and_valid_pair() -> None:
    create_reference_data()
    without_anomaly = open_session("closed-without-anomaly")
    without_anomaly.closed_by_job = True
    without_anomaly.save(update_fields=["closed_by_job"])
    without_closed = open_session("anomaly-without-closed")
    AttendanceAnomaly.objects.create(
        attendance_id=without_closed.check_in_id,  # type: ignore[attr-defined]
        reason="MISSING_CHECK_OUT",
    )
    valid = open_session("valid-missing-pair")
    valid.closed_by_job = True
    valid.save(update_fields=["closed_by_job"])
    AttendanceAnomaly.objects.create(
        attendance_id=valid.check_in_id,  # type: ignore[attr-defined]
        reason="MISSING_CHECK_OUT",
    )
    evidence = DjangoReconciliationRepository().read_evidence(timezone.localdate())
    assert evidence.job_closed_session_count == 2
    assert evidence.missing_checkout_anomaly_count == 2
    assert evidence.job_closed_without_anomaly_count == 1
    assert evidence.anomaly_without_job_closed_count == 1
