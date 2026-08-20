from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.error_codes import NOT_FOUND, VALIDATION_FAILED
from core.errors import IdentityAPIError
from identity.ports.authorization import PermissionAction
from locations.application.dependencies import LocationDependencies
from locations.application.evidence import EvidenceRequest, append_evidence, location_outbox_payload
from locations.domain.config import ConfigSnapshot, validate_config
from locations.domain.events import LocationEventType
from locations.domain.geofence import geofences_overlap
from locations.domain.locations import (
    Coordinates,
    LocationSnapshot,
    LocationWarning,
    LocationWarningDetail,
)
from locations.ports.source_data import SourceLocation

SEEDED_CHANGED_FIELDS = [
    "name",
    "kind",
    "parent_id",
    "address",
    "latitude",
    "longitude",
    "radius_m",
    "is_active",
]


@dataclass(frozen=True, slots=True)
class SeedMutation:
    saved: LocationSnapshot
    event: LocationEventType
    changed_fields: tuple[str, ...]


SeedMutations = tuple[SeedMutation, ...]


class LocationSeedService:
    def __init__(self, dependencies: LocationDependencies) -> None:
        self._dependencies = dependencies

    def seed(
        self, actor_id: int, center_path: Path, shop_path: Path
    ) -> tuple[int, int, tuple[LocationWarningDetail, ...]]:
        self._dependencies.authorization.authorize(actor_id, PermissionAction.LOCATION_MANAGE)
        rows = self._dependencies.source.load(center_path, shop_path)
        with self._dependencies.unit_of_work_factory():
            config = self._dependencies.configs.get(lock=True)
            if config is None:
                raise IdentityAPIError(NOT_FOUND, status_code=404)
            _validate_seed_config(config)
            mutations = self._reconcile(rows, config)
            self._link_parents(rows)
            self._verify_final_state(rows, config)
            warnings = self._warnings()
            warning_codes = sorted({warning.code.value for warning in warnings})
            for mutation in mutations:
                self._record(actor_id, mutation, warning_codes)
        return len(mutations), 76, warnings

    def _warnings(self) -> tuple[LocationWarningDetail, ...]:
        locations = sorted(
            self._dependencies.locations.all_by_code().values(), key=lambda item: item.code
        )
        return _seed_overlap_warnings(tuple(locations))

    def _reconcile(self, rows: tuple[SourceLocation, ...], config: ConfigSnapshot) -> SeedMutations:
        expected_codes = {row.code for row in rows}
        current = self._dependencies.locations.all_by_code(lock=True)
        _ensure_no_unexpected_identity(current, expected_codes)
        mutations: list[SeedMutation] = []
        for row in rows:
            existing = current.get(row.code)
            values = _source_values(row, config)
            if existing is None:
                saved = self._dependencies.locations.create_source(values)
                mutations.append(
                    SeedMutation(
                        saved,
                        LocationEventType.LOCATION_SEEDED,
                        tuple(SEEDED_CHANGED_FIELDS),
                    )
                )
            elif changed_fields := _source_changed_fields(existing, row, config, expected_codes):
                saved = self._dependencies.locations.reconcile_source(
                    row.code, values, existing.version + 1
                )
                mutations.append(
                    SeedMutation(
                        saved,
                        LocationEventType.LOCATION_RECONCILED,
                        tuple(changed_fields),
                    )
                )
        return tuple(mutations)

    def _link_parents(self, rows: tuple[SourceLocation, ...]) -> None:
        codes = {row.code for row in rows}
        for row in rows:
            parent_code = row.parent_code if row.parent_code in codes else None
            self._dependencies.locations.set_parent(row.code, parent_code)

    def _verify_final_state(self, rows: tuple[SourceLocation, ...], config: ConfigSnapshot) -> None:
        final = self._dependencies.locations.all_by_code()
        expected_codes = {row.code for row in rows}
        if len(final) != 76 or set(final) != expected_codes:
            raise IdentityAPIError(VALIDATION_FAILED, status_code=400)
        for row in rows:
            item = final[row.code]
            expected_parent = row.parent_code if row.parent_code in expected_codes else None
            if (
                item.name != row.name
                or item.kind != row.kind
                or item.parent_code != expected_parent
                or item.address != row.address
                or item.latitude != row.latitude
                or item.longitude != row.longitude
                or item.radius_m != config.default_radius_m
                or not item.is_active
            ):
                raise IdentityAPIError(
                    VALIDATION_FAILED, status_code=400, details={"code": [row.code]}
                )

    def _record(
        self,
        actor_id: int,
        mutation: SeedMutation,
        warning_codes: list[str],
    ) -> None:
        saved, event, changed_fields = (
            mutation.saved,
            mutation.event,
            mutation.changed_fields,
        )
        before = (
            {} if event is LocationEventType.LOCATION_SEEDED else {"version": saved.version - 1}
        )
        append_evidence(
            self._dependencies.audit,
            EvidenceRequest(
                actor_id,
                event,
                "Location",
                saved.id,
                before,
                {
                    "code": saved.code,
                    "version": saved.version,
                    "warning_codes": warning_codes,
                },
                location_outbox_payload(saved, list(changed_fields), warning_codes),
            ),
        )


