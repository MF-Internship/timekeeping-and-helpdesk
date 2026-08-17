from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).parents[3]
LOCAL_DATABASE_URL = "postgresql://app_runtime:local_runtime_only@127.0.0.1:5432/timekeeping"


def postgres_test_database_url() -> str:
    return os.environ.get("POSTGRES_TEST_DATABASE_URL", LOCAL_DATABASE_URL)


def runtime_environment() -> dict[str, str]:
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


@pytest.mark.postgres
@pytest.mark.integration
def test_django_uses_postgresql_and_rolls_back_real_transaction() -> None:
    code = """
import django
django.setup()
from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor
assert connection.vendor == 'postgresql'
with connection.cursor() as cursor:
    cursor.execute('CREATE TABLE IF NOT EXISTS foundation_rollback_probe (value integer)')
    cursor.execute('TRUNCATE foundation_rollback_probe')
try:
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute('INSERT INTO foundation_rollback_probe (value) VALUES (1)')
        raise RuntimeError('rollback')
except RuntimeError:
    pass
with connection.cursor() as cursor:
    cursor.execute('SELECT count(*) FROM foundation_rollback_probe')
    assert cursor.fetchone()[0] == 0
MigrationExecutor(connection)
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND_ROOT,
        env=runtime_environment(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
