from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[3]
BACKEND = ROOT / "backend"
FIXTURES = Path(__file__).parent / "fixtures" / "module_boundaries"
CHECKER = ROOT / "scripts" / "check_architecture.py"


def run_checker(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.architecture
def test_safe_domain_fixture_passes() -> None:
    result = run_checker(FIXTURES / "safe")
    assert result.returncode == 0, result.stderr


@pytest.mark.architecture
def test_same_owner_internal_import_is_not_a_cross_module_violation(tmp_path: Path) -> None:
    owner = tmp_path / "identity" / "application"
    owner.mkdir(parents=True)
    source = owner / "service.py"
    source.write_text("from identity.domain.accounts import AccountSnapshot\n", encoding="utf-8")

    result = run_checker(source)

    assert result.returncode == 0, result.stderr


@pytest.mark.architecture
def test_different_owner_internal_import_is_rejected(tmp_path: Path) -> None:
    owner = tmp_path / "identity" / "application"
    owner.mkdir(parents=True)
    source = owner / "service.py"
    source.write_text("from audit.domain.records import AuditEntry\n", encoding="utf-8")

    result = run_checker(source)

    assert result.returncode != 0
    assert "ARCH-CROSS-MODULE" in result.stderr


@pytest.mark.architecture
@pytest.mark.parametrize(
    ("fixture_name", "rule_id"),
    [
        ("domain_framework.py", "ARCH-DOMAIN-FRAMEWORK"),
        ("inward_violation.py", "ARCH-INWARD"),
        ("cross_module_internal.py", "ARCH-CROSS-MODULE"),
        ("oversized_core.py", "ARCH-CORE-OWNERSHIP"),
    ],
)
def test_unsafe_fixture_fails_with_rule_and_path(fixture_name: str, rule_id: str) -> None:
    result = run_checker(FIXTURES / fixture_name)

    assert result.returncode != 0
    assert rule_id in result.stderr
    assert fixture_name in result.stderr


@pytest.mark.architecture
def test_production_backend_obeys_module_boundaries() -> None:
    for module in ("identity", "audit", "config"):
        result = run_checker(BACKEND / module)
        assert result.returncode == 0, result.stderr
