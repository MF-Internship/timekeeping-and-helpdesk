from __future__ import annotations

import pytest

from audit.models import AuditLog, OutboxEvent
from config.composition import locations_container
from locations.application.dto import UpdateLocationRequest
from tests.integration.api.identity.helpers import create_user
from tests.integration.api.locations.helpers import create_config, create_location


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.parametrize("recorder_method", ["append_audit_entry", "append_outbox_event"])
def test_location_update_rolls_back_on_evidence_failure_and_never_evidences_coordinates(
    monkeypatch: pytest.MonkeyPatch, recorder_method: str
) -> None:
    create_config()
    target = create_location()
    actor = create_user("location-rollback-manager", "MANAGER")
    service = locations_container().location_admin
    monkeypatch.setattr(
        service._dependencies.audit,
        recorder_method,
        lambda event: (_ for _ in ()).throw(RuntimeError("injected")),
    )
    with pytest.raises(RuntimeError, match="injected"):
        service.update(actor.pk, target.pk, UpdateLocationRequest(version=1, name="Changed"))
    target.refresh_from_db()
    assert target.name == "Test Location" and target.version == 1
    assert not AuditLog.objects.exists() and not OutboxEvent.objects.exists()
