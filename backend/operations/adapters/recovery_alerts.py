from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from core.logging import emit_safe_failure


@dataclass(frozen=True, slots=True)
class RecoveryHealthSinks:
    logger: logging.Logger
    telemetry: Callable[[str], None]


def request_alert(sinks: RecoveryHealthSinks, reason: object) -> bool:
    return emit_safe_failure(
        sinks.logger,
        reason,
        rule="RECOVERY-HEALTH",
        path="restore_drill",
    )


def emit_health_state(sinks: RecoveryHealthSinks, state: str) -> bool:
    try:
        sinks.telemetry(state)
    except Exception:
        return False
    return True
