from datetime import timedelta

import pytest
from rest_framework_simplejwt.tokens import RefreshToken

from audit.models import AuditLog, OutboxEvent
from tests.integration.api.identity.helpers import api_client, authenticated_client, create_user


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_logout_requires_same_user_access_and_valid_refresh_cookie() -> None:
    first = create_user("first")
    second = create_user("second")
    api = authenticated_client(first)
    refresh = api.cookies["refresh_token"].value
    del api.cookies["refresh_token"]
    assert api.post("/api/v1/auth/logout", {}).json()["error_code"] == "INVALID_TOKEN"
    second_api = authenticated_client(second)
    second_api.cookies["refresh_token"] = refresh
    mismatch = second_api.post("/api/v1/auth/logout", {})
    assert mismatch.status_code == 401
    assert mismatch.json()["error_code"] == "INVALID_TOKEN"
    assert AuditLog.objects.count() == 0


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_logout_globally_revokes_refresh_and_reuse_has_no_success_evidence() -> None:
    account = create_user("logout")
    first = authenticated_client(account)
    first_refresh = first.cookies["refresh_token"].value
    second = authenticated_client(account)
    second_refresh = second.cookies["refresh_token"].value
    response = first.post("/api/v1/auth/logout", {})
    assert response.status_code == 204
    cleared = response.cookies["refresh_token"]
    assert cleared.value == ""
    assert cleared["path"] == "/api/v1/auth/"
    assert cleared["secure"] is True
    assert cleared["httponly"] is True
    assert cleared["samesite"] == "Strict"
    assert cleared["max-age"] == 0
    evidence = AuditLog.objects.count()
    for raw in (first_refresh, second_refresh):
        candidate = api_client()
        candidate.cookies["refresh_token"] = raw
        assert candidate.post("/api/v1/auth/refresh", {}).json()["error_code"] == "INVALID_TOKEN"
    first.cookies["refresh_token"] = first_refresh
    assert first.post("/api/v1/auth/logout", {}).json()["error_code"] == "INVALID_TOKEN"
    assert AuditLog.objects.count() == evidence


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_logout_rejects_malformed_expired_and_json_credentials_without_evidence() -> None:
    account = create_user("logout-invalid")
    api = authenticated_client(account)
    valid_refresh = api.cookies["refresh_token"].value
    expired = RefreshToken.for_user(account)
    expired.set_exp(lifetime=timedelta(seconds=-1))
    for raw in ("malformed", str(expired)):
        api.cookies["refresh_token"] = raw
        response = api.post("/api/v1/auth/logout", {})
        assert response.status_code == 401
        assert response.json()["error_code"] == "INVALID_TOKEN"
    api.cookies["refresh_token"] = valid_refresh
    injected = api.post("/api/v1/auth/logout", {"refresh_token": "client-owned"})
    assert injected.status_code == 400
    assert injected.json()["error_code"] == "SERVER_OWNED_FIELD"
    assert AuditLog.objects.count() == 0


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_logout_target_and_forced_gate_precede_body_validation() -> None:
    forced = create_user("logout-forced", must_change=True)
    forced_api = authenticated_client(forced)
    valid_refresh = forced_api.cookies["refresh_token"].value

    allowed_target = forced_api.post("/api/v1/auth/logout", {"unexpected": True})
    assert allowed_target.status_code == 403
    assert allowed_target.json()["error_code"] == "PASSWORD_CHANGE_REQUIRED"

    del forced_api.cookies["refresh_token"]
    missing = forced_api.post("/api/v1/auth/logout", {"unexpected": True})
    assert missing.status_code == 401
    assert missing.json()["error_code"] == "INVALID_TOKEN"

    RefreshToken(valid_refresh).blacklist()
    forced_api.cookies["refresh_token"] = valid_refresh
    revoked = forced_api.post("/api/v1/auth/logout", {"unexpected": True})
    assert revoked.status_code == 401
    assert revoked.json()["error_code"] == "INVALID_TOKEN"
    assert AuditLog.objects.count() == 0
    assert OutboxEvent.objects.count() == 0
