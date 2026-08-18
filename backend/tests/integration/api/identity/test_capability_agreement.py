import pytest

from identity.domain.authorization import Role, effective_capabilities
from tests.integration.api.identity.helpers import api_client, create_user


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_login_and_me_capabilities_match_pure_policy_for_every_role() -> None:
    for role in Role:
        account = create_user(f"agreement-{role.value.lower()}", role.value)
        api = api_client()
        login = api.post(
            "/api/v1/auth/login",
            {"username": account.username, "password": "SafePassword123!"},
        )
        expected = sorted(action.value for action in effective_capabilities(role))
        assert login.json()["capabilities"] == expected
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}")
        assert api.get("/api/v1/me/").json()["capabilities"] == expected
