from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

NOW = datetime(2026, 8, 17, tzinfo=UTC)


def test_never_run_is_unknown() -> None:
    from core.recovery_health import RestoreHealthState, evaluate_restore_health

    assert evaluate_restore_health(None, NOW, 3600).state is RestoreHealthState.UNKNOWN


def test_stale_current_and_failed_evidence_are_deterministic() -> None:
    from core.recovery_health import (
        RestoreDrillEvidence,
        RestoreHealthState,
        evaluate_restore_health,
    )

    current = RestoreDrillEvidence("passed", NOW - timedelta(seconds=3599))
    stale = RestoreDrillEvidence("passed", NOW - timedelta(seconds=3601))
    failed = RestoreDrillEvidence("failed", NOW)
    assert evaluate_restore_health(current, NOW, 3600).state is RestoreHealthState.OK
    assert evaluate_restore_health(stale, NOW, 3600).state is RestoreHealthState.ALERT
    assert evaluate_restore_health(failed, NOW, 3600).state is RestoreHealthState.ALERT


@pytest.mark.parametrize("value", ["", "0", "-1", "invalid"])
def test_invalid_restore_drill_threshold_fails_closed(value: str) -> None:
    from core.recovery_health import RestoreHealthConfigurationError, restore_drill_max_age_seconds

    with pytest.raises(RestoreHealthConfigurationError, match="HEALTH_RESTORE_DRILL_SECONDS"):
        restore_drill_max_age_seconds({"HEALTH_RESTORE_DRILL_SECONDS": value})
