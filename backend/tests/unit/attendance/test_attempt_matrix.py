from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from attendance.domain.attempts import AttendanceAttemptOutcome
from attendance.domain.attendance import AttendanceKind
from attendance.ports.attempts import AttemptDraft
from tests.unit.attendance.test_commands import COMMAND, service


class Writer:
    def __init__(self) -> None:
        self.values: list[AttemptDraft] = []

    def append(self, draft: AttemptDraft) -> None:
        self.values.append(draft)


@pytest.mark.parametrize(
    ("outcome", "attendance_id", "candidate_count"),
    [
        (AttendanceAttemptOutcome.ACCEPTED, 1, 1),
        (AttendanceAttemptOutcome.WEAK_GPS, None, None),
        (AttendanceAttemptOutcome.OUTSIDE_RADIUS, None, 0),
        (AttendanceAttemptOutcome.LOCATION_CHOICE_REQUIRED, None, 2),
        (AttendanceAttemptOutcome.INVALID_LOCATION_CHOICE, None, 1),
        (AttendanceAttemptOutcome.NO_OPEN_SESSION, None, None),
        (AttendanceAttemptOutcome.SESSION_ALREADY_OPEN, None, None),
    ],
)
def test_seven_outcome_attempt_contract_is_exactly_once(
    outcome: AttendanceAttemptOutcome, attendance_id: int | None, candidate_count: int | None
) -> None:
    writer = Writer()
    writer.append(
        AttemptDraft(
            42,
            AttendanceKind.IN,
            date(2026, 8, 18),
            datetime(2026, 8, 18, tzinfo=UTC),
            outcome,
            attendance_id,
            Decimal("10"),
            Decimal("106"),
            Decimal("5"),
            7,
            Decimal("0"),
            candidate_count,
            {},
            None,
        )
    )
    assert len(writer.values) == 1
    draft = writer.values[0]
    assert (draft.attendance_id is not None) is (outcome is AttendanceAttemptOutcome.ACCEPTED)
    assert draft.candidate_count == candidate_count
    assert not hasattr(draft, "location_candidates")


def test_unexpected_infrastructure_and_writer_failure_never_retry() -> None:
    failing, _repository, attempts, _audit = service(reference_fails=True)
    with pytest.raises(RuntimeError):
        failing.check_in(42, COMMAND)
    assert attempts.values == []
    accepted, _repository, writer_attempts, _audit = service(writer_fails=True)
    assert accepted.check_in(42, COMMAND).attendance.id == 1
    assert len(writer_attempts.values) == 1
