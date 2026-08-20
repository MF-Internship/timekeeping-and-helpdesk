from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from locations.domain.config import validate_config
from locations.ports.repositories import ConfigRepository, LocationRepository
from locations.ports.source_data import LocationSource


@dataclass(frozen=True, slots=True)
class ReadinessDependencies:
    configs: ConfigRepository
    locations: LocationRepository
    source: LocationSource
    paths: tuple[Path, Path]


class ReferenceDataReadinessService:
    def __init__(self, dependencies: ReadinessDependencies) -> None:
        self._configs = dependencies.configs
        self._locations = dependencies.locations
        self._source = dependencies.source
        self._center_path, self._shop_path = dependencies.paths

    def check(self) -> tuple[bool, tuple[str, ...]]:
        config = self._configs.get()
        if config is None:
            return False, ("config_missing",)
        try:
            validate_config(config)
        except ValueError:
            return False, ("config_invalid",)
        source = {row.code: row for row in self._source.load(self._center_path, self._shop_path)}
        actual = self._locations.all_by_code()
        errors: list[str] = []
        if len(actual) != 76:
            errors.append("location_count")
        if set(actual) != set(source):
            errors.append("location_codes")
        for code in sorted(set(actual) & set(source)):
            item, expected = actual[code], source[code]
            parent = expected.parent_code if expected.parent_code in source else None
            if (
                item.kind != expected.kind
                or item.parent_code != parent
                or item.latitude != expected.latitude
                or item.longitude != expected.longitude
                or item.radius_m != config.default_radius_m
                or not item.is_active
            ):
                errors.append(f"location_drift:{code}")
        return not errors, tuple(errors)
