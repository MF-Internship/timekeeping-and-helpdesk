from datetime import UTC, datetime
from decimal import Decimal

import pytest

from attendance.adapters.persistence.attempts import DjangoAttemptWriter
from attendance.adapters.persistence.repositories import DjangoAttendanceRepository
from attendance.adapters.persistence.unit_of_work import DjangoUnitOfWork
from attendance.application.commands import AttendanceCommandService
from attendance.application.dependencies import AttendanceDependencies
from attendance.application.dto import AttendanceCommand
from attendance.models import Attendance, AttendanceAnomaly, AttendanceAttempt, AttendanceSession
from audit.domain.records import AuditEntry, OutboxRecord
from audit.models import AuditLog, OutboxEvent
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
    def now(self) -> datetime:
        return datetime(2026, 8, 18, 1, tzinfo=UTC)


class FailingAudit:
    def append_audit_entry(self, entry: AuditEntry) -> None:
        raise RuntimeError("audit unavailable")

    def append_outbox_event(self, event: OutboxRecord) -> None:
        raise AssertionError("attendance must not append outbox")


def test_audit_failure_rolls_back_business_state_and_creates_no_attempt() -> None:
    create_reference_data()
    user = User.objects.create(
        username="attendance-audit-rollback",
        full_name="Attendance Audit Rollback",
        role="HELPDESK",
        password="!",
        must_change_password=False,
    )
    service = AttendanceCommandService(
        AttendanceDependencies(
            Authorization(),
            Clock(),
            DjangoAttendanceReferenceData(),
            DjangoAttendanceRepository(),
            DjangoAttemptWriter(),
            FailingAudit(),
            DjangoUnitOfWork,
        )
    )
    with pytest.raises(RuntimeError):
        service.check_in(user.pk, AttendanceCommand(Decimal("10"), Decimal("106"), Decimal("5")))
    assert not Attendance.objects.exists()
    assert not AttendanceSession.objects.exists()
    assert not AttendanceAnomaly.objects.exists()
    assert not AttendanceAttempt.objects.exists()
    assert not AuditLog.objects.exists() and not OutboxEvent.objects.exists()
