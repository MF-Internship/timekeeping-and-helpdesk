from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from django.conf import settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from tests.integration.api.identity.helpers import (
    api_client,
    create_user,
    manager_client,
)


def _login_for_expiry(username: str) -> tuple[APIClient, str]:
    user_api = api_client()
    login = user_api.post(
        "/api/v1/auth/login",
        {"username": username, "password": "SafePassword123!"},
    )
    assert login.status_code == 200
    access = login.json()["access"]
    user_api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return user_api, access


def _apply_security_operation(operation: str, user_api: APIClient, user_id: int) -> None:
    if operation == "logout":
        assert user_api.post("/api/v1/auth/logout", {}).status_code == 204
        return
    if operation == "password_change":
        changed = user_api.post(
            "/api/v1/change-password",
            {"current_password": "SafePassword123!", "new_password": "ChangedPassword456!"},
        )
        assert changed.status_code == 200
        return
    manager_api, _manager = manager_client(f"expiry-manager-{operation}")
    if operation == "reset":
        assert manager_api.post(f"/api/v1/users/{user_id}/reset-password", {}).status_code == 200
        return
    response = manager_api.patch(f"/api/v1/users/{user_id}/status", {"is_active": False})
    assert response.status_code == 200


def _assert_access_expires_at_boundary(user_api: APIClient, access: str) -> None:
    token = AccessToken(access, verify=False)
    expiry = datetime.fromtimestamp(int(token["exp"]), tz=UTC)
    token.check_exp(current_time=expiry - timedelta(microseconds=1))
    with pytest.raises(TokenError):
        token.check_exp(current_time=expiry)
    with patch("rest_framework_simplejwt.tokens.aware_utcnow", return_value=expiry):
        expired_response = user_api.get("/api/v1/me/")
    assert expired_response.status_code == 401
    assert expired_response.json()["error_code"] == "INVALID_TOKEN"


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_access_token_accepts_before_and_rejects_at_fifteen_minute_expiry() -> None:
    account = create_user("expiry")
    api = api_client()
    response = api.post(
        "/api/v1/auth/login", {"username": "expiry", "password": "SafePassword123!"}
    )
    assert settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"] == timedelta(minutes=15)
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {response.json()['access']}")
    assert api.get("/api/v1/me/").status_code == 200
    token = AccessToken(response.json()["access"], verify=False)
    expiry = datetime.fromtimestamp(int(token["exp"]), tz=UTC)
    token.check_exp(current_time=expiry - timedelta(microseconds=1))
    with pytest.raises(TokenError):
        token.check_exp(current_time=expiry)
    expired = AccessToken.for_user(account)
    expired.set_exp(lifetime=timedelta(seconds=-1))
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {expired}")
    denied = api.get("/api/v1/me/")
    assert denied.status_code == 401
    assert denied.json()["error_code"] == "INVALID_TOKEN"


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
@pytest.mark.parametrize(
    ("operation", "pre_expiry_status", "pre_expiry_code"),
    [
        ("logout", 200, None),
        ("reset", 403, "PASSWORD_CHANGE_REQUIRED"),
        ("password_change", 200, None),
        ("deactivate", 401, "ACCOUNT_INACTIVE"),
    ],
)
def test_security_mutations_preserve_only_canonical_access_lifetime_and_account_gate(
    operation: str, pre_expiry_status: int, pre_expiry_code: str | None
) -> None:
    user = create_user(f"expiry-{operation}")
    user_api, access = _login_for_expiry(user.username)
    _apply_security_operation(operation, user_api, user.pk)

    user_api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    current = user_api.get("/api/v1/me/")
    assert current.status_code == pre_expiry_status
    if pre_expiry_code is not None:
        assert current.json()["error_code"] == pre_expiry_code

    _assert_access_expires_at_boundary(user_api, access)
