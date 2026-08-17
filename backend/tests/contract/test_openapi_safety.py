from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures/openapi"


@pytest.mark.parametrize("fixture", sorted(FIXTURES.glob("*.yaml")))
def test_protected_schema_fixture_fails_with_path_only(fixture: Path) -> None:
    from scripts.check_openapi import OpenAPISafetyError, check_openapi_text

    protected = fixture.read_text(encoding="utf-8")
    with pytest.raises(OpenAPISafetyError) as captured:
        check_openapi_text(protected, fixture.name)
    diagnostic = str(captured.value)
    assert fixture.name in diagnostic
    for value in ("do-not-print-this", "user:password", "10.785850", "private/image.png"):
        assert value not in diagnostic
