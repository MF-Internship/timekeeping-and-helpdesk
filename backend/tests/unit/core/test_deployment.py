from __future__ import annotations

import pytest

from core.deployment import (
    ConfigurationError,
    EnvironmentName,
    load_runtime_settings,
    validate_database_separation,
)

VAPID_PRIVATE_KEY = "_JwK_15j-P5tijB2GLjaUo9O78G63Quft2hADnTnj7U"
VAPID_PUBLIC_KEY = (
    "BHPBij6oiVlZ6ydT8A8cMACRw4bRGEDWu46WEWlK9XuOVJ_3YRv4Zui2SjMw0gRmKBdMbgakGwKtojux_sCKRSY"
)


def valid_environment(**overrides: str) -> dict[str, str]:
    environment = overrides.get("APP_ENV", "development")
    values = {
        "APP_ENV": environment,
        "DATABASE_URL": "postgresql://runtime:password@db.invalid/app",
        "DJANGO_SECRET_KEY": "safe-test-value",
        "DJANGO_DEBUG": "false",
        "API_DOCS_ENABLED": "true",
        "DJANGO_CACHE_BACKEND": "locmem",
        "REDIS_URL": "rediss://user:password@redis.invalid/0",
        "REDIS_KEY_PREFIX": f"timekeeping-{environment}",
        "R2_BUCKET": f"timekeeping-{environment}",
        "ORIGIN_CREDENTIAL_HEADER": "X-Origin-Credential",
        "ORIGIN_CREDENTIAL": "x" * 32,
        "WEB_PUSH_VAPID_PUBLIC_KEY": VAPID_PUBLIC_KEY,
        "WEB_PUSH_VAPID_PRIVATE_KEY": VAPID_PRIVATE_KEY,
        "WEB_PUSH_VAPID_SUBJECT": "mailto:test@example.invalid",
        "PUSH_SUBSCRIPTION_ENCRYPTION_KEY": "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
        "WEB_PUSH_ENABLED": "true" if environment != "development" else "false",
        "WEB_PUSH_ALLOWED_ORIGINS": "https://push.example.invalid",
    }
    values.update(overrides)
    return values


@pytest.mark.unit
def test_loads_typed_development_settings() -> None:
    settings = load_runtime_settings(valid_environment())

    assert settings.environment is EnvironmentName.DEVELOPMENT
    assert settings.debug is False
    assert settings.api_docs_enabled is True


@pytest.mark.unit
@pytest.mark.parametrize("name", ["dev", "prod", "qa", ""])
def test_rejects_unknown_or_empty_environment_name(name: str) -> None:
    with pytest.raises(ConfigurationError, match="APP_ENV"):
        load_runtime_settings(valid_environment(APP_ENV=name))


@pytest.mark.unit
@pytest.mark.parametrize("key", ["DATABASE_URL", "DJANGO_SECRET_KEY", "ORIGIN_CREDENTIAL"])
@pytest.mark.parametrize("value", ["", "UNRESOLVED"])
def test_rejects_empty_and_unresolved_runtime_values(key: str, value: str) -> None:
    with pytest.raises(ConfigurationError) as raised:
        load_runtime_settings(valid_environment(**{key: value}))

    assert key in str(raised.value)
    assert value not in str(raised.value) or value == ""


@pytest.mark.unit
def test_rejects_non_postgresql_database() -> None:
    with pytest.raises(ConfigurationError, match="DATABASE_URL"):
        load_runtime_settings(valid_environment(DATABASE_URL="sqlite:///local.db"))


@pytest.mark.unit
def test_database_collision_reports_keys_not_dsn() -> None:
    dsn = "postgresql://user:password@db.invalid/app"

    with pytest.raises(ConfigurationError) as raised:
        validate_database_separation(dsn, dsn)

    assert "DATABASE_URL" in str(raised.value)
    assert "DATABASE_ADMIN_URL" in str(raised.value)
    assert dsn not in str(raised.value)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("REDIS_URL", "redis://redis.invalid/0"),
        ("REDIS_URL", "rediss://redis.invalid/0"),
        ("REDIS_KEY_PREFIX", "shared-prefix"),
        ("R2_BUCKET", "shared-bucket"),
    ],
)
def test_non_development_requires_encrypted_qualified_resources(key: str, value: str) -> None:
    with pytest.raises(ConfigurationError, match=key):
        load_runtime_settings(valid_environment(APP_ENV="staging", **{key: value}))


@pytest.mark.unit
def test_rejects_forbidden_result_backend() -> None:
    values = valid_environment()
    values["REDIS_RESULT_BACKEND_URL"] = "rediss://user:password@redis.invalid/1"

    with pytest.raises(ConfigurationError, match="REDIS_RESULT_BACKEND_URL"):
        load_runtime_settings(values)


