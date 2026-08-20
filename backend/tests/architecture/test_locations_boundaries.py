from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2] / "locations"


@pytest.mark.architecture
def test_locations_domain_is_framework_free() -> None:
    forbidden = {"django", "rest_framework"}
    for path in (ROOT / "domain").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {
            node.names[0].name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
        } | {
            (node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        assert not imports & forbidden, path


@pytest.mark.architecture
def test_locations_application_uses_identity_and_audit_public_ports_only() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in (ROOT / "application").glob("*.py")
    )
    assert "identity.models" not in source
    assert "audit.models" not in source
    assert "identity.adapters" not in source
    assert "audit.adapters" not in source
