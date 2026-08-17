from __future__ import annotations

import logging

from core.correlation import get_correlation
from core.event_payload import sanitize_failure_reason


class CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        request_id, correlation_id = get_correlation()
        record.request_id = request_id
        record.correlation_id = correlation_id
        return True


def emit_safe_failure(
    logger: logging.Logger,
    reason: object,
    *,
    rule: str,
    path: str,
) -> bool:
    safe_reason = sanitize_failure_reason(reason)
    safe_rule = sanitize_failure_reason(rule)
    safe_path = sanitize_failure_reason(path)
    try:
        logger.error(
            "%s",
            safe_reason,
            extra={"rule_id": safe_rule, "artifact_path": safe_path, "failed": True},
        )
    except Exception:
        return False
    return True
