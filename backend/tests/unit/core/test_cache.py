from __future__ import annotations

import ast
from pathlib import Path

from core.cache import (
    CACHE_BACKEND_CHOICES,
    THROTTLE_CACHE_ALIAS,
    THROTTLE_CACHE_TABLE,
    is_process_local_backend,
)


def test_cache_constants_are_closed_and_stable() -> None:
    assert THROTTLE_CACHE_ALIAS == "default"
    assert THROTTLE_CACHE_TABLE == "throttle_cache"
    assert CACHE_BACKEND_CHOICES == ("locmem", "database", "redis")


def test_process_local_classification_is_canonical() -> None:
    assert is_process_local_backend("django.core.cache.backends.locmem.LocMemCache")
    assert is_process_local_backend("django.core.cache.backends.dummy.DummyCache")
    assert is_process_local_backend("django.core.cache.backends.filebased.FileBasedCache")
    assert not is_process_local_backend("django.core.cache.backends.db.DatabaseCache")
    assert not is_process_local_backend("django.core.cache.backends.redis.RedisCache")


def test_core_cache_imports_no_django() -> None:
    source = (Path(__file__).parents[3] / "core" / "cache.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert all(not name.startswith("django") for name in imported)
