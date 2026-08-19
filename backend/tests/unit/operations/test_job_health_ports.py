from dataclasses import fields

import pytest

from identity.domain.authorization import JobHealthAccessScope
from operations.application.dependencies import JobHealthDependencies
from operations.ports.attendance_health import AttendanceHealthEvidence


@pytest.mark.unit
def test_health_dependencies_and_evidence_are_typed() -> None:
    assert {field.name for field in fields(JobHealthDependencies)} == {
        "authorization",
        "clock",
        "job_runs",
        "attendance_health",
        "read_unit_of_work_factory",
    }
    assert {field.name for field in fields(AttendanceHealthEvidence)} == {
        "overdue_open_session_count",
        "job_closed_session_count",
        "missing_checkout_anomaly_count",
        "job_closed_without_anomaly_count",
        "anomaly_without_job_closed_count",
    }
    assert {item.value for item in JobHealthAccessScope} == {"INVESTIGATE", "ESCALATE_ONLY"}
