from __future__ import annotations

import ast
from pathlib import Path

import pytest

BACKEND = Path(__file__).parents[2]
ALLOWED_ROLE_OWNER = BACKEND / "identity" / "domain" / "authorization.py"


@pytest.mark.architecture
def test_job_health_role_interpretation_stays_in_identity_authorization() -> None:
    offenders: list[str] = []
    for root_name in ("operations", "config"):
        for path in (BACKEND / root_name).rglob("*.py"):
            if _uses_role(path):
                offenders.append(str(path.relative_to(BACKEND)))
    assert offenders == []


def _uses_role(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "Role":
            return True
        if isinstance(node, ast.Attribute) and node.attr in {"MANAGER", "LEADER", "HELPDESK"}:
            return True
    return False
