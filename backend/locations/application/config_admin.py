from __future__ import annotations

from datetime import time
from decimal import Decimal
from typing import Any

from core.error_codes import NOT_FOUND, VALIDATION_FAILED
from core.errors import IdentityAPIError
from identity.ports.authorization import PermissionAction
from locations.application.dependencies import LocationDependencies
from locations.application.evidence import EvidenceRequest, append_evidence, config_outbox_payload
from locations.domain.config import ConfigSnapshot, overlay_config, validate_config
from locations.domain.events import LocationEventType
from locations.domain.locations import LocationWarning, LocationWarningDetail

INVALID_FIELD_MESSAGE = "Giá trị không hợp lệ."
CONFIG_MUTABLE_FIELDS = [
    field for field in ConfigSnapshot.__dataclass_fields__ if field not in {"id", "timezone"}
]


def default_config(
    *,
    shift_start: time,
    shift_end: time,
    late_grace_minutes: int,
    early_checkout_grace_minutes: int,
) -> ConfigSnapshot:
    return ConfigSnapshot(
        1,
        "Asia/Ho_Chi_Minh",
        (0, 1, 2, 3, 4, 5),
        Decimal("50"),
        Decimal("70"),
        Decimal("25"),
        Decimal("25"),
        Decimal("100"),
        shift_start,
        shift_end,
        late_grace_minutes,
        early_checkout_grace_minutes,
        60,
    )


class ConfigAdminService:
    def __init__(self, dependencies: LocationDependencies) -> None:
        self._dependencies = dependencies

    def initialize(self, actor_id: int, candidate: ConfigSnapshot) -> ConfigSnapshot:
        self._dependencies.authorization.authorize(
            actor_id, PermissionAction.CONFIG_MANAGE_ATTENDANCE
        )
        try:
            validate_config(candidate)
        except ValueError as error:
            raise _config_validation_error(error) from error
        with self._dependencies.unit_of_work_factory():
            if self._dependencies.configs.get(lock=True) is not None:
                raise IdentityAPIError(VALIDATION_FAILED, status_code=400)
            created = self._dependencies.configs.create(candidate)
            append_evidence(
                self._dependencies.audit,
                _config_initialize_evidence(actor_id),
            )
            return created

    def update(
        self, actor_id: int, patch: dict[str, Any]
    ) -> tuple[ConfigSnapshot, tuple[LocationWarningDetail, ...]]:
        self._dependencies.authorization.authorize(
            actor_id, PermissionAction.CONFIG_MANAGE_ATTENDANCE
        )
        with self._dependencies.unit_of_work_factory():
            current = self._dependencies.configs.get(lock=True)
            if current is None:
                raise IdentityAPIError(NOT_FOUND, status_code=404)
            candidate = _validated_overlay(current, patch)
            locations = self._dependencies.locations.list()
            _ensure_radius_cap(candidate, locations)
            warnings = _config_warnings(candidate, locations)
            if candidate == current:
                return current, warnings
            saved = self._dependencies.configs.update(candidate)
            append_evidence(
                self._dependencies.audit,
                _config_update_evidence(actor_id, current, candidate, warnings),
            )
            return saved, warnings


def _validated_overlay(current: ConfigSnapshot, patch: dict[str, Any]) -> ConfigSnapshot:
    try:
        return overlay_config(current, patch)
    except (TypeError, ValueError) as error:
        raise _config_validation_error(error) from error


def _config_initialize_evidence(actor_id: int) -> EvidenceRequest:
    return EvidenceRequest(
        actor_id,
        LocationEventType.CONFIG_INITIALIZED,
        "Config",
        1,
        {},
        {"initialized": True},
        config_outbox_payload(CONFIG_MUTABLE_FIELDS),
    )


def _config_validation_error(error: TypeError | ValueError) -> IdentityAPIError:
    field = str(error)
    valid_fields = set(ConfigSnapshot.__dataclass_fields__)
    if field not in valid_fields:
        field = "non_field_errors"
    return IdentityAPIError(
        VALIDATION_FAILED,
        status_code=400,
        details={field: [INVALID_FIELD_MESSAGE]},
    )


def _ensure_radius_cap(config: ConfigSnapshot, locations: tuple[Any, ...]) -> None:
    violations = [item for item in locations if item.radius_m > config.max_radius_m]
    if violations:
        raise IdentityAPIError(
            VALIDATION_FAILED,
            status_code=400,
            details={"max_radius_m": [item.code for item in violations]},
        )


def _config_warnings(
    config: ConfigSnapshot, locations: tuple[Any, ...]
) -> tuple[LocationWarningDetail, ...]:
    affected = sorted(
        (
            item
            for item in locations
            if item.is_active and item.radius_m < config.max_attendance_accuracy_m
        ),
        key=lambda item: (item.code, item.id),
    )
    return tuple(
        LocationWarningDetail(
            LocationWarning.RADIUS_BELOW_ATTENDANCE_ACCURACY,
            (item.id,),
            (item.code,),
            item.radius_m,
            config.max_attendance_accuracy_m,
        )
        for item in affected
    )


def _config_update_evidence(
    actor_id: int,
    current: ConfigSnapshot,
    candidate: ConfigSnapshot,
    warnings: tuple[LocationWarningDetail, ...],
) -> EvidenceRequest:
    changed = {
        key: True
        for key in ConfigSnapshot.__dataclass_fields__
        if key != "id" and getattr(current, key) != getattr(candidate, key)
    }
    warning_codes = sorted({warning.code.value for warning in warnings})
    return EvidenceRequest(
        actor_id,
        LocationEventType.CONFIG_UPDATED,
        "Config",
        1,
        {"changed_fields": sorted(changed)},
        {**changed, "warning_codes": warning_codes},
        config_outbox_payload(list(changed), warning_codes),
    )
