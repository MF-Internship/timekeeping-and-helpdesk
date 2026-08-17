from __future__ import annotations

from typing import Final

THROTTLE_CACHE_ALIAS: Final = "default"
THROTTLE_CACHE_TABLE: Final = "throttle_cache"
CACHE_BACKEND_CHOICES: Final = ("locmem", "database", "redis")

_PROCESS_LOCAL_BACKENDS: Final = frozenset(
    {
        "django.core.cache.backends.locmem.LocMemCache",
        "django.core.cache.backends.dummy.DummyCache",
        "django.core.cache.backends.filebased.FileBasedCache",
    }
)
_BACKEND_PATHS: Final = {
    "locmem": "django.core.cache.backends.locmem.LocMemCache",
    "database": "django.core.cache.backends.db.DatabaseCache",
    "redis": "django.core.cache.backends.redis.RedisCache",
}


def is_process_local_backend(backend_path: str) -> bool:
    return backend_path in _PROCESS_LOCAL_BACKENDS


def cache_backend_path(choice: str) -> str:
    return _BACKEND_PATHS[choice]
