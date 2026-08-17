from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[3]
FIXTURES = Path(__file__).parent / "fixtures" / "deployment"
SCRIPT = ROOT / "scripts" / "deployment_check.py"


def run_isolation(fixture_name: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "backend")
    return subprocess.run(
        [sys.executable, str(SCRIPT), "isolation", "--inventory", str(FIXTURES / fixture_name)],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.contract
def test_valid_cache_inventory_passes() -> None:
    result = run_isolation("cache-valid.yaml")

    assert result.returncode == 0, result.stderr


@pytest.mark.contract
@pytest.mark.parametrize(
    "fixture_name",
    ["cache-missing.yaml", "cache-unknown.yaml", "cache-process-local.yaml"],
)
def test_unsafe_cache_inventory_fails_by_path(fixture_name: str) -> None:
    result = run_isolation(fixture_name)

    assert result.returncode != 0
    assert "environments." in result.stderr
    assert "password" not in result.stderr.casefold()


@pytest.mark.architecture
def test_deployment_check_imports_canonical_cache_vocabulary() -> None:
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "core.cache"
        for alias in node.names
    }
    assert {"CACHE_BACKEND_CHOICES", "is_process_local_backend"} <= imported_names
