from __future__ import annotations

from dataclasses import dataclass

from identity.ports.authorization import AuthorizationGateway
from locations.application.config_admin import ConfigAdminService
from locations.application.holidays import HolidayService
from locations.application.location_admin import LocationAdminService
from locations.application.queries import ConfigQueryService, LocationQueryService
from locations.application.readiness import ReferenceDataReadinessService
from locations.application.seed import LocationSeedService


@dataclass(frozen=True, slots=True)
class LocationsContainer:
    authorization: AuthorizationGateway
    location_queries: LocationQueryService
    location_admin: LocationAdminService
    config_queries: ConfigQueryService
    config_admin: ConfigAdminService
    holidays: HolidayService
    seed: LocationSeedService
    readiness: ReferenceDataReadinessService
