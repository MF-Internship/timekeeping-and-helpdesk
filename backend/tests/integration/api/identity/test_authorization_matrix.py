import pytest

from audit.models import AuditLog, OutboxEvent
from tests.integration.api.identity.helpers import authenticated_client, create_user


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
@pytest.mark.parametrize("role", ["LEADER", "HELPDESK"])
def test_non_manager_user_admin_denial_beats_forced_change_and_invalid_body(role: str) -> None:
    actor = create_user(f"denied-{role.lower()}", role, must_change=True)
    api = authenticated_client(actor)
    response = api.post("/api/v1/users/", {"malformed": True})
    assert response.status_code == 403
    assert response.json()["error_code"] == "PERMISSION_DENIED"
    assert AuditLog.objects.count() == OutboxEvent.objects.count() == 0
