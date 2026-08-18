from __future__ import annotations

from decimal import Decimal

import pytest

from audit.models import AuditLog, OutboxEvent
from tests.integration.api.identity.helpers import manager_client
from tests.integration.api.locations.helpers import create_config, create_location


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_duplicate_coordinate_and_overlap_are_success_warnings_only() -> None:
    create_config()
    first = create_location("WARN00001")
    create_location("WARN00002")
    api, _manager = manager_client("location-warning-manager")
    response = api.patch(
        f"/api/v1/locations/{first.pk}/",
        {"version": 1, "radius_m": "20.000"},
        format="json",
    )
    assert response.status_code == 200
    warnings = {warning["code"]: warning for warning in response.json()["warnings"]}
    assert set(warnings) == {"GEOFENCE_OVERLAP", "RADIUS_BELOW_ATTENDANCE_ACCURACY"}
    assert warnings["GEOFENCE_OVERLAP"]["related_location_ids"]
    assert warnings["GEOFENCE_OVERLAP"]["related_location_codes"] == ["WARN00002"]
    assert warnings["RADIUS_BELOW_ATTENDANCE_ACCURACY"] == {
        "code": "RADIUS_BELOW_ATTENDANCE_ACCURACY",
        "radius_m": "20.000",
        "threshold_m": "25.000",
    }
    assert AuditLog.objects.count() == OutboxEvent.objects.count() == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
@pytest.mark.parametrize(
    "field,value", [("latitude", "91"), ("longitude", "181"), ("radius_m", "0")]
)
def test_invalid_location_geometry_has_no_evidence(field: str, value: str) -> None:
    create_config()
    target = create_location()
    api, _manager = manager_client(f"location-invalid-{field}")
    response = api.patch(
        f"/api/v1/locations/{target.pk}/", {"version": 1, field: value}, format="json"
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "VALIDATION_FAILED"
    target.refresh_from_db()
    assert target.version == 1 and target.radius_m == Decimal("50")
    assert not AuditLog.objects.exists() and not OutboxEvent.objects.exists()
