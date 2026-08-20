from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from audit.domain.relay import RelayConfig, retry_after, safe_transport_error


def test_retry_backoff_is_capped() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    config = RelayConfig(backoff_base_seconds=10, backoff_max_seconds=25)
    assert retry_after(now, 1, config) == now + timedelta(seconds=10)
    assert retry_after(now, 2, config) == now + timedelta(seconds=20)
    assert retry_after(now, 3, config) == now + timedelta(seconds=25)
    assert retry_after(now, 8, config) == now + timedelta(seconds=25)


@pytest.mark.parametrize(
    "key",
    ["batch_size", "lease_seconds", "max_attempts", "backoff_base_seconds", "backoff_max_seconds"],
)
def test_relay_config_rejects_zero_values(key: str) -> None:
    values = {
        "batch_size": 1,
        "lease_seconds": 1,
        "max_attempts": 1,
        "backoff_base_seconds": 1,
        "backoff_max_seconds": 1,
    }
    values[key] = 0
    with pytest.raises(ValueError):
        RelayConfig(**values)


def test_transport_error_sanitization_removes_protected_values() -> None:
    reason = "failed https://signed.example/path?token=secret at 10.785850,106.700000"
    sanitized = safe_transport_error(reason)
    assert "https://" not in sanitized
    assert "token=" not in sanitized
    assert "10.785850" not in sanitized
    assert sanitized
