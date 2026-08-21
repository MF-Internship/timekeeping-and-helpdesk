from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from core.event_payload import sanitize_failure_reason

LOGGER = logging.getLogger("operations.metrics")


class MetricValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    labels: Mapping[str, frozenset[str]]


@dataclass(frozen=True, slots=True)
class MetricSample:
    name: str
    labels: Mapping[str, str]
    value: float = 1


METRIC_REGISTRY: Mapping[str, MetricDefinition] = {
    "outbox_relay_events_total": MetricDefinition(
        {"state": frozenset({"published", "failed", "dead_letter", "lost_claim"})}
    ),
    "retention_pruned_total": MetricDefinition(
        {"category": frozenset({"processed_event", "outbox_published", "outbox_dead_letter"})}
    ),
    "operations_health_state_total": MetricDefinition(
        {"state": frozenset({"ok", "alert", "unknown"})}
    ),
}


def validate_metric(name: str, labels: Mapping[str, str]) -> None:
    definition = METRIC_REGISTRY.get(name)
    if definition is None:
        raise MetricValidationError(name)
    if set(labels) != set(definition.labels):
        raise MetricValidationError(name)
    for key, value in labels.items():
        if value not in definition.labels[key]:
            raise MetricValidationError(name)


def emit_metric(
    sink: Callable[[str, Mapping[str, str], float], None],
    sample: MetricSample,
    *,
    logger: logging.Logger = LOGGER,
) -> bool:
    try:
        validate_metric(sample.name, sample.labels)
    except MetricValidationError:
        _warn(logger, f"invalid metric {sample.name}")
        return False
    try:
        sink(sample.name, dict(sample.labels), sample.value)
    except Exception as error:
        _warn(logger, f"metric sink failed {error}")
        return False
    return True


def _warn(logger: logging.Logger, reason: object) -> None:
    try:
        logger.warning("%s", sanitize_failure_reason(reason))
    except Exception:
        return
