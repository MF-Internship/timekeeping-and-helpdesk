from __future__ import annotations

from decimal import Decimal

from core.error_codes import LOCATION_VERSION_CONFLICT, NOT_FOUND, VALIDATION_FAILED
from core.errors import IdentityAPIError
from identity.ports.authorization import PermissionAction
from locations.application.dependencies import LocationDependencies
from locations.application.dto import UpdateLocationRequest
from locations.application.evidence import EvidenceRequest, append_evidence, location_outbox_payload
from locations.domain.events import LocationEventType
from locations.domain.geofence import geofences_overlap
from locations.domain.locations import (
    Coordinates,
    LocationCandidate,
    LocationSnapshot,
    LocationWarning,
    LocationWarningDetail,
    validate_location_candidate,
)


class LocationAdminService:
    def __init__(self, dependencies: LocationDependencies) -> None:
        self._dependencies = dependencies

    def update(
        self, actor_id: int, location_id: int, request: UpdateLocationRequest
    ) -> tuple[LocationSnapshot, tuple[LocationWarningDetail, ...]]:
        self._dependencies.authorization.authorize(actor_id, PermissionAction.LOCATION_MANAGE)
        with self._dependencies.unit_of_work_factory():
            config = self._dependencies.configs.get(lock=True)
            if config is None:
                raise IdentityAPIError(NOT_FOUND, status_code=404)
            current = self._dependencies.locations.get(location_id, lock=True)
            if current is None:
                raise IdentityAPIError(NOT_FOUND, status_code=404)
            _ensure_current_version(current, request)
            candidate = _validated_candidate(current, request, config.max_radius_m)
            warnings = self._warnings(current.id, candidate, config.max_attendance_accuracy_m)
            if candidate == _candidate(current, UpdateLocationRequest(version=current.version)):
                return current, warnings
            saved = self._dependencies.locations.update(current.id, candidate, current.version + 1)
            append_evidence(
                self._dependencies.audit,
                _update_evidence(actor_id, current, saved, (request.reason, warnings)),
            )
            return saved, warnings

    def _warnings(
        self, location_id: int, candidate: LocationCandidate, accuracy_threshold: Decimal
    ) -> tuple[LocationWarningDetail, ...]:
        warnings: list[LocationWarningDetail] = []
        if candidate.radius_m < accuracy_threshold:
            warnings.append(
                LocationWarningDetail(
                    LocationWarning.RADIUS_BELOW_ATTENDANCE_ACCURACY,
                    radius_m=candidate.radius_m,
                    threshold_m=accuracy_threshold,
                )
            )
        center = Coordinates(candidate.latitude, candidate.longitude)
        related = _overlapping_locations(
            location_id, center, candidate.radius_m, self._dependencies.locations.list()
        )
        if related:
            warnings.append(
                LocationWarningDetail(
                    LocationWarning.GEOFENCE_OVERLAP,
                    tuple(item.id for item in related),
                    tuple(item.code for item in related),
                )
            )
        return tuple(sorted(warnings, key=lambda warning: warning.code.value))


def _overlapping_locations(
    location_id: int,
    center: Coordinates,
    radius_m: Decimal,
    locations: tuple[LocationSnapshot, ...],
) -> list[LocationSnapshot]:
    related = [
        other
        for other in locations
        if other.id != location_id
        and geofences_overlap(
            center,
            radius_m,
            Coordinates(other.latitude, other.longitude),
            other.radius_m,
        )
    ]
    return sorted(related, key=lambda item: (item.code, item.id))


def _candidate(current: LocationSnapshot, request: UpdateLocationRequest) -> LocationCandidate:
    return LocationCandidate(
        request.name if request.name is not None else current.name,
        request.address if request.address is not None else current.address,
        request.latitude if request.latitude is not None else current.latitude,
        request.longitude if request.longitude is not None else current.longitude,
        request.radius_m if request.radius_m is not None else current.radius_m,
        request.is_active if request.is_active is not None else current.is_active,
    )


def _ensure_current_version(current: LocationSnapshot, request: UpdateLocationRequest) -> None:
    if current.version == request.version:
        return
    details: dict[str, object] = {"current_version": current.version}
    if request.reason:
        details["submitted_reason"] = request.reason
    raise IdentityAPIError(
        LOCATION_VERSION_CONFLICT,
        status_code=409,
        details=details,
    )


def _validated_candidate(
    current: LocationSnapshot, request: UpdateLocationRequest, max_radius_m: Decimal
) -> LocationCandidate:
    candidate = _candidate(current, request)
    try:
        validate_location_candidate(candidate, max_radius_m)
    except ValueError as error:
        raise IdentityAPIError(VALIDATION_FAILED, status_code=400) from error
    return candidate


def _update_evidence(
    actor_id: int,
    current: LocationSnapshot,
    saved: LocationSnapshot,
    context: tuple[str | None, tuple[LocationWarningDetail, ...]],
) -> EvidenceRequest:
    reason, warnings = context
    after: dict[str, object] = {
        "changed_fields": _changed_fields(current, saved),
        "version": saved.version,
    }
    if reason:
        after["reason"] = reason
    after["warning_codes"] = sorted({warning.code.value for warning in warnings})
    return EvidenceRequest(
        actor_id,
        LocationEventType.LOCATION_UPDATED,
        "Location",
        saved.id,
        {"version": current.version},
        after,
        location_outbox_payload(
            saved,
            _changed_fields(current, saved),
            [warning.code.value for warning in warnings],
        ),
    )


def _changed_fields(current: LocationSnapshot, saved: LocationSnapshot) -> list[str]:
    return [
        name
        for name in ("name", "address", "latitude", "longitude", "radius_m", "is_active")
        if getattr(current, name) != getattr(saved, name)
    ]
