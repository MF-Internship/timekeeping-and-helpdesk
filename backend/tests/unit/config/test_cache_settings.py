from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).parents[3]


def runtime_environment(**overrides: str) -> dict[str, str]:
    environment_name = overrides.get("APP_ENV", "development")
    values = {
        "APP_ENV": environment_name,
        "DATABASE_URL": "postgresql://runtime:password@db.invalid/app",
        "DJANGO_SECRET_KEY": "safe-test-value",
        "DJANGO_DEBUG": "false",
        "API_DOCS_ENABLED": "true",
        "DJANGO_CACHE_BACKEND": "locmem" if environment_name == "development" else "database",
        "REDIS_URL": "rediss://user:password@redis.invalid/0",
        "REDIS_KEY_PREFIX": f"timekeeping-{environment_name}",
        "R2_BUCKET": f"timekeeping-{environment_name}",
        "ORIGIN_CREDENTIAL_HEADER": "X-Origin-Credential",
        "ORIGIN_CREDENTIAL": "x" * 32,
    }
    values.update(overrides)
    return values


def import_cache_settings(values: dict[str, str]) -> subprocess.CompletedProcess[str]:
    runtime_keys = set(runtime_environment()) | {"DJANGO_SETTINGS_MODULE"}
    environment = {key: value for key, value in os.environ.items() if key not in runtime_keys}
    environment.update(values)
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "import json; from config import settings; "
            "print(json.dumps(settings.CACHES, sort_keys=True))",
        ],
        cwd=BACKEND_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.unit
@pytest.mark.parametrize("environment_name", ["staging", "production"])
def test_shipped_non_development_cache_is_database(environment_name: str) -> None:
    result = import_cache_settings(runtime_environment(APP_ENV=environment_name))

    assert result.returncode == 0, result.stderr
    caches = json.loads(result.stdout)
    assert list(caches) == ["default"]
    assert caches["default"]["BACKEND"] == "django.core.cache.backends.db.DatabaseCache"
    assert caches["default"]["LOCATION"] == "throttle_cache"


@pytest.mark.unit
def test_development_defaults_to_locmem_when_choice_is_absent() -> None:
    values = runtime_environment()
    values.pop("DJANGO_CACHE_BACKEND")
    result = import_cache_settings(values)

    assert result.returncode == 0, result.stderr
    caches = json.loads(result.stdout)
    assert list(caches) == ["default"]
    assert caches["default"]["BACKEND"] == "django.core.cache.backends.locmem.LocMemCache"


@pytest.mark.unit
@pytest.mark.parametrize("choice", ["", "unknown"])
def test_empty_or_unknown_cache_choice_fails_closed(choice: str) -> None:
    result = import_cache_settings(runtime_environment(DJANGO_CACHE_BACKEND=choice))

    assert result.returncode != 0
    assert "DJANGO_CACHE_BACKEND" in result.stderr
    assert choice not in result.stderr or choice == ""


@pytest.mark.unit
def test_process_local_cache_is_rejected_outside_development_even_with_debug() -> None:
    result = import_cache_settings(
        runtime_environment(
            APP_ENV="production",
            DJANGO_CACHE_BACKEND="locmem",
            DJANGO_DEBUG="true",
        )
    )

    assert result.returncode != 0
    assert "DJANGO_CACHE_BACKEND" in result.stderr


@pytest.mark.unit
def test_redis_choice_fails_when_package_is_unavailable() -> None:
    result = import_cache_settings(
        runtime_environment(APP_ENV="staging", DJANGO_CACHE_BACKEND="redis")
    )

    assert result.returncode != 0
    assert "DJANGO_CACHE_BACKEND" in result.stderr
