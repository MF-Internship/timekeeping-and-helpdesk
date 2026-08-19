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
from attendance.models import AttendanceAnomaly, AttendanceSession
from config.operations_adapters import DjangoReconciliationJobRuns
from operations.models import JobRun
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


def test_overlapping_invocations_change_each_session_once_across_three_trials() -> None:
    create_reference_data()
    for trial in range(3):
        client, user = helpdesk_client(f"reconcile-race-{trial}")
        assert (
            client.post("/api/v1/attendance/check-in", gps_payload(), format="json").status_code
            == 201
        )
        session = AttendanceSession.objects.get(user=user)
        session.work_date = timezone.localdate() - timedelta(days=1)
        session.save(update_fields=["work_date"])
        barrier = Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(_invoke, barrier) for _ in range(2)]
            results = sorted(future.result() for future in futures)
        assert results == [(1, 0), (1, 1)]
        assert (
            AttendanceAnomaly.objects.filter(
                attendance_id=session.check_in_id,
                reason="MISSING_CHECK_OUT",  # type: ignore[attr-defined]
            ).count()
            == 1
        )
    assert JobRun.objects.count() == 6


def _invoke(barrier: Barrier) -> tuple[int, int]:
    close_old_connections()
    try:
        result = ReconciliationService(
            ReconciliationDependencies(
                DjangoClock(),
                BarrierRepository(barrier),
                DjangoReconciliationJobRuns(),
                DjangoUnitOfWork,
            )
        ).run()
        return result.scanned_count, result.changed_count
    finally:
        close_old_connections()
