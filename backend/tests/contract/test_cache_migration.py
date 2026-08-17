from __future__ import annotations

import ast
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).parents[2]


@pytest.mark.contract
def test_cache_table_provisioning_has_one_operations_leaf() -> None:
    migrations = sorted((BACKEND_ROOT / "operations" / "migrations").glob("[0-9]*.py"))
    assert [path.name for path in migrations] == ["0001_throttle_cache_table.py"]


@pytest.mark.contract
def test_cache_migration_uses_approved_mechanism_and_canonical_table() -> None:
    path = BACKEND_ROOT / "operations" / "migrations" / "0001_throttle_cache_table.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    canonical_import = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "core.cache"
        and any(alias.name == "THROTTLE_CACHE_TABLE" for alias in node.names)
        for node in ast.walk(tree)
    )
    assert canonical_import
    assert "call_command" in source
    assert "createcachetable" in source
    assert '"throttle_cache"' not in source


@pytest.mark.contract
def test_settings_and_migration_share_table_identity() -> None:
    settings_source = (BACKEND_ROOT / "config" / "settings.py").read_text(encoding="utf-8")
    migration_source = (
        BACKEND_ROOT / "operations" / "migrations" / "0001_throttle_cache_table.py"
    ).read_text(encoding="utf-8")
    assert "THROTTLE_CACHE_TABLE" in settings_source
    assert "THROTTLE_CACHE_TABLE" in migration_source


@pytest.mark.architecture
def test_config_has_no_migration_or_app_registration() -> None:
    assert not (BACKEND_ROOT / "config" / "migrations").exists()
    assert not (BACKEND_ROOT / "config" / "apps.py").exists()
