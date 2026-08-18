import pytest

from audit.models import AuditLog, OutboxEvent
from tests.integration.api.identity.helpers import authenticated_client, create_user, manager_client
from tests.integration.api.locations.helpers import create_config, create_location


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_all_roles_list_but_only_manager_updates_with_optimistic_version() -> None:
    create_config()
    location = create_location()
    for role in ("LEADER", "MANAGER", "HELPDESK"):
        api = authenticated_client(create_user(f"location-{role.lower()}", role))
        assert api.get("/api/v1/locations/").status_code == 200
    manager_api, _manager = manager_client("location-manager-update")
    response = manager_api.patch(
        f"/api/v1/locations/{location.pk}/",
        {"version": 1, "name": "Updated", "reason": "approved"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["location"]["version"] == 2
    stale = manager_api.patch(
        f"/api/v1/locations/{location.pk}/",
        {"version": 1, "name": "Lost", "reason": "retain"},
        format="json",
    )
    assert stale.status_code == 409
    assert stale.json()["error_code"] == "LOCATION_VERSION_CONFLICT"
    assert stale.json()["details"] == {"current_version": 2, "submitted_reason": "retain"}
    assert AuditLog.objects.filter(target_type="Location").count() == 1
    assert OutboxEvent.objects.filter(aggregate_type="Location").count() == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_permission_precedes_bad_body_and_location_create_delete_are_absent() -> None:
    create_config()
    location = create_location()
    api = authenticated_client(create_user("location-helpdesk", "HELPDESK"))
    denied = api.patch(f"/api/v1/locations/{location.pk}/", {"bad": True}, format="json")
    assert denied.status_code == 403
    assert denied.json()["error_code"] == "PERMISSION_DENIED"
    assert api.post("/api/v1/locations/", {}, format="json").status_code == 404
    assert api.delete(f"/api/v1/locations/{location.pk}/").status_code == 404


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_same_value_is_noop_and_bad_route_id_is_not_found_after_permission() -> None:
    create_config()
    location = create_location()
    api, _manager = manager_client("location-same-value")
    response = api.patch(
        f"/api/v1/locations/{location.pk}/",
        {"version": 1, "name": location.name},
        format="json",
    )
    assert response.status_code == 200
    location.refresh_from_db()
    assert location.version == 1
    assert AuditLog.objects.count() == OutboxEvent.objects.count() == 0
    assert api.patch("/api/v1/locations/not-an-id/", {"version": 1, "name": "x"}).status_code == 404


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
@pytest.mark.parametrize(
    "query",
    ["unknown=value", "kind=UNKNOWN", "parent=0", "parent=bad", "is_active=maybe"],
)
def test_invalid_filters_are_rejected_with_canonical_headers_and_no_evidence(
    query: str,
) -> None:
    create_config()
    api, _manager = manager_client(f"location-filter-{query.split('=', 1)[0]}-{len(query)}")
    response = api.get(f"/api/v1/locations/?{query}")
    assert response.status_code == 400
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    assert response.headers["Cache-Control"] == "private, no-store"
    assert not AuditLog.objects.exists() and not OutboxEvent.objects.exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
@pytest.mark.parametrize("field,value", [("code", "NEW"), ("kind", "SHOP"), ("parent_id", 1)])
def test_server_owned_fields_are_rejected_without_evidence(field: str, value: object) -> None:
    create_config()
    target = create_location()
    api, _manager = manager_client(f"location-owned-{field}")
    response = api.patch(
        f"/api/v1/locations/{target.pk}/",
        {"version": 1, field: value, "name": "Changed"},
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "SERVER_OWNED_FIELD"
    assert not AuditLog.objects.exists() and not OutboxEvent.objects.exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_location_forced_password_and_inactive_precede_malformed_requests() -> None:
    create_config()
    forced = create_user("location-forced-manager", "MANAGER", must_change=True)
    forced_api = authenticated_client(forced)
    forced_response = forced_api.get("/api/v1/locations/?unknown=value")
    assert (forced_response.status_code, forced_response.json()["error_code"]) == (
        403,
        "PASSWORD_CHANGE_REQUIRED",
    )

    inactive = create_user("location-inactive-manager", "MANAGER")
    inactive_api = authenticated_client(inactive)
    inactive.is_active = False
    inactive.save(update_fields=["is_active"])
    inactive_response = inactive_api.get("/api/v1/locations/?unknown=value")
    assert (inactive_response.status_code, inactive_response.json()["error_code"]) == (
        401,
        "ACCOUNT_INACTIVE",
    )
    assert not AuditLog.objects.exists() and not OutboxEvent.objects.exists()
