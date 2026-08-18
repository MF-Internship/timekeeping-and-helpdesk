import pytest

from audit.models import AuditLog, OutboxEvent
from tests.integration.api.identity.helpers import authenticated_client, create_user


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_action_target_forced_change_and_dto_precedence_has_no_side_effects() -> None:
    helpdesk = create_user("forced-help", must_change=True)
    manager = create_user("forced-manager", "MANAGER", must_change=True)
    helpdesk_api = authenticated_client(helpdesk)
    manager_api = authenticated_client(manager)
    assert helpdesk_api.post("/api/v1/users/", {}).json()["error_code"] == "PERMISSION_DENIED"
    assert manager_api.post("/api/v1/users/", {}).json()["error_code"] == (
        "PASSWORD_CHANGE_REQUIRED"
    )
    manager.must_change_password = False
    manager.save(update_fields=["must_change_password"])
    protected = manager_api.patch(f"/api/v1/users/{manager.pk}/", {"role": "HELPDESK"})
    assert protected.json()["error_code"] == "PERMISSION_DENIED"
    assert AuditLog.objects.count() == OutboxEvent.objects.count() == 0
