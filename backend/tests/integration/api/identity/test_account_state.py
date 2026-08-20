import pytest

from tests.integration.api.identity.helpers import authenticated_client, create_user


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_every_bearer_request_reloads_current_active_and_role_state() -> None:
    account = create_user("state")
    api = authenticated_client(account)
    account.role = "LEADER"
    account.save(update_fields=["role"])
    assert api.get("/api/v1/me/").json()["role"] == "LEADER"
    account.is_active = False
    account.save(update_fields=["is_active"])
    denied = api.get("/api/v1/me/")
    assert denied.status_code == 401
    assert denied.json()["error_code"] == "ACCOUNT_INACTIVE"
