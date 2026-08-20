from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum


class OperationalHealthState(StrEnum):
    OK = "ok"
    ALERT = "alert"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class HeartbeatHealth:
    state: OperationalHealthState
    reason: str


def evaluate_heartbeat(
    *,
    now: datetime,
    last_success_at: datetime | None,
    stale_after_seconds: int,
) -> HeartbeatHealth:
    if stale_after_seconds < 1:
        raise ValueError("stale_after_seconds must be positive")
    if last_success_at is None:
        return HeartbeatHealth(OperationalHealthState.UNKNOWN, "never_seen")
    if last_success_at < now - timedelta(seconds=stale_after_seconds):
        return HeartbeatHealth(OperationalHealthState.ALERT, "stale")
    return HeartbeatHealth(OperationalHealthState.OK, "fresh")
