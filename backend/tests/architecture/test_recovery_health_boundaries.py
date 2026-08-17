import ast
from pathlib import Path


def test_recovery_health_core_has_no_outward_operational_import() -> None:
    path = Path("backend/core/recovery_health.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in node.names
    }
    forbidden = ("django", "operations", "logging", "alerts", "telemetry")
    assert not any(name.startswith(forbidden) for name in imports)
