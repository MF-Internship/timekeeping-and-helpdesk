from __future__ import annotations

from pathlib import Path

import pytest

from audit.models import AuditLog, OutboxEvent
from config.composition import locations_container
from locations.models import Location
from tests.integration.api.identity.helpers import create_user
from tests.integration.api.locations.helpers import create_config

ROOT = Path(__file__).parents[5]


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_seed_restores_one_drift_with_one_version_and_evidence_increment() -> None:
    create_config()
    actor = create_user("seed-drift-manager", "MANAGER")
    paths = (ROOT / "docs/dia_chi_ttkd.csv", ROOT / "docs/dia_chi_cua_hang.csv")
    service = locations_container().seed
    service.seed(actor.pk, *paths)
    target = Location.objects.get(code="HCM020129")
    Location.objects.filter(pk=target.pk).update(name="drift")
    before = (AuditLog.objects.count(), OutboxEvent.objects.count())
    changed, total, warnings = service.seed(actor.pk, *paths)
    assert (changed, total) == (1, 76)
    assert [warning.code.value for warning in warnings] == ["GEOFENCE_OVERLAP"]
    target.refresh_from_db()
    assert target.name != "drift"
    assert target.version == 2
    assert (AuditLog.objects.count(), OutboxEvent.objects.count()) == (before[0] + 1, before[1] + 1)
    assert Location.objects.count() == 76
