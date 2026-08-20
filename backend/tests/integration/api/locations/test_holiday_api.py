import pytest

from audit.models import AuditLog, OutboxEvent
from tests.integration.api.identity.helpers import authenticated_client, create_user, manager_client


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_manager_creates_lists_deletes_and_duplicate_fails() -> None:
    api, _manager = manager_client("holiday-manager")
    created = api.post(
        "/api/v1/holidays/", {"date": "2026-09-02", "name": "Holiday"}, format="json"
    )
    assert created.status_code == 201
    assert api.get("/api/v1/holidays/").status_code == 200
    duplicate = api.post(
        "/api/v1/holidays/", {"date": "2026-09-02", "name": "Duplicate"}, format="json"
    )
    assert duplicate.status_code == 400
    holiday_id = created.json()["id"]
    assert api.delete(f"/api/v1/holidays/{holiday_id}/").status_code == 204
    assert api.delete(f"/api/v1/holidays/{holiday_id}/").status_code == 404
    assert AuditLog.objects.filter(target_type="Holiday").count() == 2
    assert OutboxEvent.objects.filter(aggregate_type="Holiday").count() == 2


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_non_manager_holiday_access_is_denied_before_validation() -> None:
    api = authenticated_client(create_user("holiday-helpdesk", "HELPDESK"))
    response = api.post("/api/v1/holidays/", {"bad": True}, format="json")
    assert response.status_code == 403
    assert response.json()["error_code"] == "PERMISSION_DENIED"


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
@pytest.mark.parametrize(
    "payload", [{"date": "invalid", "name": "Holiday"}, {"date": "2027-01-01", "name": ""}]
)
def test_invalid_holiday_payload_has_no_evidence(payload: dict[str, object]) -> None:
    api, _manager = manager_client(f"holiday-invalid-{len(str(payload))}")
    response = api.post("/api/v1/holidays/", payload, format="json")
    assert response.status_code == 400
    assert not AuditLog.objects.exists() and not OutboxEvent.objects.exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_holiday_malformed_nonpositive_and_missing_targets_are_equivalent() -> None:
    api, _manager = manager_client("holiday-missing-target")
    responses = [
        api.delete("/api/v1/holidays/not-an-id/"),
        api.delete("/api/v1/holidays/0/"),
        api.delete("/api/v1/holidays/999999/"),
    ]
    assert {(response.status_code, response.json()["error_code"]) for response in responses} == {
        (404, "NOT_FOUND")
    }
    assert not AuditLog.objects.exists() and not OutboxEvent.objects.exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_holiday_forced_password_and_inactive_precede_malformed_targets() -> None:
    forced = create_user("holiday-forced-manager", "MANAGER", must_change=True)
    forced_api = authenticated_client(forced)
    forced_response = forced_api.delete("/api/v1/holidays/not-an-id/")
    assert (forced_response.status_code, forced_response.json()["error_code"]) == (
        403,
        "PASSWORD_CHANGE_REQUIRED",
    )

    inactive = create_user("holiday-inactive-manager", "MANAGER")
    inactive_api = authenticated_client(inactive)
    inactive.is_active = False
    inactive.save(update_fields=["is_active"])
    inactive_response = inactive_api.delete("/api/v1/holidays/not-an-id/")
    assert (inactive_response.status_code, inactive_response.json()["error_code"]) == (
        401,
        "ACCOUNT_INACTIVE",
    )
    assert inactive_response.json()["request_id"] == inactive_response.headers["X-Request-ID"]
    assert inactive_response.headers["Cache-Control"] == "private, no-store"
    assert not AuditLog.objects.exists() and not OutboxEvent.objects.exists()
