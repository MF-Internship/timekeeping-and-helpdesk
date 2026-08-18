from datetime import UTC, datetime, timedelta

import pytest
from django.conf import settings
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from tests.integration.api.identity.helpers import api_client, create_user


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
