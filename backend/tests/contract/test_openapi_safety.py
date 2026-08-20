from __future__ import annotations

from pathlib import Path

import pytest
import yaml

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


def test_generated_attendance_coordinate_fields_are_named_but_never_exemplified() -> None:
    from scripts.generate_openapi import generate_openapi_bytes

    rendered = generate_openapi_bytes().decode()
    assert "captured_latitude:" in rendered and "captured_longitude:" in rendered
    assert "latitude:" in rendered and "longitude:" in rendered
    assert "10.000000" not in rendered and "106.000000" not in rendered


def test_job_health_has_no_forbidden_detail_or_mutation_surface() -> None:
    from scripts.generate_openapi import generate_openapi_bytes

    document = yaml.safe_load(generate_openapi_bytes())
    path = document["paths"]["/api/v1/operations/job-health"]
    assert set(path) == {"get"}
    rendered = str(path).lower()
    for forbidden in ("user_id", "session_id", "gps", "latitude", "longitude", "closed_count"):
        assert forbidden not in rendered


@pytest.mark.parametrize(
    ("schema_name", "field_name"),
    [
        ("NotificationItem", "full_name"),
        ("NotificationItem", "gps"),
        ("PushSubscriptionResult", "endpoint"),
        ("PushSubscriptionResult", "encrypted_subscription"),
        ("Target", "url"),
    ],
)
def test_notification_contracts_reject_sensitive_response_fields(
    schema_name: str, field_name: str
) -> None:
    from scripts.check_openapi import OpenAPISafetyError, check_openapi_text

    document = {
        "openapi": "3.0.3",
        "components": {"schemas": {schema_name: {"properties": {field_name: {"type": "string"}}}}},
    }

    with pytest.raises(OpenAPISafetyError, match="OPENAPI-SAFETY"):
        check_openapi_text(yaml.safe_dump(document), "notification-privacy")
