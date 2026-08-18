from __future__ import annotations

import ast
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).parents[2]
APPROVED_LOCAL_APPS = frozenset({"operations", "identity", "audit", "locations"})


@pytest.mark.architecture
def test_config_and_core_are_not_django_apps() -> None:
    forbidden = (
        BACKEND_ROOT / "config" / "apps.py",
        BACKEND_ROOT / "config" / "management",
        BACKEND_ROOT / "config" / "migrations",
        BACKEND_ROOT / "config" / "models.py",
        BACKEND_ROOT / "core" / "apps.py",
        BACKEND_ROOT / "core" / "migrations",
        BACKEND_ROOT / "core" / "models.py",
    )
    assert not [path for path in forbidden if path.exists()]


@pytest.mark.architecture
def test_only_approved_local_apps_are_registered() -> None:
    settings_path = BACKEND_ROOT / "config" / "settings.py"
    assert settings_path.exists(), "config/settings.py"
    tree = ast.parse(settings_path.read_text(encoding="utf-8"))
    installed_apps = _assigned_string_list(tree, "INSTALLED_APPS")
    local_apps = {name.split(".", maxsplit=1)[0] for name in installed_apps} & _local_packages()
    assert local_apps == APPROVED_LOCAL_APPS
    assert "config" not in installed_apps
    assert "core" not in installed_apps


@pytest.mark.architecture
def test_no_unapproved_local_persistence_owner_exists() -> None:
    persistence_owners = {
        path.parent.name for path in BACKEND_ROOT.glob("*/migrations") if path.is_dir()
    }
    assert persistence_owners <= APPROVED_LOCAL_APPS


def _assigned_string_list(tree: ast.AST, variable_name: str) -> list[str]:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        owns_assignment = any(
            isinstance(target, ast.Name) and target.id == variable_name for target in node.targets
        )
        if not owns_assignment:
            continue
        if isinstance(node.value, ast.List | ast.Tuple):
            return [
                element.value
                for element in node.value.elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            ]
    return []


def _local_packages() -> set[str]:
    return {
        path.name
        for path in BACKEND_ROOT.iterdir()
        if path.is_dir() and (path / "__init__.py").exists()
    }
