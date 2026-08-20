from __future__ import annotations

from enum import StrEnum


class AttendanceAttemptOutcome(StrEnum):
    ACCEPTED = "ACCEPTED"
    WEAK_GPS = "WEAK_GPS"
    OUTSIDE_RADIUS = "OUTSIDE_RADIUS"
    LOCATION_CHOICE_REQUIRED = "LOCATION_CHOICE_REQUIRED"
    INVALID_LOCATION_CHOICE = "INVALID_LOCATION_CHOICE"
    NO_OPEN_SESSION = "NO_OPEN_SESSION"
    SESSION_ALREADY_OPEN = "SESSION_ALREADY_OPEN"


FAILURE_OUTCOMES = frozenset(
    {
        AttendanceAttemptOutcome.WEAK_GPS,
        AttendanceAttemptOutcome.OUTSIDE_RADIUS,
        AttendanceAttemptOutcome.INVALID_LOCATION_CHOICE,
        AttendanceAttemptOutcome.NO_OPEN_SESSION,
        AttendanceAttemptOutcome.SESSION_ALREADY_OPEN,
    }
)


def is_failure(outcome: AttendanceAttemptOutcome) -> bool:
    return outcome in FAILURE_OUTCOMES


def nearest_is_approximate(outcome: AttendanceAttemptOutcome) -> bool:
    return outcome is AttendanceAttemptOutcome.WEAK_GPS
