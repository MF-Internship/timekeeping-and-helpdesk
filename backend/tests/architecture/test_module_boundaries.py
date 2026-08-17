from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[3]
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
