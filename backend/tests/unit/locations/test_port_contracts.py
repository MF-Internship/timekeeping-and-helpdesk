from locations.domain.events import LocationEventType
from locations.domain.geofence import LocationValidationResult
from locations.domain.locations import LocationKind, LocationWarning


def test_closed_feature_vocabularies() -> None:
    assert len(LocationKind) == 2
    assert len(LocationWarning) == 2
    assert {warning.value for warning in LocationWarning} == {
        "GEOFENCE_OVERLAP",
        "RADIUS_BELOW_ATTENDANCE_ACCURACY",
    }
    assert len(LocationValidationResult) == 2
    assert len(LocationEventType) == 7
