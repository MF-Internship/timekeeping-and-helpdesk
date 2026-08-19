from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import pytest
from django.db import close_old_connections, transaction
from django.utils import timezone

from attendance.adapters.persistence.reconciliation import DjangoReconciliationRepository
from attendance.models import AttendanceSession
from config.operations_adapters import DjangoReadOnlyRepeatableRead
from identity.ports.authorization import JobHealthAccessScope
from operations.adapters.persistence.job_runs import DjangoJobRunRepository
from operations.application.dependencies import JobHealthDependencies
from operations.application.job_health import JobHealthService
from tests.integration.api.attendance.helpers import (
    create_reference_data,
    gps_payload,
    helpdesk_client,
)

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


class Authorization:
    def authorize_job_health(self, actor_id: int) -> JobHealthAccessScope:
        return JobHealthAccessScope.INVESTIGATE


class Clock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class PausingJobRuns(DjangoJobRunRepository):
    def __init__(self, barrier: Barrier) -> None:
        self.barrier = barrier

    def latest(self):  # type: ignore[no-untyped-def]
        result = super().latest()
        self.barrier.wait()
        self.barrier.wait()
        return result


def test_health_uses_one_repeatable_read_snapshot_during_reconciliation_commit() -> None:
    create_reference_data()
    client, user = helpdesk_client("health-snapshot")
    assert (
        client.post("/api/v1/attendance/check-in", gps_payload(), format="json").status_code == 201
    )
    session = AttendanceSession.objects.get(user=user)
    session.work_date = timezone.localdate() - timedelta(days=1)
    session.save(update_fields=["work_date"])
    barrier = Barrier(2)

    def write() -> None:
        close_old_connections()
        try:
            barrier.wait()
            with transaction.atomic():
                DjangoReconciliationRepository().reconcile_locked(session.pk, timezone.localdate())
            barrier.wait()
        finally:
            close_old_connections()

    dependencies = JobHealthDependencies(
        Authorization(),
        Clock(),
        PausingJobRuns(barrier),
        DjangoReconciliationRepository(),
        DjangoReadOnlyRepeatableRead,
    )
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(write)
        health = JobHealthService(dependencies).read(user.pk).health
        future.result()
    assert health.evidence.overdue_open_session_count == 1
    assert health.evidence.job_closed_session_count == 0
    assert AttendanceSession.objects.get(pk=session.pk).closed_by_job is True
