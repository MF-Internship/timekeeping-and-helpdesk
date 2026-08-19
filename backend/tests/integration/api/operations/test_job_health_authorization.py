import json

import pytest

from tests.integration.api.identity.helpers import api_client, authenticated_client, create_user

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("role", ["MANAGER", "LEADER"])
def test_authorized_roles_receive_global_private_health(role: str) -> None:
    response = authenticated_client(create_user(f"health-{role.lower()}", role)).get(
        "/api/v1/operations/job-health"
    )
    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"
    assert response.json()["state"] in {"ok", "alert", "unknown"}


def test_helpdesk_is_denied_before_input_validation() -> None:
    response = authenticated_client(create_user("health-helpdesk", "HELPDESK")).get(
        "/api/v1/operations/job-health?user_id=1"
    )
    assert (response.status_code, response.json()["error_code"]) == (403, "PERMISSION_DENIED")


def test_authorized_query_scope_is_rejected() -> None:
    response = authenticated_client(create_user("health-manager-query", "MANAGER")).get(
        "/api/v1/operations/job-health?user_id=1"
    )
    assert (response.status_code, response.json()["error_code"]) == (400, "VALIDATION_FAILED")


def test_unauthenticated_and_account_states_use_canonical_ordering() -> None:
    anonymous = api_client().get("/api/v1/operations/job-health")
    assert (anonymous.status_code, anonymous.json()["error_code"]) == (401, "INVALID_TOKEN")
    inactive = create_user("health-inactive", "MANAGER")
    inactive_client = authenticated_client(inactive)
    inactive.is_active = False
    inactive.save(update_fields=["is_active"])
    forced = create_user("health-forced", "MANAGER")
    forced_client = authenticated_client(forced)
    forced.must_change_password = True
    forced.save(update_fields=["must_change_password"])
    assert (
        inactive_client.get("/api/v1/operations/job-health").json()["error_code"]
        == "ACCOUNT_INACTIVE"
    )
    assert (
        forced_client.get("/api/v1/operations/job-health").json()["error_code"]
        == "PASSWORD_CHANGE_REQUIRED"
    )


def test_global_aggregate_is_equal_across_authorized_scopes_and_body_is_rejected() -> None:
    manager = authenticated_client(create_user("health-global-manager", "MANAGER"))
    leader = authenticated_client(create_user("health-global-leader", "LEADER"))
    manager_payload = manager.get("/api/v1/operations/job-health").json()
    leader_payload = leader.get("/api/v1/operations/job-health").json()
    for field in ("state", "overdue_open_session_count", "evidence_counts", "reason_flags"):
        assert manager_payload[field] == leader_payload[field]
    body = manager.generic(
        "GET",
        "/api/v1/operations/job-health",
        json.dumps({"user_id": 1}),
        content_type="application/json",
    )
    assert (body.status_code, body.json()["error_code"]) == (400, "VALIDATION_FAILED")
