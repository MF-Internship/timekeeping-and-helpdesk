from __future__ import annotations

import pytest

from audit.models import AuditLog, OutboxEvent
from config.composition import locations_container
from core.errors import IdentityAPIError
from locations.application.dto import UpdateLocationRequest
from locations.models import Location
from tests.integration.api.identity.helpers import create_user
from tests.integration.api.locations.helpers import create_config, create_location


@pytest.mark.django_db
@pytest.mark.unit
def test_queries_are_stable_global_and_filtered_and_update_evidence_is_exact() -> None:
    create_config()
    center = create_location("CENTER000")
    center.kind = "BUSINESS_CENTER"
    center.save(update_fields=["kind"])
    shop = create_location("SHOP00001")
    Location.objects.filter(pk=shop.pk).update(parent=center)
    query = locations_container().location_queries
    assert [item.code for item in query.list()] == ["CENTER000", "SHOP00001"]
    assert [item.code for item in query.list(kind="SHOP", parent_id=center.pk)] == ["SHOP00001"]
    actor = create_user("location-service-manager", "MANAGER")
    saved, _warnings = locations_container().location_admin.update(
        actor.pk, shop.pk, UpdateLocationRequest(version=1, name="Changed", reason="approved")
    )
    assert saved.version == 2
    audit = AuditLog.objects.get(target_type="Location")
    assert audit.after["reason"] == "approved"
    assert audit.after["warning_codes"] == ["GEOFENCE_OVERLAP"]
    event = OutboxEvent.objects.get(aggregate_type="Location")
    assert event.payload == {
        "action": "locations.location.updated",
        "location_id": shop.pk,
        "code": shop.code,
        "version": 2,
        "changed_fields": ["name"],
        "warning_codes": ["GEOFENCE_OVERLAP"],
    }


@pytest.mark.django_db
@pytest.mark.unit
def test_stale_check_precedes_same_value_noop() -> None:
    create_config()
    target = create_location()
    actor = create_user("location-stale-manager", "MANAGER")
    Location.objects.filter(pk=target.pk).update(version=2)
    with pytest.raises(IdentityAPIError) as error:
        locations_container().location_admin.update(
            actor.pk, target.pk, UpdateLocationRequest(version=1, name=target.name)
        )
    assert error.value.error_code == "LOCATION_VERSION_CONFLICT"
    assert error.value.details == {"current_version": 2}
    assert not AuditLog.objects.exists() and not OutboxEvent.objects.exists()
