from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol

from attendance.domain.attempts import AttendanceAttemptOutcome
from attendance.domain.attendance import AttendanceKind


@dataclass(frozen=True, slots=True)
class AttemptDraft:
    user_id: int
    kind: AttendanceKind
    work_date: date
    recorded_at: datetime
    outcome: AttendanceAttemptOutcome
    attendance_id: int | None
    latitude: Decimal
    longitude: Decimal
    accuracy_m: Decimal
    nearest_location_id: int | None
    nearest_distance_m: Decimal | None
    candidate_count: int | None
    device_metadata: dict[str, object]
    request_ip: str | None


class AttemptWriter(Protocol):
    def append(self, draft: AttemptDraft) -> None: ...
