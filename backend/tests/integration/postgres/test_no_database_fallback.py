from __future__ import annotations

import subprocess
import sys

import pytest

from tests.integration.postgres.test_database_foundation import (
    BACKEND_ROOT,
    runtime_environment,
)


@pytest.mark.integration
def test_sqlite_configuration_is_rejected() -> None:
    environment = runtime_environment()
    environment["DATABASE_URL"] = "sqlite:///fallback.db"
    result = subprocess.run(
        [sys.executable, "-c", "import config.settings"],
        cwd=BACKEND_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "DATABASE_URL" in result.stderr
    assert "sqlite" not in result.stderr.casefold()


@pytest.mark.integration
def test_unavailable_postgresql_does_not_fallback() -> None:
    environment = runtime_environment()
    environment["DATABASE_URL"] = "postgresql://runtime:password@127.0.0.1:1/unavailable"
    code = (
        "import django; django.setup(); "
        "from django.db import connection; connection.ensure_connection()"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "sqlite" not in result.stderr.casefold()
