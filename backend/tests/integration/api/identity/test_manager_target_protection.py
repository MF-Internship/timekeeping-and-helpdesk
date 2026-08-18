import pytest

from audit.models import AuditLog, OutboxEvent
from tests.integration.api.identity.helpers import manager_client


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
@pytest.mark.parametrize(
    "method,path_suffix,body",
    [
        ("patch", "/", {"unexpected": True}),
        ("patch", "/role", {}),
        ("patch", "/status", {"is_active": "invalid"}),
        ("post", "/reset-password", {"unexpected": True}),
    ],
)
def test_manager_target_denial_precedes_every_payload_shape(
    method: str, path_suffix: str, body: dict[str, object]
) -> None:
    api, manager = manager_client(f"protected-{path_suffix.strip('/').replace('/', '-') or 'self'}")
    response = getattr(api, method)(f"/api/v1/users/{manager.pk}{path_suffix}", body)
    assert response.status_code == 403
    assert response.json()["error_code"] == "PERMISSION_DENIED"
    assert AuditLog.objects.count() == OutboxEvent.objects.count() == 0
