from datetime import UTC, datetime
from decimal import Decimal

import pytest

from attendance.adapters.persistence.attempts import DjangoAttemptWriter
from attendance.adapters.persistence.repositories import DjangoAttendanceRepository
from attendance.adapters.persistence.unit_of_work import DjangoUnitOfWork
from attendance.application.commands import AttendanceCommandService
from attendance.application.dependencies import AttendanceDependencies
from attendance.application.dto import AttendanceCommand
from attendance.domain.attendance import AttendanceAnomalyReason
from attendance.models import Attendance, AttendanceAttempt, AttendanceSession
from audit.adapters.persistence.recording import DjangoAuditRecorder
from audit.models import AuditLog
from config.attendance_adapters import DjangoAttendanceReferenceData
from identity.models import User
from tests.integration.api.attendance.helpers import create_reference_data

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


class Authorization:
    def authorize_check_in(self, actor_id: int) -> None:
        return None

    def authorize_check_out(self, actor_id: int) -> None:
        return None

    def authorize_view_self(self, actor_id: int) -> None:
        return None


class Clock:
    def __init__(self) -> None:
        self.values = iter(
            (
                datetime(2026, 8, 18, 1, tzinfo=UTC),
                datetime(2026, 8, 18, 8, tzinfo=UTC),
                datetime(2026, 8, 18, 9, tzinfo=UTC),
                datetime(2026, 8, 18, 10, tzinfo=UTC),
            )
        )

    def now(self) -> datetime:
        return next(self.values)


class FailingReplacementRepository(DjangoAttendanceRepository):
    def __init__(self) -> None:
        self.fail = False

    def replace_anomalies(self, attendance_id, removable_reasons, reasons):  # type: ignore[no-untyped-def]
        super().replace_anomalies(attendance_id, removable_reasons, reasons)
        if self.fail and not reasons:
            raise RuntimeError("injected anomaly replacement failure")


def test_final_out_replacement_failure_rolls_back_whole_punch_transaction() -> None:
    create_reference_data()
    user = User.objects.create(
        username="anomaly-rollback",
        full_name="Anomaly Rollback",
        role="HELPDESK",
        password="!",
        must_change_password=False,
    )
    repository = FailingReplacementRepository()
    service = AttendanceCommandService(
        AttendanceDependencies(
            Authorization(),
            Clock(),
            DjangoAttendanceReferenceData(),
            repository,
            DjangoAttemptWriter(),
            DjangoAuditRecorder(),
            DjangoUnitOfWork,
        )
    )
    command = AttendanceCommand(Decimal("10"), Decimal("106"), Decimal("5"))
    service.check_in(user.pk, command)
    service.check_out(user.pk, command)
    service.check_in(user.pk, command)
    before = (
        Attendance.objects.count(),
        AttendanceSession.objects.filter(check_out__isnull=False).count(),
        AuditLog.objects.count(),
        AttendanceAttempt.objects.count(),
    )
    previous_out = Attendance.objects.filter(kind="OUT").get()
    assert previous_out.anomalies.filter(reason=AttendanceAnomalyReason.EARLY_CHECK_OUT).exists()
    repository.fail = True
    with pytest.raises(RuntimeError, match="injected anomaly replacement failure"):
        service.check_out(user.pk, command)
    assert previous_out.anomalies.filter(reason=AttendanceAnomalyReason.EARLY_CHECK_OUT).exists()
    assert (
        Attendance.objects.count(),
        AttendanceSession.objects.filter(check_out__isnull=False).count(),
        AuditLog.objects.count(),
        AttendanceAttempt.objects.count(),
    ) == before
