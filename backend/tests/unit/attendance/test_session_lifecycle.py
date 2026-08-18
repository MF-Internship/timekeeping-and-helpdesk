from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from attendance.domain.sessions import SessionSnapshot, duration_minutes, is_open_session


def test_duration_rounds_half_up_to_exactly_six_decimal_minutes() -> None:
    start = datetime(2026, 8, 18, tzinfo=UTC)
    assert duration_minutes(start, start + timedelta(microseconds=1)) == Decimal("0.000000")
    assert duration_minutes(start, start + timedelta(microseconds=30)) == Decimal("0.000001")


def test_session_open_predicate_and_work_date_are_inherited_from_check_in() -> None:
    work_date = date(2026, 8, 18)
    session = SessionSnapshot(1, 2, work_date, 3, None, None, False)
    assert is_open_session(session) and session.work_date == work_date
    assert not is_open_session(SessionSnapshot(1, 2, work_date, 3, 4, Decimal("1"), False))
    assert not is_open_session(SessionSnapshot(1, 2, work_date, 3, None, None, True))
