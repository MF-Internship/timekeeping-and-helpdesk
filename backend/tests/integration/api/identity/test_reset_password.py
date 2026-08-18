import pytest

from audit.models import AuditLog, OutboxEvent
from tests.integration.api.identity.helpers import api_client, create_user, manager_client


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_reset_is_empty_body_owned_revokes_all_refresh_and_generates_new_value_each_time() -> None:
    api, _manager = manager_client("reset-manager")
    target = create_user("reset-target")
    device = api_client()
    login = device.post(
        "/api/v1/auth/login", {"username": target.username, "password": "SafePassword123!"}
    )
    old_refresh = device.cookies["refresh_token"].value
    first = api.post(f"/api/v1/users/{target.pk}/reset-password", {})
    second = api.post(f"/api/v1/users/{target.pk}/reset-password", {})
    assert first.status_code == second.status_code == 200
    assert first.json()["generated_password"] != second.json()["generated_password"]
    stale = api_client()
    stale.cookies["refresh_token"] = old_refresh
    assert stale.post("/api/v1/auth/refresh", {}).json()["error_code"] == "INVALID_TOKEN"
    device.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}")
    residual = device.get("/api/v1/me/")
    assert residual.status_code == 403
    assert residual.json()["error_code"] == "PASSWORD_CHANGE_REQUIRED"
    injected = api.post(f"/api/v1/users/{target.pk}/reset-password", {"password": "client"})
    assert injected.json()["error_code"] == "SERVER_OWNED_FIELD"
    assert AuditLog.objects.filter(target_id=str(target.pk)).count() == 3
    assert OutboxEvent.objects.filter(aggregate_id=str(target.pk)).count() == 3
