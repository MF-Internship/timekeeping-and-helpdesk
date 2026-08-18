import pytest

from audit.models import AuditLog, OutboxEvent
from tests.integration.api.identity.helpers import api_client, authenticated_client, create_user

TARGET_OPERATIONS = (
    ("get", "/api/v1/users/not-an-id/", None),
    ("patch", "/api/v1/users/not-an-id/", {"unexpected": True}),
    ("patch", "/api/v1/users/not-an-id/role", {}),
    ("patch", "/api/v1/users/not-an-id/status", {"is_active": "invalid"}),
    ("post", "/api/v1/users/not-an-id/reset-password", {"unexpected": True}),
)


def _request(client: object, method: str, path: str, body: object) -> object:
    call = getattr(client, method)
    return call(path) if body is None else call(path, body)


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
@pytest.mark.parametrize(("method", "path", "body"), TARGET_OPERATIONS)
def test_malformed_target_id_does_not_bypass_authentication(
    method: str, path: str, body: object
) -> None:
    response = _request(api_client(), method, path, body)

    assert response.status_code == 401
    assert response.json()["error_code"] == "INVALID_TOKEN"


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
@pytest.mark.parametrize("role", ["LEADER", "HELPDESK"])
@pytest.mark.parametrize(("method", "path", "body"), TARGET_OPERATIONS)
def test_malformed_target_id_does_not_bypass_action_rbac(
    role: str, method: str, path: str, body: object
) -> None:
    actor = create_user(f"malformed-{role.lower()}-{method}", role)
    response = _request(authenticated_client(actor), method, path, body)

    assert response.status_code == 403
    assert response.json()["error_code"] == "PERMISSION_DENIED"
    assert AuditLog.objects.count() == 0
    assert OutboxEvent.objects.count() == 0


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
@pytest.mark.parametrize(("method", "path", "body"), TARGET_OPERATIONS)
def test_authorized_actor_validates_route_id_before_body(
    method: str, path: str, body: object
) -> None:
    manager = create_user(f"malformed-manager-{method}", "MANAGER")
    response = _request(authenticated_client(manager), method, path, body)

    assert response.status_code == 404
    assert AuditLog.objects.count() == 0
    assert OutboxEvent.objects.count() == 0


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_forced_authorized_actor_is_gated_before_route_id_validation() -> None:
    manager = create_user("malformed-forced-manager", "MANAGER", must_change=True)

    response = authenticated_client(manager).patch(
        "/api/v1/users/not-an-id/status", {"is_active": "invalid"}
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "PASSWORD_CHANGE_REQUIRED"
