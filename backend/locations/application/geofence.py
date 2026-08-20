from locations.domain.geofence import (
    LocationValidationResult,
    ValidatedPosition,
    classify_geofence,
    haversine_distance_m,
)
from locations.domain.locations import Coordinates, LocationSnapshot


class DefaultGeofenceService:
    def evaluate(
        self, position: ValidatedPosition, location: LocationSnapshot
    ) -> tuple[float, LocationValidationResult]:
        distance = haversine_distance_m(
            position.coordinates,
            Coordinates(location.latitude, location.longitude),
        )
        return distance, classify_geofence(distance, location.radius_m)
