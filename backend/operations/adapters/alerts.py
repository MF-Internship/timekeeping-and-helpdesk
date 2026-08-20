from __future__ import annotations

import logging

from core.event_payload import sanitize_failure_reason

LOGGER = logging.getLogger("operations.alerts")


def emit_alert(
    reason: object,
    *,
    route_name: str = "unresolved",
    logger: logging.Logger = LOGGER,
) -> bool:
    safe_reason = sanitize_failure_reason(reason)
    safe_route = sanitize_failure_reason(route_name)
    try:
        logger.warning("alert route=%s reason=%s", safe_route, safe_reason)
    except Exception:
        return False
    return True
