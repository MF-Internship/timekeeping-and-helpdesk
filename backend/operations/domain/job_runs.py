from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class JobName(StrEnum):
    MISSING_CHECK_OUT = "MISSING_CHECK_OUT"


class JobRunStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    PARTIAL_FAILED = "PARTIAL_FAILED"
    FAILED = "FAILED"


class JobRunErrorCode(StrEnum):
    SESSION_PROCESSING_FAILED = "SESSION_PROCESSING_FAILED"
    RUN_ABORTED = "RUN_ABORTED"


@dataclass(frozen=True, slots=True)
class JobRunTerminal:
    status: JobRunStatus
    error_code: JobRunErrorCode | None


@dataclass(frozen=True, slots=True)
class JobRunCounterDelta:
    scanned: int
    changed: int
    anomaly: int


@dataclass(frozen=True, slots=True)
class JobRunSnapshot:
    id: int
    job_name: JobName
    started_at: datetime
    finished_at: datetime | None
    status: JobRunStatus
    scanned_count: int
    changed_count: int
    anomaly_count: int
    error_code: JobRunErrorCode | None

    @property
    def can_terminalize(self) -> bool:
        return self.status is JobRunStatus.RUNNING


def classify_terminal(changed_count: int, *, session_failed: bool, aborted: bool) -> JobRunTerminal:
    if aborted:
        return JobRunTerminal(JobRunStatus.FAILED, JobRunErrorCode.RUN_ABORTED)
    if not session_failed:
        return JobRunTerminal(JobRunStatus.SUCCEEDED, None)
    if changed_count > 0:
        return JobRunTerminal(
            JobRunStatus.PARTIAL_FAILED,
            JobRunErrorCode.SESSION_PROCESSING_FAILED,
        )
    return JobRunTerminal(JobRunStatus.FAILED, JobRunErrorCode.SESSION_PROCESSING_FAILED)
