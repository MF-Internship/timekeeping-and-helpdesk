from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from attendance.domain.sessions import SessionSnapshot


def is_reconciliation_candidate(session: SessionSnapshot, current_date: date) -> bool:
    return (
        session.work_date < current_date
        and session.check_out_id is None
        and not session.closed_by_job
    )


def ordered_candidate_ids(candidates: tuple[SessionSnapshot, ...]) -> tuple[int, ...]:
    return tuple(item.id for item in sorted(candidates, key=lambda item: (item.work_date, item.id)))


@dataclass(frozen=True, slots=True)
class ReconciliationOutcome:
    run_id: int
    status: str
    scanned_count: int
    changed_count: int
    anomaly_count: int
    error_code: str | None
