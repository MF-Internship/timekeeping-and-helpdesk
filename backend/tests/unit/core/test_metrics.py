from __future__ import annotations

import logging

import pytest

from core.metrics import MetricSample, MetricValidationError, emit_metric, validate_metric


class CollectingHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_validate_metric_rejects_unknown_name_label_key_and_value() -> None:
    validate_metric("outbox_relay_events_total", {"state": "published"})
    with pytest.raises(MetricValidationError):
        validate_metric("unknown_metric", {"state": "published"})
    with pytest.raises(MetricValidationError):
        validate_metric("outbox_relay_events_total", {"worker": "a"})
    with pytest.raises(MetricValidationError):
        validate_metric("outbox_relay_events_total", {"state": "event-123"})


def test_emit_metric_drops_invalid_metric_and_warns_once_without_label_value() -> None:
    logger = logging.Logger("metric-test")
    handler = CollectingHandler()
    logger.addHandler(handler)
    calls: list[tuple[str, dict[str, str], float]] = []
    emitted = emit_metric(
        lambda name, labels, value: calls.append((name, dict(labels), value)),
        MetricSample("outbox_relay_events_total", {"state": "event-123"}),
        logger=logger,
    )
    assert not emitted
    assert calls == []
    assert len(handler.records) == 1
    assert "outbox_relay_events_total" in handler.records[0].getMessage()
    assert "event-123" not in handler.records[0].getMessage()


def test_metric_sink_failure_is_contained_and_sanitized() -> None:
    logger = logging.Logger("metric-failure-test")
    handler = CollectingHandler()
    logger.addHandler(handler)

    def fail(name: str, labels: object, value: float) -> None:
        del name, labels, value
        raise RuntimeError("bad https://example.invalid/?token=secret 10.785850")

    assert not emit_metric(
        fail,
        MetricSample("outbox_relay_events_total", {"state": "failed"}),
        logger=logger,
    )
    text = handler.records[0].getMessage()
    assert "https://" not in text
    assert "token=" not in text
    assert "10.785850" not in text
