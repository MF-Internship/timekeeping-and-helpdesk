from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parents[1] / "migration_fixtures"


@pytest.mark.parametrize("name", ["safe", "merge", "nullable", "default", "contraction_tagged"])
def test_safe_migration_graphs_pass(name: str) -> None:
    from scripts.migration_check import check_tree

    assert check_tree(FIXTURES / name) == []


@pytest.mark.parametrize(
    ("name", "rule"),
    [
        ("duplicate", "MIGRATION-LEAF"),
        ("required", "MIGRATION-DB-DEFAULT"),
        ("contraction", "MIGRATION-RELEASE-PHASE"),
        ("mixed", "MIGRATION-MIXED-PHASE"),
        ("owner", "MIGRATION-OWNER"),
        ("cache_drift", "MIGRATION-CACHE-IDENTITY"),
    ],
)
def test_unsafe_migration_graph_has_expected_rule(name: str, rule: str) -> None:
    from scripts.migration_check import check_tree

    findings = check_tree(FIXTURES / name)
    assert rule in {finding.rule for finding in findings}


def test_checker_is_ast_only() -> None:
    source = Path("scripts/migration_check.py").read_text(encoding="utf-8")
    assert "import django" not in source
    assert "django.setup" not in source
    assert "connection" not in source


def test_locations_migration_is_safe_and_has_one_leaf() -> None:
    from scripts.migration_check import check_tree

    assert check_tree(Path("backend/locations")) == []
