from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AttendanceHealthEvidence:
    overdue_open_session_count: int
    job_closed_session_count: int
    missing_checkout_anomaly_count: int
    job_closed_without_anomaly_count: int
    anomaly_without_job_closed_count: int


class AttendanceHealthReader(Protocol):
    def read_evidence(self, current_date: date) -> AttendanceHealthEvidence: ...
