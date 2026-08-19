from datetime import timedelta

import pytest
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


class FailingRepository(DjangoReconciliationRepository):
    def __init__(self, target: int) -> None:
        self.target = target
        self.failed = False

    def reconcile_locked(self, session_id, current_date):  # type: ignore[no-untyped-def]
        changed = super().reconcile_locked(session_id, current_date)
        if session_id == self.target and not self.failed:
            self.failed = True
            raise RuntimeError("injected anomaly persistence failure")
        return changed


class FailingCounter(DjangoReconciliationJobRuns):
    def __init__(self) -> None:
        super().__init__()
        self.changed_calls = 0

    def record_scan(self, run_id: int, *, changed: bool) -> None:
        super().record_scan(run_id, changed=changed)
        if changed:
            self.changed_calls += 1
        if self.changed_calls == 2:
            self.changed_calls += 1
            raise RuntimeError("injected counter failure")


def stale_sessions() -> list[AttendanceSession]:
    create_reference_data()
    result = []
    for index in range(3):
        client, user = helpdesk_client(f"partial-{index}")
        assert (
            client.post("/api/v1/attendance/check-in", gps_payload(), format="json").status_code
            == 201
        )
        session = AttendanceSession.objects.get(user=user)
        session.work_date = timezone.localdate() - timedelta(days=1)
        session.save(update_fields=["work_date"])
        result.append(session)
    return result


def run(repository, job_runs=None):  # type: ignore[no-untyped-def]
    return ReconciliationService(
        ReconciliationDependencies(
            DjangoClock(),
            repository,
            job_runs or DjangoReconciliationJobRuns(),
            DjangoUnitOfWork,
        )
    ).run()


@pytest.mark.parametrize("failure", ["anomaly", "counter"])
def test_per_session_failure_rolls_back_only_affected_session_and_retry_finishes(
    failure: str,
) -> None:
    sessions = stale_sessions()
    repository = (
        FailingRepository(sessions[1].pk)
        if failure == "anomaly"
        else DjangoReconciliationRepository()
    )
    result = run(repository, FailingCounter() if failure == "counter" else None)
    assert (result.status, result.scanned_count, result.changed_count, result.anomaly_count) == (
        "PARTIAL_FAILED",
        3,
        2,
        2,
    )
    states = list(AttendanceSession.objects.order_by("id").values_list("closed_by_job", flat=True))
    assert states == [True, False, True]
    assert AttendanceAnomaly.objects.filter(reason="MISSING_CHECK_OUT").count() == 2
    assert JobRun.objects.latest("id").error_code == "SESSION_PROCESSING_FAILED"

    retry = run(DjangoReconciliationRepository())
    assert (retry.status, retry.scanned_count, retry.changed_count) == ("SUCCEEDED", 1, 1)
    assert AttendanceSession.objects.filter(closed_by_job=True).count() == 3
    assert AttendanceAnomaly.objects.filter(reason="MISSING_CHECK_OUT").count() == 3
