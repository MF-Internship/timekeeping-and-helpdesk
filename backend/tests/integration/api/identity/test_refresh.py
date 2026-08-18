import pytest

from tests.integration.api.identity.helpers import api_client, create_user


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_refresh_rotates_once_and_never_accepts_json_credentials() -> None:
    create_user("rotate")
    api = api_client()
    api.post("/api/v1/auth/login", {"username": "rotate", "password": "SafePassword123!"})
    old_refresh = api.cookies["refresh_token"].value
    rotated = api.post("/api/v1/auth/refresh", {})
    assert rotated.status_code == 200
    assert api.cookies["refresh_token"].value != old_refresh
    reused = api_client()
    reused.cookies["refresh_token"] = old_refresh
    assert reused.post("/api/v1/auth/refresh", {}).json()["error_code"] == "INVALID_TOKEN"
    injected = api.post("/api/v1/auth/refresh", {"refresh_token": old_refresh})
    assert injected.status_code == 400
    assert injected.json()["error_code"] == "SERVER_OWNED_FIELD"


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
@pytest.mark.parametrize("raw", [None, "malformed"])
def test_refresh_failure_has_no_replacement_cookie(raw: str | None) -> None:
    api = api_client()
    if raw is not None:
        api.cookies["refresh_token"] = raw
    response = api.post("/api/v1/auth/refresh", {})
    assert response.status_code == 401
    assert response.json()["error_code"] == "INVALID_TOKEN"
    assert "refresh_token" not in response.cookies
