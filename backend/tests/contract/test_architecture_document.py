from __future__ import annotations

from pathlib import Path

import pytest

DOCUMENT = Path(__file__).parents[3] / "docs" / "ARCHITECTURE.md"


@pytest.mark.contract
def test_architecture_document_contains_each_foundation_rule_once() -> None:
    text = DOCUMENT.read_text(encoding="utf-8")
    required_once = (
        "sole Django composition root",
        "narrow pure technical kernel",
        "only approved local operational Django application",
        "Dependencies point inward",
        "closed cross-module exemptions",
        "sole technical table",
    )
    for rule in required_once:
        assert text.count(rule) == 1, rule
