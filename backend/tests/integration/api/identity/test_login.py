import pytest

from tests.integration.api.identity.helpers import api_client, create_user


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_login_success_cookie_and_non_enumerating_denials() -> None:
    create_user("active")
    create_user("inactive", active=False)
    api = api_client()
    success = api.post("/api/v1/auth/login", {"username": "active", "password": "SafePassword123!"})
    assert success.status_code == 200
    assert "refresh" not in success.json()
    assert success.cookies["refresh_token"]["httponly"] is True
    denied = [
        api.post("/api/v1/auth/login", {"username": "missing", "password": "wrong"}),
        api.post("/api/v1/auth/login", {"username": "active", "password": "wrong"}),
        api.post(
            "/api/v1/auth/login",
            {"username": "inactive", "password": "SafePassword123!"},
        ),
    ]
    assert {(item.status_code, item.json()["error_code"]) for item in denied} == {
        (401, "INVALID_CREDENTIALS")
    }
    assert len({item.json()["message"] for item in denied}) == 1
