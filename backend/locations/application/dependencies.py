from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from audit.ports.recording import AuditRecorder
from identity.ports.authorization import AuthorizationGateway
from locations.ports.repositories import ConfigRepository, HolidayRepository, LocationRepository
from locations.ports.source_data import LocationSource
from locations.ports.unit_of_work import UnitOfWork


@dataclass(frozen=True, slots=True)
class LocationDependencies:
    locations: LocationRepository
    configs: ConfigRepository
    holidays: HolidayRepository
    source: LocationSource
    authorization: AuthorizationGateway
    audit: AuditRecorder
    unit_of_work_factory: Callable[[], UnitOfWork]
