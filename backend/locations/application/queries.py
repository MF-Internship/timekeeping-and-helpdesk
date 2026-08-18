from locations.domain.config import ConfigSnapshot
from locations.domain.locations import LocationSnapshot
from locations.ports.repositories import ConfigRepository, LocationRepository


class LocationQueryService:
    def __init__(self, locations: LocationRepository) -> None:
        self._locations = locations

    def list(
        self,
        *,
        kind: str | None = None,
        parent_id: int | None = None,
        is_active: bool | None = None,
    ) -> tuple[LocationSnapshot, ...]:
        return self._locations.list(kind=kind, parent_id=parent_id, is_active=is_active)


class ConfigQueryService:
    def __init__(self, configs: ConfigRepository) -> None:
        self._configs = configs

    def get(self) -> ConfigSnapshot | None:
        return self._configs.get()
