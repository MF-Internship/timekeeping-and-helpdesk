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
def test_seed_is_exact_and_idempotent() -> None:
    create_config()
    actor = create_user("seed-manager", "MANAGER")
    service = locations_container().seed
    paths = (ROOT / "docs/dia_chi_ttkd.csv", ROOT / "docs/dia_chi_cua_hang.csv")
    changed, total, warnings = service.seed(actor.pk, *paths)
    assert (changed, total) == (76, 76)
    assert [warning.code.value for warning in warnings] == ["GEOFENCE_OVERLAP"]
    assert warnings[0].related_location_ids
    assert warnings[0].related_location_codes
    assert Location.objects.count() == 76
    assert Location.objects.filter(kind="BUSINESS_CENTER").count() == 7
    assert Location.objects.filter(kind="SHOP").count() == 69
    assert Location.objects.filter(parent=None, kind="BUSINESS_CENTER").count() == 7
    assert Location.objects.get(code="HCM020129").parent.code == "HCM020000"
    assert Location.objects.get(code="HCM000079").parent is None
    evidence = (AuditLog.objects.count(), OutboxEvent.objects.count())
    assert {
        tuple(value)
        for value in AuditLog.objects.values_list("after__warning_codes", flat=True)
        if value
    } == {("GEOFENCE_OVERLAP",)}
    assert {
        tuple(value)
        for value in OutboxEvent.objects.values_list("payload__warning_codes", flat=True)
        if value
    } == {("GEOFENCE_OVERLAP",)}
    changed, total, rerun_warnings = service.seed(actor.pk, *paths)
    assert (changed, total) == (0, 76)
    assert rerun_warnings == warnings
    assert (AuditLog.objects.count(), OutboxEvent.objects.count()) == evidence
