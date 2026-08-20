from __future__ import annotations

import logging

from operations.adapters.alerts import emit_alert


class CollectingHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


class FailingHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        raise RuntimeError("sink down")


def test_alert_sanitizes_reason_and_route_name() -> None:
    logger = logging.Logger("alert-test")
    handler = CollectingHandler()
    logger.addHandler(handler)
    assert emit_alert(
        "bad https://example.invalid/?token=secret 10.785850",
        route_name="/api/raw?token=secret",
        logger=logger,
    )
    text = handler.records[0].getMessage()
    assert "https://" not in text
    assert "token=" not in text
    assert "10.785850" not in text


def test_alert_sink_failure_is_contained() -> None:
    logger = logging.Logger("alert-failing-test")
    logger.addHandler(FailingHandler())
    assert not emit_alert("controlled", logger=logger)
