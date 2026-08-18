from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


def pytest_configure() -> None:
    os.environ.setdefault("APP_ENV", "development")
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql://app_runtime:local_runtime_only@127.0.0.1:5432/timekeeping",
    )
    os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key")
    os.environ.setdefault("DJANGO_CACHE_BACKEND", "locmem")
    os.environ.setdefault("ORIGIN_CREDENTIAL", "test-origin-credential-at-least-32-chars")


@pytest.fixture(autouse=True)
def clear_shared_throttle_cache() -> None:
    from django.core.cache import caches

    from core.cache import THROTTLE_CACHE_ALIAS

    caches[THROTTLE_CACHE_ALIAS].clear()
