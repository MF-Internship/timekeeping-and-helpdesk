from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from attendance.domain.attendance import AttendanceAnomalyReason
from attendance.models import Attendance, AttendanceAnomaly, AttendanceAttempt, AttendanceSession
from audit.models import AuditLog, OutboxEvent
from locations.models import Holiday
from operations.models import JobRun
from tests.integration.api.attendance.helpers import (
    create_reference_data,
    gps_payload,
    helpdesk_client,
)

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


def test_daily_reconciliation_is_idempotent_and_does_not_invent_checkout() -> None:
    create_reference_data()
    client, user = helpdesk_client("reconcile-daily")
    assert (
        client.post("/api/v1/attendance/check-in", gps_payload(), format="json").status_code == 201
    )
    session = AttendanceSession.objects.get(user=user)
    session.work_date = timezone.localdate() - timedelta(days=1)
    session.save(update_fields=["work_date"])
    attendance_before = Attendance.objects.count()
    attempt_before = AttendanceAttempt.objects.count()
    audit_before = AuditLog.objects.count()
    outbox_before = OutboxEvent.objects.count()

    call_command("reconcile_missing_checkouts")
    for _ in range(3):
        call_command("reconcile_missing_checkouts")

    session.refresh_from_db()
    assert session.closed_by_job is True
    assert session.check_out_id is None  # type: ignore[attr-defined]
    assert session.duration_minutes is None
    assert (
        AttendanceAnomaly.objects.filter(
            attendance_id=session.check_in_id,  # type: ignore[attr-defined]
            reason=AttendanceAnomalyReason.MISSING_CHECK_OUT.value,
        ).count()
        == 1
    )
    assert Attendance.objects.count() == attendance_before
    assert AttendanceAttempt.objects.count() == attempt_before
    assert AuditLog.objects.count() == audit_before
    assert OutboxEvent.objects.count() == outbox_before
    assert list(JobRun.objects.values_list("status", "changed_count")) == [
        ("SUCCEEDED", 1),
        ("SUCCEEDED", 0),
        ("SUCCEEDED", 0),
        ("SUCCEEDED", 0),
    ]


def test_weekday_sunday_holiday_are_eligible_but_current_date_is_not() -> None:
    create_reference_data()
    current = timezone.localdate()
    sunday = current - timedelta(days=(current.weekday() + 1 or 7))
    holiday = sunday - timedelta(days=1)
    work_dates = (current - timedelta(days=1), sunday, holiday, current)
    sessions: list[AttendanceSession] = []
    clients = []
    for index, work_date in enumerate(work_dates):
        client, user = helpdesk_client(f"reconcile-calendar-{index}")
        clients.append(client)
        assert (
            client.post("/api/v1/attendance/check-in", gps_payload(), format="json").status_code
            == 201
        )
        session = AttendanceSession.objects.get(user=user)
        session.work_date = work_date
        session.save(update_fields=["work_date"])
        sessions.append(session)
    Holiday.objects.create(date=holiday, name="Configured holiday")

    call_command("reconcile_missing_checkouts")

    for session in sessions:
        session.refresh_from_db()
    assert [session.closed_by_job for session in sessions] == [True, True, True, False]
    assert AttendanceAnomaly.objects.filter(reason="MISSING_CHECK_OUT").count() == 3
    assert (
        clients[0].post("/api/v1/attendance/check-in", gps_payload(), format="json").status_code
        == 201
    )
