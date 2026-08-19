from datetime import UTC, date, datetime

from attendance.domain.reconciliation import is_reconciliation_candidate, ordered_candidate_ids
from attendance.domain.sessions import SessionSnapshot
from operations.domain.job_runs import JobRunStatus, classify_terminal


def session(identifier: int, work_date: date, *, checkout: int | None = None, closed: bool = False):  # type: ignore[no-untyped-def]
    return SessionSnapshot(identifier, 1, work_date, identifier, checkout, None, closed)


def test_eligibility_is_only_prior_date_canonical_open_and_has_deterministic_order() -> None:
    current = date(2026, 8, 19)
    candidates = (
        session(4, date(2026, 8, 18)),
        session(2, date(2026, 8, 17)),
        session(3, date(2026, 8, 18)),
    )
    assert ordered_candidate_ids(candidates) == (2, 3, 4)
    assert is_reconciliation_candidate(candidates[0], current)
    assert not is_reconciliation_candidate(session(5, current), current)
    assert not is_reconciliation_candidate(session(6, date(2026, 8, 18), checkout=9), current)
    assert not is_reconciliation_candidate(session(7, date(2026, 8, 18), closed=True), current)


def test_outcomes_cover_zero_work_session_error_and_abort() -> None:
    assert (
        classify_terminal(0, session_failed=False, aborted=False).status is JobRunStatus.SUCCEEDED
    )
    assert (
        classify_terminal(1, session_failed=True, aborted=False).status
        is JobRunStatus.PARTIAL_FAILED
    )
    assert classify_terminal(0, session_failed=True, aborted=False).status is JobRunStatus.FAILED
    assert classify_terminal(0, session_failed=False, aborted=True).status is JobRunStatus.FAILED


def test_reconciliation_domain_has_no_calendar_configuration_inputs() -> None:
    from inspect import signature

    assert set(signature(is_reconciliation_candidate).parameters) == {"session", "current_date"}
    assert datetime(2026, 8, 18, tzinfo=UTC).date().weekday() >= 0
