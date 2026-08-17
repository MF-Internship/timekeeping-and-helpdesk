from __future__ import annotations

import ast
from pathlib import Path


def test_present_throttle_consumers_import_canonical_alias() -> None:
    backend_root = Path(__file__).parents[2]
    cache_source = backend_root / "core" / "cache.py"
    for path in backend_root.rglob("*.py"):
        if path == cache_source or "tests" in path.parts or "migrations" in path.parts:
            continue
        source = path.read_text(encoding="utf-8")
        if "THROTTLE_CACHE_ALIAS" not in source:
            continue
        tree = ast.parse(source)
        canonical_import = any(
            isinstance(node, ast.ImportFrom)
            and node.module == "core.cache"
            and any(alias.name == "THROTTLE_CACHE_ALIAS" for alias in node.names)
            for node in ast.walk(tree)
        )
        assert canonical_import, path
