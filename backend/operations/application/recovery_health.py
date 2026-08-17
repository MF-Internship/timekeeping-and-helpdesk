from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from core.event_payload import sanitize_failure_reason
from core.recovery_health import (
    RestoreDrillEvidence,
    RestoreHealth,
    RestoreHealthState,
    evaluate_restore_health,
    restore_drill_max_age_seconds,
)
from operations.adapters.recovery_alerts import (
    RecoveryHealthSinks,
    emit_health_state,
    request_alert,
)


def evaluate_and_publish_restore_health(
    evidence: RestoreDrillEvidence | None,
    now: datetime,
    values: Mapping[str, str],
    sinks: RecoveryHealthSinks,
) -> RestoreHealth:
    max_age_seconds = restore_drill_max_age_seconds(values)
    health = evaluate_restore_health(evidence, now, max_age_seconds)
    safe_reason = sanitize_failure_reason(health.reason)
    if health.state in {RestoreHealthState.UNKNOWN, RestoreHealthState.ALERT}:
        request_alert(sinks, safe_reason)
    emit_health_state(sinks, health.state.value)
    return health
