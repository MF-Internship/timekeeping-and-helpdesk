import json

import pytest

from audit.models import AuditLog, OutboxEvent
from tests.integration.api.identity.helpers import authenticated_client, create_user

pytestmark = pytest.mark.django_db


def test_manager_gets_only_authorized_account_link_without_read_side_effects() -> None:
    client = authenticated_client(create_user("health-private-manager", "MANAGER"))
    before = AuditLog.objects.count(), OutboxEvent.objects.count()
    response = client.get("/api/v1/operations/job-health")
    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"
    payload = response.json()
    assert payload["investigation_links"] == {"accounts": "/api/v1/users/"}
    assert payload["escalation_guidance"] is None
    assert (AuditLog.objects.count(), OutboxEvent.objects.count()) == before


def test_leader_gets_escalation_only_without_sensitive_detail_or_links() -> None:
    client = authenticated_client(create_user("health-private-leader", "LEADER"))
    response = client.get("/api/v1/operations/job-health")
    payload = response.json()
    assert response.status_code == 200
    assert payload["investigation_links"] is None
    assert "MANAGER" in payload["escalation_guidance"]
    serialized = json.dumps(payload).lower()
    for forbidden in (
        "user_id",
        "session_id",
        "latitude",
        "longitude",
        "gps",
        "traceback",
        "secret",
    ):
        assert forbidden not in serialized


def test_no_rerun_or_repair_routes_are_exposed() -> None:
    client = authenticated_client(create_user("health-no-mutation", "MANAGER"))
    assert client.post("/api/v1/operations/job-health").status_code == 405
    assert client.post("/api/v1/operations/job-health/rerun").status_code == 404
    assert client.post("/api/v1/operations/job-health/repair").status_code == 404
