from __future__ import annotations

import logging
import subprocess
import sys

import pytest

PROTECTED_VALUES = (
    "https://user:secret@example.invalid/object",
    "token=token-secret",
    "password=hunter2",
    "cookie=session-secret",
    "object_key=private-object",
    "image_data=encoded-image",
    "10.123456,106.123456",
)
PROTECTED = " ".join(PROTECTED_VALUES)


class MessageHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def test_log_consumer_removes_protected_external_values() -> None:
    from core.logging import emit_safe_failure

    logger = logging.Logger("sanitized-output")
    handler = MessageHandler()
    logger.addHandler(handler)
    assert emit_safe_failure(logger, PROTECTED, rule="RULE", path="artifact")
    output = " ".join(handler.messages)
    assert_protected_values_absent(output)


def assert_protected_values_absent(output: str) -> None:
    for value in (
        "example.invalid",
        "token-secret",
        "hunter2",
        "session-secret",
        "private-object",
        "encoded-image",
        "10.123456",
    ):
        assert value not in output


def test_error_consumer_rejects_protected_detail_without_echo() -> None:
    from core.errors import build_error_envelope

    with pytest.raises(ValueError) as captured:
        build_error_envelope(
            "VALIDATION_FAILED",
            "00000000-0000-4000-8000-000000000000",
            {"field": [PROTECTED]},
        )
    assert_protected_values_absent(str(captured.value))


def test_recovery_consumer_sanitizes_probe_failure() -> None:
    from core.recovery import REQUIRED_CATEGORIES, RecoveryInputs, verify_restore

    class Connection:
        def execute(self, query: str) -> object:
            if "audit_rows" in query:
                raise RuntimeError(PROTECTED)
            return True

        def close(self) -> None:
            return None

    inputs = RecoveryInputs(
        "postgresql://runtime:secret@runtime/app",
        "postgresql://admin:secret@admin/app",
        "postgresql://restore:secret@restore/app",
    )
    result = verify_restore(inputs, lambda _dsn: Connection())
    assert set(REQUIRED_CATEGORIES)
    assert_protected_values_absent(" ".join(result.failures))


def test_deployment_consumer_does_not_echo_protected_inventory_values() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/deployment_check.py",
            "isolation",
            "--inventory",
            "backend/tests/contract/fixtures/deployment/protected.yaml",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert_protected_values_absent(result.stdout + result.stderr)


def test_capacity_result_and_alert_metric_adapters_do_not_expose_input() -> None:
    from scripts.capacity_check import CapacityIdentity, CapacityInputs, measure_capacity

    from operations.adapters.recovery_alerts import (
        RecoveryHealthSinks,
        emit_health_state,
        request_alert,
    )

    class Resource:
        def measure(self, _identity: str) -> float:
            raise RuntimeError(PROTECTED)

        def close(self) -> None:
            return None

    identities = tuple(
        CapacityIdentity(f"employee-{index:03d}", f"credential-{index:03d}") for index in range(50)
    )
    result = measure_capacity(CapacityInputs(identities, 20, "ops"), Resource)
    assert_protected_values_absent(repr(result))
    handler = MessageHandler()
    logger = logging.Logger("aggregate-sanitizer")
    logger.addHandler(handler)
    telemetry: list[str] = []
    sinks = RecoveryHealthSinks(logger, telemetry.append)
    assert request_alert(sinks, PROTECTED)
    assert emit_health_state(sinks, "alert")
    assert_protected_values_absent(" ".join(handler.messages + telemetry))
