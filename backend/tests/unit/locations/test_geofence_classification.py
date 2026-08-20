from decimal import Decimal
from inspect import signature

from locations.domain.geofence import LocationValidationResult, classify_geofence


def test_classifier_has_exactly_two_results_and_inclusive_radius() -> None:
    assert {item.value for item in LocationValidationResult} == {
        "INSIDE_GEOFENCE",
        "OUTSIDE_GEOFENCE",
    }
    assert classify_geofence(40, Decimal("50")) is LocationValidationResult.INSIDE_GEOFENCE
    assert classify_geofence(50, Decimal("50")) is LocationValidationResult.INSIDE_GEOFENCE
    assert classify_geofence(60, Decimal("50")) is LocationValidationResult.OUTSIDE_GEOFENCE
    assert "accuracy" not in signature(classify_geofence).parameters