def _validate_seed_config(config: ConfigSnapshot) -> None:
    try:
        validate_config(config)
    except ValueError as error:
        field = str(error)
        if field not in ConfigSnapshot.__dataclass_fields__:
            field = "non_field_errors"
        raise IdentityAPIError(
            VALIDATION_FAILED,
            status_code=400,
            details={field: ["Giá trị không hợp lệ."]},
        ) from error


def _seed_overlap_warnings(
    locations: tuple[LocationSnapshot, ...],
) -> tuple[LocationWarningDetail, ...]:
    related: dict[int, LocationSnapshot] = {}
    for index, first in enumerate(locations):
        for second in locations[index + 1 :]:
            if geofences_overlap(
                Coordinates(first.latitude, first.longitude),
                first.radius_m,
                Coordinates(second.latitude, second.longitude),
                second.radius_m,
            ):
                related[first.id] = first
                related[second.id] = second
    if not related:
        return ()
    affected = sorted(related.values(), key=lambda item: (item.code, item.id))
    return (
        LocationWarningDetail(
            LocationWarning.GEOFENCE_OVERLAP,
            tuple(item.id for item in affected),
            tuple(item.code for item in affected),
        ),
    )


def _ensure_no_unexpected_identity(
    current: dict[str, LocationSnapshot], expected_codes: set[str]
) -> None:
    unexpected = sorted(set(current) - expected_codes)
    if unexpected:
        raise IdentityAPIError(
            VALIDATION_FAILED, status_code=400, details={"code": [unexpected[0]]}
        )


def _source_values(row: SourceLocation, config: ConfigSnapshot) -> dict[str, object]:
    return {
        "code": row.code,
        "name": row.name,
        "kind": row.kind.value,
        "address": row.address,
        "latitude": row.latitude,
        "longitude": row.longitude,
        "radius_m": config.default_radius_m,
        "is_active": True,
    }


def _is_drifted(
    existing: LocationSnapshot,
    row: SourceLocation,
    config: ConfigSnapshot,
    expected_codes: set[str],
) -> bool:
    return bool(_source_changed_fields(existing, row, config, expected_codes))


def _source_changed_fields(
    existing: LocationSnapshot,
    row: SourceLocation,
    config: ConfigSnapshot,
    expected_codes: set[str],
) -> list[str]:
    expected_parent = row.parent_code if row.parent_code in expected_codes else None
    comparisons = {
        "name": existing.name != row.name,
        "kind": existing.kind != row.kind,
        "address": existing.address != row.address,
        "latitude": existing.latitude != row.latitude,
        "longitude": existing.longitude != row.longitude,
        "radius_m": existing.radius_m != config.default_radius_m,
        "is_active": not existing.is_active,
        "parent_id": existing.parent_code != expected_parent,
    }
    return [field for field, changed in comparisons.items() if changed]
