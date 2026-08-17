from __future__ import annotations

from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).parents[2]
BUSINESS_NAMES = {
    "auth",
    "identity",
    "locations",
    "attendance",
    "tasks",
    "reporting",
    "notifications",
}


@pytest.mark.architecture
def test_no_out_of_scope_runtime_package_exists() -> None:
    packages = {path.name for path in BACKEND_ROOT.iterdir() if path.is_dir()}
    assert not packages & BUSINESS_NAMES


@pytest.mark.architecture
def test_runtime_source_has_no_business_models_or_routes() -> None:
    runtime_paths = [BACKEND_ROOT / "config", BACKEND_ROOT / "core", BACKEND_ROOT / "operations"]
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for root in runtime_paths
        for path in root.rglob("*.py")
        if "migrations" not in path.parts
    )
    forbidden = ("AuditLog", "OutboxEvent", "AbstractUser", "login/", "attendance/", "tasks/")
    assert not [name for name in forbidden if name in source]
