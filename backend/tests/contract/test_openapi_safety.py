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


def test_canonical_credential_schema_properties_are_narrow_exceptions() -> None:
    from scripts.check_openapi import OpenAPISafetyError, check_openapi_text

    prefix = """openapi: 3.0.3
components:
  schemas:
"""
    for schema, field in (
        ("Login", "password"),
        ("GeneratedUserResult", "generated_password"),
        ("ResetPasswordResult", "generated_password"),
    ):
        check_openapi_text(
            prefix
            + f"""    {schema}:
      type: object
      properties:
        {field}: {{type: string}}
""",
            "credential.yaml",
        )

    with pytest.raises(OpenAPISafetyError):
        check_openapi_text(
            prefix
            + """    UnapprovedResult:
      type: object
      properties:
        generated_password: {type: string}
""",
            "unapproved.yaml",
        )


def test_login_password_exception_does_not_allow_nested_password_keys() -> None:
    from scripts.check_openapi import OpenAPISafetyError, check_openapi_text

    with pytest.raises(OpenAPISafetyError):
        check_openapi_text(
            """openapi: 3.0.3
components:
  schemas:
    Login:
      type: object
      properties:
        nested:
          type: object
          properties:
            password: {type: string}
""",
            "nested.yaml",
        )
