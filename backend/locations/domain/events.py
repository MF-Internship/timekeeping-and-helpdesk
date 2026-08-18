from enum import StrEnum


class LocationEventType(StrEnum):
    LOCATION_SEEDED = "locations.location.seeded"
    LOCATION_RECONCILED = "locations.location.reconciled"
    LOCATION_UPDATED = "locations.location.updated"
    CONFIG_INITIALIZED = "locations.config.initialized"
    CONFIG_UPDATED = "locations.config.updated"
    HOLIDAY_CREATED = "locations.holiday.created"
    HOLIDAY_DELETED = "locations.holiday.deleted"
