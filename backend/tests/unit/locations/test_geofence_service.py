from __future__ import annotations

from decimal import Decimal
from inspect import signature

import pytest

from locations.application.geofence import DefaultGeofenceService
from locations.domain.geofence import LocationValidationResult, ValidatedPosition
from locations.domain.locations import LocationKind, LocationSnapshot


def snapshot(radius: str = "50") -> LocationSnapshot:
    return LocationSnapshot(
        1,
        "A",
        "A",
        LocationKind.SHOP,
        None,
        None,
        "Address",
        Decimal("10"),
        Decimal("106"),
        Decimal(radius),
        True,
        1,
    )


@pytest.mark.unit
def test_accuracy_is_independent_from_membership_and_service_has_no_workflow_decision() -> None:
    service = DefaultGeofenceService()
    close = ValidatedPosition(Decimal("10"), Decimal("106"), Decimal("20"))
    poor = ValidatedPosition(Decimal("10"), Decimal("106"), Decimal("200"))
    assert service.evaluate(close, snapshot())[1] is LocationValidationResult.INSIDE_GEOFENCE
    assert service.evaluate(poor, snapshot())[1] is LocationValidationResult.INSIDE_GEOFENCE
    assert list(signature(service.evaluate).parameters) == ["position", "location"]
