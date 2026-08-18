import pytest

EXPECTED_OPERATIONS = {
    "/api/v1/auth/login": {"post": "auth_login_create"},
    "/api/v1/auth/refresh": {"post": "auth_refresh_create"},
    "/api/v1/auth/logout": {"post": "auth_logout_create"},
    "/api/v1/me/": {
        "get": "identity_me_retrieve",
        "patch": "identity_me_partial_update",
    },
    "/api/v1/change-password": {"post": "identity_change_password_create"},
    "/api/v1/users/": {"get": "users_list", "post": "users_create"},
    "/api/v1/users/{user_id}/": {
        "get": "users_retrieve",
        "patch": "users_partial_update",
    },
    "/api/v1/users/{user_id}/role": {"patch": "users_role_partial_update"},
    "/api/v1/users/{user_id}/status": {"patch": "users_status_partial_update"},
    "/api/v1/users/{user_id}/reset-password": {"post": "users_reset_password_create"},
}


@pytest.mark.contract
def test_identity_paths_operations_security_and_open_strings() -> None:
    from scripts.generate_openapi import schema_document

    document = schema_document()
    for path, methods in EXPECTED_OPERATIONS.items():
        assert path in document["paths"]
        for method, operation_id in methods.items():
            operation = document["paths"][path][method]
            assert operation["operationId"] == operation_id
            if path not in {"/api/v1/auth/login", "/api/v1/auth/refresh"}:
                assert operation["security"] == [{"bearerAuth": []}]
    schemas = document["components"]["schemas"]
    assert "enum" not in schemas["AdminUser"]["properties"]["role"]
    assert "enum" not in schemas["SelfUser"]["properties"]["role"]
    assert "enum" not in schemas["SelfUser"]["properties"]["capabilities"]["items"]


@pytest.mark.contract
def test_credentials_are_confined_to_approved_schema_locations() -> None:
    from scripts.generate_openapi import schema_document

    document = schema_document()
    schemas = document["components"]["schemas"]
    password_paths = [
        name for name, schema in schemas.items() if "password" in schema.get("properties", {})
    ]
    assert password_paths == ["Login"]
    assert "refresh_token" not in str(document)
    generated_paths = [
        name
        for name, schema in schemas.items()
        if "generated_password" in schema.get("properties", {})
    ]
    assert sorted(generated_paths) == ["GeneratedUserResult", "ResetPasswordResult"]


@pytest.mark.contract
def test_logout_clear_cookie_matches_issued_cookie_security_attributes() -> None:
    from rest_framework.response import Response

    from identity.adapters.api.views import _clear_refresh, _set_refresh

    issued = Response()
    cleared = Response()
    _set_refresh(issued, "opaque")
    _clear_refresh(cleared)

    issued_cookie = issued.cookies["refresh_token"]
    cleared_cookie = cleared.cookies["refresh_token"]
    for attribute in ("path", "secure", "httponly", "samesite"):
        assert cleared_cookie[attribute] == issued_cookie[attribute]
    assert cleared_cookie.value == ""
    assert cleared_cookie["max-age"] == 0
