import pytest

from audit.models import AuditLog, OutboxEvent
from tests.integration.api.identity.helpers import manager_client


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_generated_plaintext_exists_only_in_immediate_create_response() -> None:
    api, _manager = manager_client("secret-manager")
    created = api.post(
        "/api/v1/users/",
        {"username": "secret-worker", "full_name": "Secret Worker", "role": "HELPDESK"},
    )
    plaintext = created.json()["generated_password"]
    target_id = created.json()["user"]["id"]
    assert "generated_password" not in api.get(f"/api/v1/users/{target_id}/").json()
    persisted = repr(list(AuditLog.objects.values())) + repr(list(OutboxEvent.objects.values()))
    assert plaintext not in persisted
