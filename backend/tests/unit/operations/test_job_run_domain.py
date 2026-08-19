from dataclasses import replace
from datetime import UTC, datetime

import pytest

from operations.domain.job_runs import (
    JobName,
    JobRunErrorCode,
    JobRunSnapshot,
    JobRunStatus,
    classify_terminal,
)


@pytest.mark.unit
def test_job_run_vocabulary_is_closed() -> None:
    assert {item.value for item in JobName} == {"MISSING_CHECK_OUT"}
    assert {item.value for item in JobRunStatus} == {
        "RUNNING",
        "SUCCEEDED",
        "PARTIAL_FAILED",
        "FAILED",
    }
    assert {item.value for item in JobRunErrorCode} == {
        "SESSION_PROCESSING_FAILED",
        "RUN_ABORTED",
    }


@pytest.mark.unit
@pytest.mark.parametrize(
    ("inputs", "expected"),
    [
        ((0, False, False), (JobRunStatus.SUCCEEDED, None)),
        ((3, False, False), (JobRunStatus.SUCCEEDED, None)),
        (
            (2, True, False),
            (JobRunStatus.PARTIAL_FAILED, JobRunErrorCode.SESSION_PROCESSING_FAILED),
        ),
        ((0, True, False), (JobRunStatus.FAILED, JobRunErrorCode.SESSION_PROCESSING_FAILED)),
        ((2, False, True), (JobRunStatus.FAILED, JobRunErrorCode.RUN_ABORTED)),
    ],
)
def test_terminal_classification(
    inputs: tuple[int, bool, bool],
    expected: tuple[JobRunStatus, JobRunErrorCode | None],
) -> None:
    changed_count, session_failed, aborted = inputs
    result = classify_terminal(changed_count, session_failed=session_failed, aborted=aborted)
    assert (result.status, result.error_code) == expected


@pytest.mark.unit
def test_only_running_snapshot_can_be_terminalized() -> None:
    snapshot = JobRunSnapshot(
        1,
        JobName.MISSING_CHECK_OUT,
        datetime(2026, 8, 19, tzinfo=UTC),
        None,
        JobRunStatus.RUNNING,
        0,
        0,
        0,
        None,
    )
    assert snapshot.can_terminalize
    assert not replace(
        snapshot,
        status=JobRunStatus.SUCCEEDED,
        finished_at=snapshot.started_at,
    ).can_terminalize
