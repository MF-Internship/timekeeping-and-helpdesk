from __future__ import annotations

import pytest

from audit.models import AuditLog, OutboxEvent
from config.composition import locations_container
from tests.integration.api.identity.helpers import create_user
from tests.integration.api.locations.helpers import create_config, create_location


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.parametrize("recorder_method", ["append_audit_entry", "append_outbox_event"])
def test_config_update_rolls_back_with_evidence_and_never_rewrites_locations(
    monkeypatch: pytest.MonkeyPatch,
    recorder_method: str,
) -> None:
    config = create_config()
    location = create_location()
    actor = create_user("config-rollback-manager", "MANAGER")
    service = locations_container().config_admin
    monkeypatch.setattr(
        service._dependencies.audit,
        recorder_method,
        lambda event: (_ for _ in ()).throw(RuntimeError("injected")),
    )
    with pytest.raises(RuntimeError, match="injected"):
        service.update(actor.pk, {"late_grace_minutes": 20})
    config.refresh_from_db()
    location.refresh_from_db()
    assert config.late_grace_minutes == 15
    assert location.radius_m == 50 and location.version == 1
    assert not AuditLog.objects.exists() and not OutboxEvent.objects.exists()