@pytest.mark.unit
def test_rejects_short_origin_credential_without_echoing_it() -> None:
    value = "too-short"
    with pytest.raises(ConfigurationError) as raised:
        load_runtime_settings(valid_environment(ORIGIN_CREDENTIAL=value))

    assert "ORIGIN_CREDENTIAL" in str(raised.value)
    assert value not in str(raised.value)


@pytest.mark.unit
@pytest.mark.parametrize(
    "key",
    [
        "WEB_PUSH_VAPID_PUBLIC_KEY",
        "WEB_PUSH_VAPID_PRIVATE_KEY",
        "WEB_PUSH_VAPID_SUBJECT",
        "PUSH_SUBSCRIPTION_ENCRYPTION_KEY",
        "WEB_PUSH_ALLOWED_ORIGINS",
    ],
)
def test_production_requires_web_push_secrets_without_echoing_them(key: str) -> None:
    values = valid_environment(APP_ENV="production")
    values.pop(key)

    with pytest.raises(ConfigurationError) as raised:
        load_runtime_settings(values)

    assert key in str(raised.value)


@pytest.mark.unit
def test_rejects_malformed_subscription_encryption_key() -> None:
    value = "not-a-valid-key"

    with pytest.raises(ConfigurationError) as raised:
        load_runtime_settings(
            valid_environment(
                WEB_PUSH_ENABLED="true",
                PUSH_SUBSCRIPTION_ENCRYPTION_KEY=value,
            )
        )

    assert "PUSH_SUBSCRIPTION_ENCRYPTION_KEY" in str(raised.value)
    assert value not in str(raised.value)


@pytest.mark.unit
@pytest.mark.parametrize(
    "origin",
    [
        "http://push.example.invalid",
        "https://user@push.example.invalid",
        "https://push.example.invalid/path",
    ],
)
def test_rejects_non_exact_https_push_origin(origin: str) -> None:
    with pytest.raises(ConfigurationError, match="WEB_PUSH_ALLOWED_ORIGINS"):
        load_runtime_settings(
            valid_environment(WEB_PUSH_ENABLED="true", WEB_PUSH_ALLOWED_ORIGINS=origin)
        )


@pytest.mark.unit
def test_disabled_web_push_ignores_placeholder_provider_configuration() -> None:
    settings = load_runtime_settings(
        valid_environment(
            WEB_PUSH_ENABLED="false",
            WEB_PUSH_VAPID_PUBLIC_KEY="placeholder",
            WEB_PUSH_VAPID_PRIVATE_KEY="placeholder",
            PUSH_SUBSCRIPTION_ENCRYPTION_KEY="placeholder",
            WEB_PUSH_ALLOWED_ORIGINS="placeholder",
        )
    )

    assert settings.web_push_enabled is False
    assert settings.push_subscription_encryption_keys == ()


@pytest.mark.unit
def test_non_development_can_run_authoritative_inbox_with_push_disabled() -> None:
    values = valid_environment(APP_ENV="production", WEB_PUSH_ENABLED="false")
    for key in (
        "WEB_PUSH_VAPID_PUBLIC_KEY",
        "WEB_PUSH_VAPID_PRIVATE_KEY",
        "WEB_PUSH_VAPID_SUBJECT",
        "PUSH_SUBSCRIPTION_ENCRYPTION_KEY",
        "WEB_PUSH_ALLOWED_ORIGINS",
    ):
        values.pop(key)

    settings = load_runtime_settings(values)

    assert settings.web_push_enabled is False
    assert settings.push_subscription_encryption_keys == ()


@pytest.mark.unit
def test_enabled_web_push_rejects_mismatched_vapid_pair_without_echoing() -> None:
    mismatched_public_key = VAPID_PUBLIC_KEY[:-1] + "A"

    with pytest.raises(ConfigurationError) as raised:
        load_runtime_settings(
            valid_environment(
                WEB_PUSH_ENABLED="true",
                WEB_PUSH_VAPID_PUBLIC_KEY=mismatched_public_key,
            )
        )

    assert "WEB_PUSH_VAPID_PUBLIC_KEY" in str(raised.value)
    assert mismatched_public_key not in str(raised.value)


@pytest.mark.unit
def test_subscription_key_ring_preserves_primary_first() -> None:
    first = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
    second = "MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE="

    settings = load_runtime_settings(
        valid_environment(
            WEB_PUSH_ENABLED="true",
            PUSH_SUBSCRIPTION_ENCRYPTION_KEY=f"{first},{second}",
        )
    )

    assert settings.push_subscription_encryption_keys == (first, second)
