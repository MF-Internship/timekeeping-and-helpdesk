from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import psycopg
import pytest

from core.cache import THROTTLE_CACHE_TABLE

BACKEND_ROOT = Path(__file__).parents[3]
LOCAL_DATABASE_URL = "postgresql://app_runtime:local_runtime_only@127.0.0.1:5432/timekeeping"


def postgres_test_database_url() -> str:
    return os.environ.get("POSTGRES_TEST_DATABASE_URL", LOCAL_DATABASE_URL)


def django_environment() -> dict[str, str]:
    values = dict(os.environ)
    values.update(
        {
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "APP_ENV": "development",
            "DATABASE_URL": postgres_test_database_url(),
            "DJANGO_SECRET_KEY": "safe-test-value",
            "DJANGO_DEBUG": "false",
            "API_DOCS_ENABLED": "true",
            "DJANGO_CACHE_BACKEND": "database",
            "REDIS_URL": "rediss://user:password@redis.invalid/0",
            "REDIS_KEY_PREFIX": "timekeeping-development",
            "R2_BUCKET": "timekeeping-development",
            "ORIGIN_CREDENTIAL_HEADER": "X-Origin-Credential",
            "ORIGIN_CREDENTIAL": "x" * 32,
        }
    )
    return values


def migrate(target: str) -> None:
    result = subprocess.run(
        [sys.executable, "manage.py", "migrate", "operations", target, "--noinput"],
        cwd=BACKEND_ROOT,
        env=django_environment(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def table_count() -> int:
    with psycopg.connect(postgres_test_database_url()) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s",
            (THROTTLE_CACHE_TABLE,),
        )
        row = cursor.fetchone()
    assert row is not None
    return int(row[0])


@pytest.mark.postgres
@pytest.mark.integration
def test_cache_migration_applies_reverses_and_reapplies_on_postgresql() -> None:
    migrate("zero")
    assert table_count() == 0

    migrate("0001")
    assert table_count() == 1

    migrate("zero")
    assert table_count() == 0

    migrate("0001")
    assert table_count() == 1
