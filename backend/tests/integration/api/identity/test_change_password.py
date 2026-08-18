import pytest

from tests.integration.api.identity.helpers import api_client, authenticated_client, create_user


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_change_password_rolls_back_invalid_current_and_replaces_refresh_session() -> None:
    account = create_user("password", must_change=True)
    api = authenticated_client(account)
    old_refresh = api.cookies["refresh_token"].value
    denied = api.post(
        "/api/v1/change-password", {"current_password": "wrong", "new_password": "NewSafe123!"}
    )
    assert denied.status_code == 400
    assert account.check_password("SafePassword123!")
    changed = api.post(
        "/api/v1/change-password",
        {"current_password": "SafePassword123!", "new_password": "NewSafePassword456!"},
    )
    assert changed.status_code == 200
    assert api.cookies["refresh_token"].value != old_refresh
    stale = api_client()
    stale.cookies["refresh_token"] = old_refresh
    assert stale.post("/api/v1/auth/refresh", {}).json()["error_code"] == "INVALID_TOKEN"
    assert api.post("/api/v1/auth/refresh", {}).status_code == 200
