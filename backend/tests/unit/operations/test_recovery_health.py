from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from operations.adapters.recovery_alerts import RecoveryHealthSinks

NOW = datetime(2026, 8, 17, tzinfo=UTC)


class CollectingHandler(logging.Handler):
    def __init__(self, *, fail: bool = False) -> None:
        super().__init__()
        self.fail = fail
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        if self.fail:
            raise RuntimeError("alert sink failed")
        self.messages.append(record.getMessage())


def sinks(handler: logging.Handler, telemetry: list[str]) -> RecoveryHealthSinks:
    logger = logging.Logger("recovery-health-test")
    logger.addHandler(handler)
    return RecoveryHealthSinks(logger, telemetry.append)


def test_unknown_and_stale_states_request_alert_and_emit_telemetry() -> None:
    from core.recovery_health import RestoreDrillEvidence, RestoreHealthState
    from operations.application.recovery_health import evaluate_and_publish_restore_health

    handler = CollectingHandler()
    telemetry: list[str] = []
    values = {"HEALTH_RESTORE_DRILL_SECONDS": "3600"}
    unknown = evaluate_and_publish_restore_health(None, NOW, values, sinks(handler, telemetry))
    stale_evidence = RestoreDrillEvidence("passed", NOW - timedelta(seconds=3601))
    stale = evaluate_and_publish_restore_health(
        stale_evidence, NOW, values, sinks(handler, telemetry)
    )
    assert unknown.state is RestoreHealthState.UNKNOWN
    assert stale.state is RestoreHealthState.ALERT
    assert len(handler.messages) == 2
    assert telemetry == ["unknown", "alert"]


def test_external_text_is_sanitized_and_sink_failures_are_contained() -> None:
    from core.recovery_health import RestoreDrillEvidence
    from operations.application.recovery_health import evaluate_and_publish_restore_health

    telemetry_calls = 0

    def failing_telemetry(_state: str) -> None:
        nonlocal telemetry_calls
        telemetry_calls += 1
        raise RuntimeError("telemetry unavailable")

    logger = logging.Logger("failing-recovery-health")
    logger.addHandler(CollectingHandler(fail=True))
    configured_sinks = RecoveryHealthSinks(logger, failing_telemetry)
    evidence = RestoreDrillEvidence("failed", NOW)
    result = evaluate_and_publish_restore_health(
        evidence,
        NOW,
        {"HEALTH_RESTORE_DRILL_SECONDS": "3600"},
        configured_sinks,
    )
    assert result.state.value == "alert"
    assert telemetry_calls == 1
