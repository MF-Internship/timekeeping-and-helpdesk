from typing import Protocol

from locations.domain.geofence import LocationValidationResult, ValidatedPosition
from locations.domain.locations import LocationSnapshot


class GeofenceService(Protocol):
    def evaluate(
        self, position: ValidatedPosition, location: LocationSnapshot
    ) -> tuple[float, LocationValidationResult]: ...
