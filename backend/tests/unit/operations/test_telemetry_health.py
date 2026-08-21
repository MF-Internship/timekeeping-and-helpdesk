from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from operations.domain.telemetry_health import OperationalHealthState, evaluate_heartbeat

NOW = datetime(2026, 8, 21, 3, tzinfo=UTC)


def test_never_seen_heartbeat_is_unknown() -> None:
    health = evaluate_heartbeat(now=NOW, last_success_at=None, stale_after_seconds=60)
    assert health.state is OperationalHealthState.UNKNOWN
    assert health.reason == "never_seen"


def test_stale_and_fresh_heartbeat_states() -> None:
    stale = evaluate_heartbeat(
        now=NOW,
        last_success_at=NOW - timedelta(seconds=61),
        stale_after_seconds=60,
    )
    assert stale.state is OperationalHealthState.ALERT
    fresh = evaluate_heartbeat(
        now=NOW,
        last_success_at=NOW - timedelta(seconds=60),
        stale_after_seconds=60,
    )
    assert fresh.state is OperationalHealthState.OK


def test_heartbeat_threshold_rejects_zero() -> None:
    with pytest.raises(ValueError):
        evaluate_heartbeat(now=NOW, last_success_at=NOW, stale_after_seconds=0)
