from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True, slots=True)
class SessionSnapshot:
    id: int
    user_id: int
    work_date: date
    check_in_id: int
    check_out_id: int | None
    duration_minutes: Decimal | None
    closed_by_job: bool


def is_open_session(session: SessionSnapshot) -> bool:
    return session.check_out_id is None and not session.closed_by_job


def duration_minutes(check_in_at: datetime, check_out_at: datetime) -> Decimal:
    seconds = Decimal(str((check_out_at - check_in_at).total_seconds()))
    if seconds < 0:
        raise ValueError("duration_minutes")
    return (seconds / Decimal("60")).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
