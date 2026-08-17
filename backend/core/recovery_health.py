from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum


class RestoreHealthState(StrEnum):
    UNKNOWN = "unknown"
    OK = "ok"
    ALERT = "alert"


class RestoreHealthConfigurationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RestoreDrillEvidence:
    status: str
    recorded_at: datetime | None


@dataclass(frozen=True, slots=True)
class RestoreHealth:
    state: RestoreHealthState
    reason: str


def restore_drill_max_age_seconds(values: Mapping[str, str]) -> int:
    raw = values.get("HEALTH_RESTORE_DRILL_SECONDS", "")
    try:
        seconds = int(raw)
    except ValueError as error:
        raise RestoreHealthConfigurationError("HEALTH_RESTORE_DRILL_SECONDS") from error
    if seconds <= 0:
        raise RestoreHealthConfigurationError("HEALTH_RESTORE_DRILL_SECONDS")
    return seconds


def evaluate_restore_health(
    evidence: RestoreDrillEvidence | None,
    now: datetime,
    max_age_seconds: int,
) -> RestoreHealth:
    if evidence is None or evidence.recorded_at is None:
        return RestoreHealth(RestoreHealthState.UNKNOWN, "restore drill has never run")
    if evidence.status != "passed":
        return RestoreHealth(RestoreHealthState.ALERT, "restore drill did not pass")
    recorded_at = evidence.recorded_at.astimezone(UTC)
    if now.astimezone(UTC) - recorded_at > timedelta(seconds=max_age_seconds):
        return RestoreHealth(RestoreHealthState.ALERT, "restore drill evidence is stale")
    return RestoreHealth(RestoreHealthState.OK, "restore drill evidence is current")
