from __future__ import annotations

import logging

import pytest


class CollectingHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


class FailingHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        raise RuntimeError("sink unavailable")


def test_filter_enriches_bound_and_empty_correlation() -> None:
    from core.correlation import bind_correlation, reset_correlation
    from core.logging import CorrelationFilter

    filter_ = CorrelationFilter()
    empty = logging.LogRecord("test", logging.INFO, __file__, 1, "empty", (), None)
    assert filter_.filter(empty)
    assert (empty.request_id, empty.correlation_id) == ("", "")
    token = bind_correlation("00000000-0000-4000-8000-000000000001")
    try:
        bound = logging.LogRecord("test", logging.INFO, __file__, 1, "bound", (), None)
        assert filter_.filter(bound)
        assert bound.request_id == bound.correlation_id
        assert bound.request_id.endswith("1")
    finally:
        reset_correlation(token)


def test_safe_failure_emission_sanitizes_external_text_and_uses_safe_record_keys() -> None:
    from core.logging import emit_safe_failure

    logger = logging.Logger("safe-test")
    handler = CollectingHandler()
    logger.addHandler(handler)
    emitted = emit_safe_failure(
        logger,
        "password=hunter2 https://user:secret@example.invalid 10.123456,106.123456",
        rule="CONTROLLED-RULE",
        path="artifact/path",
    )
    assert emitted
    record = handler.records[0]
    rendered = record.getMessage()
    assert "hunter2" not in rendered
    assert "example.invalid" not in rendered
    assert "10.123456" not in rendered
    assert record.rule_id == "CONTROLLED-RULE"
    assert record.artifact_path == "artifact/path"
    assert record.failed is True


def test_sink_failure_is_contained() -> None:
    from core.logging import emit_safe_failure

    logger = logging.Logger("failing-test")
    logger.addHandler(FailingHandler())
    assert not emit_safe_failure(logger, "controlled", rule="RULE", path="path")


def test_django_logging_configuration_names_required_components(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = {
        "DJANGO_DEBUG": "false",
        "API_DOCS_ENABLED": "true",
        "REDIS_URL": "redis://localhost/0",
        "REDIS_KEY_PREFIX": "timekeeping-development",
        "R2_BUCKET": "timekeeping-development",
        "ORIGIN_CREDENTIAL_HEADER": "X-Origin-Credential",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    from config import settings

    configuration = settings.LOGGING
    assert "correlation" in configuration["filters"]
    assert "correlated" in configuration["formatters"]
    assert "console" in configuration["handlers"]
    assert configuration["handlers"]["console"]["filters"] == ["correlation"]
