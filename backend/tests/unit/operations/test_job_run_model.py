import pytest
from django.db.models import CheckConstraint

from operations.models import JobRun


@pytest.mark.unit
def test_job_run_fields_defaults_constraints_and_indexes_are_closed() -> None:
    assert {field.name for field in JobRun._meta.fields} == {
        "id",
        "job_name",
        "started_at",
        "finished_at",
        "status",
        "scanned_count",
        "changed_count",
        "anomaly_count",
        "error_code",
    }
    for name in ("status", "scanned_count", "changed_count", "anomaly_count"):
        assert JobRun._meta.get_field(name).db_default is not None
    constraint_names = {
        constraint.name
        for constraint in JobRun._meta.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert constraint_names == {
        "job_run_name_valid",
        "job_run_status_valid",
        "job_run_error_valid",
        "job_run_terminal_shape",
        "job_run_finish_order",
        "job_run_counts_valid",
        "job_run_failure_shape",
    }
    assert {index.name for index in JobRun._meta.indexes} == {
        "job_run_started_idx",
        "job_run_status_idx",
    }
