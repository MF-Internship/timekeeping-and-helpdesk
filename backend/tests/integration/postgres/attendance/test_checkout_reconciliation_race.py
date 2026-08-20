from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from django.db import close_old_connections
from django.utils import timezone

from attendance.adapters.clock import DjangoClock
from attendance.adapters.persistence.reconciliation import DjangoReconciliationRepository
from attendance.adapters.persistence.unit_of_work import DjangoUnitOfWork
from attendance.application.reconciliation import ReconciliationDependencies, ReconciliationService
from attendance.models import Attendance, AttendanceAnomaly, AttendanceSession
from config.operations_adapters import DjangoReconciliationJobRuns
from tests.integration.api.attendance.helpers import (
    create_reference_data,
    gps_payload,
    helpdesk_client,
)

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


class BarrierRepository(DjangoReconciliationRepository):
    def __init__(self, barrier: Barrier) -> None:
        self.barrier = barrier

    def candidate_ids(self, current_date):  # type: ignore[no-untyped-def]
        result = super().candidate_ids(current_date)
        self.barrier.wait()
        return result


def test_checkout_and_reconciliation_have_exactly_one_winner_across_three_trials() -> None:
    create_reference_data()
    for trial in range(3):
        _assert_trial(trial)


def _assert_trial(trial: int) -> None:
    client, user = helpdesk_client(f"checkout-reconcile-{trial}")
    response = client.post("/api/v1/attendance/check-in", gps_payload(), format="json")
    assert response.status_code == 201
    session = AttendanceSession.objects.get(user=user)
    session.work_date = timezone.localdate() - timedelta(days=1)
    session.save(update_fields=["work_date"])
    changed, checkout = _race(client, Barrier(2))
    session.refresh_from_db()
    assert (changed, checkout) in {(1, (409, "NO_OPEN_SESSION")), (0, (201, "ACCEPTED"))}
    assert bool(session.closed_by_job) is (changed == 1)
    assert (session.check_out_id is not None) is (changed == 0)  # type: ignore[attr-defined]
    assert Attendance.objects.filter(user=user, kind="OUT").count() == int(changed == 0)
    missing_count = AttendanceAnomaly.objects.filter(
        attendance_id=session.check_in_id,  # type: ignore[attr-defined]
        reason="MISSING_CHECK_OUT",
    ).count()
    assert missing_count == changed


def _race(client, barrier: Barrier):  # type: ignore[no-untyped-def]
    with ThreadPoolExecutor(max_workers=2) as pool:
        job_future = pool.submit(_reconcile, barrier)
        checkout_future = pool.submit(_check_out, client, barrier)
        return job_future.result(), checkout_future.result()


def _reconcile(barrier: Barrier) -> int:
    close_old_connections()
    try:
        dependencies = ReconciliationDependencies(
            DjangoClock(),
            BarrierRepository(barrier),
            DjangoReconciliationJobRuns(),
            DjangoUnitOfWork,
        )
        return ReconciliationService(dependencies).run().changed_count
    finally:
        close_old_connections()


def _check_out(client, barrier: Barrier):  # type: ignore[no-untyped-def]
    close_old_connections()
    try:
        barrier.wait()
        response = client.post("/api/v1/attendance/check-out", gps_payload(), format="json")
        return response.status_code, response.json().get("error_code", "ACCEPTED")
    finally:
        close_old_connections()
