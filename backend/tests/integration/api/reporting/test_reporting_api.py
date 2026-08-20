from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from attendance.domain.attempts import AttendanceAttemptOutcome
from attendance.domain.attendance import AttendanceAnomalyReason, AttendanceKind
from attendance.models import Attendance, AttendanceAnomaly, AttendanceAttempt, AttendanceSession
from audit.models import AuditLog
from tasks.domain.evidence import GpsQuality
from tasks.domain.tasks import CompletionMethod, TaskStatus
from tasks.models import TaskUpdate
from tests.integration.api.attendance.helpers import create_reference_data
from tests.integration.api.identity.helpers import authenticated_client, create_user
from tests.integration.api.tasks.helpers import create_task


@pytest.mark.django_db
def test_attendance_report_keeps_attempt_anomaly_and_failure_rate_semantics() -> None:
    _, locations = create_reference_data()
    user = create_user("helpdesk-report", "HELPDESK")
    client = authenticated_client(user)
    today = timezone.localdate()
    now = timezone.now()
    check_in = Attendance.objects.create(
        user=user,
        kind=AttendanceKind.IN.value,
        work_date=today,
        recorded_at=now,
        captured_latitude=Decimal("10.000000000000000"),
        captured_longitude=Decimal("106.000000000000000"),
        accuracy_m=Decimal("5.000"),
        location=locations[0],
        distance_m=Decimal("0.000"),
        validation_result="INSIDE_GEOFENCE",
        resolution_method="AUTO_SINGLE",
    )
    check_out = Attendance.objects.create(
        user=user,
        kind=AttendanceKind.OUT.value,
        work_date=today,
        recorded_at=now + timedelta(hours=8),
        captured_latitude=Decimal("10.000000000000000"),
        captured_longitude=Decimal("106.000000000000000"),
        accuracy_m=Decimal("5.000"),
        location=locations[0],
        distance_m=Decimal("0.000"),
        validation_result="INSIDE_GEOFENCE",
        resolution_method="AUTO_SINGLE",
    )
    AttendanceSession.objects.create(
        user=user,
        work_date=today,
        check_in=check_in,
        check_out=check_out,
        duration_minutes=Decimal("480.000000"),
    )
    AttendanceAnomaly.objects.create(
        attendance=check_in, reason=AttendanceAnomalyReason.LATE_CHECK_IN.value
    )
    _attempt(
        AttemptSeed(user, today, now, AttendanceAttemptOutcome.ACCEPTED.value, locations[0]),
        check_in,
    )
    _attempt(AttemptSeed(user, today, now, AttendanceAttemptOutcome.WEAK_GPS.value, locations[0]))
    _attempt(
        AttemptSeed(
            user,
            today,
            now,
            AttendanceAttemptOutcome.LOCATION_CHOICE_REQUIRED.value,
            locations[0],
        )
    )

    response = client.get(
        f"/api/v1/reports/attendance/?start_date={today.isoformat()}&end_date={today.isoformat()}"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["punch_count"] == 2
    assert payload["total_valid_worked_minutes"] == 480.0
    assert payload["anomaly_counts"] == {"LATE_CHECK_IN": 1}
    assert payload["attempt_counts"]["LOCATION_CHOICE_REQUIRED"] == 1
    assert payload["failure_rate"] == {
        "numerator": 1,
        "denominator": 2,
        "excluded_count": 1,
        "rate_percent": 50.0,
    }
    assert response["Cache-Control"] == "private, no-store"


@pytest.mark.django_db
def test_helpdesk_report_scope_is_self_even_with_user_filter() -> None:
    create_reference_data()
    owner = create_user("helpdesk-owner", "HELPDESK")
    other = create_user("helpdesk-other", "HELPDESK")
    client = authenticated_client(owner)
    today = timezone.localdate()
    create_task(owner, owner, assigned_date=today)
    create_task(owner, other, assigned_date=today)

    response = client.get(
        "/api/v1/reports/tasks/"
        f"?start_date={today.isoformat()}&end_date={today.isoformat()}&user_id={other.pk}"
    )

    assert response.status_code == 200
    assert response.json()["total_tasks"] == 1


@pytest.mark.django_db
def test_task_report_separates_completion_method_actual_completer_and_assigned_closed() -> None:
    create_reference_data()
    manager = create_user("manager-report", "MANAGER")
    assignee = create_user("task-assignee", "HELPDESK")
    client = authenticated_client(manager)
    today = timezone.localdate()
    task = create_task(
        manager,
        assignee,
        assigned_date=today,
        status=TaskStatus.COMPLETED.value,
    )
    TaskUpdate.objects.create(
        task=task,
        user=assignee,
        status=TaskStatus.COMPLETED.value,
        completion_method=CompletionMethod.FIELD_EVIDENCE.value,
        captured_latitude=Decimal("10.000000"),
        captured_longitude=Decimal("106.000000"),
        accuracy_m=Decimal("5.000"),
        captured_at=timezone.now(),
        gps_quality=GpsQuality.GOOD.value,
        resolution_method="GPS_ONLY",
    )

    response = client.get(
        f"/api/v1/reports/tasks/?start_date={today.isoformat()}&end_date={today.isoformat()}"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status_counts"]["COMPLETED"] == 1
    assert payload["completion_method_counts"] == {"MANAGER_OVERRIDE": 1, "FIELD_EVIDENCE": 0}
    assert payload["gps_quality_counts"]["GOOD"] == 1
    assert payload["actual_completer_counts"] == {str(manager.pk): 1}
    assert payload["assigned_task_closed_count"] == 1


@pytest.mark.django_db
def test_export_requires_export_permission_audits_and_uses_no_store_csv() -> None:
    create_reference_data()
    helpdesk = create_user("helpdesk-no-export", "HELPDESK")
    manager = create_user("manager-export", "MANAGER")
    today = timezone.localdate()

    denied = authenticated_client(helpdesk).get(
        f"/api/v1/reports/tasks/export/?start_date={today.isoformat()}&end_date={today.isoformat()}"
    )
    assert denied.status_code == 403
    assert not AuditLog.objects.exists()

    response = authenticated_client(manager).get(
        f"/api/v1/reports/tasks/export/?start_date={today.isoformat()}&end_date={today.isoformat()}"
    )

    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"
    assert response["Content-Type"].startswith("text/csv")
    assert "total_tasks" in response.content.decode()
    assert AuditLog.objects.filter(action="report.exported", actor=manager).count() == 1


@dataclass(frozen=True, slots=True)
class AttemptSeed:
    user: object
    work_date: object
    recorded_at: object
    outcome: str
    location: object


def _attempt(seed: AttemptSeed, attendance: Attendance | None = None) -> None:
    AttendanceAttempt.objects.create(
        user=seed.user,
        kind=AttendanceKind.IN.value,
        work_date=seed.work_date,
        recorded_at=seed.recorded_at,
        outcome=seed.outcome,
        attendance=attendance,
        captured_latitude=Decimal("10.000000000000000"),
        captured_longitude=Decimal("106.000000000000000"),
        accuracy_m=Decimal("5.000"),
        nearest_location=seed.location,
        nearest_distance_m=Decimal("0.000"),
    )
