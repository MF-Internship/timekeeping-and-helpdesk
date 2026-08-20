from __future__ import annotations

from decimal import Decimal

from core.error_codes import PERMISSION_DENIED
from core.errors import IdentityAPIError
from identity.application.authorization import DjangoAuthorizationGateway
from identity.domain.authorization import PermissionAction, is_task_assignee_eligible
from identity.models import User
from locations.domain.geofence import (
    LocationValidationResult,
    ValidatedPosition,
    classify_geofence,
    haversine_distance_m,
)
from locations.domain.locations import Coordinates
from locations.models import Config, Location
from tasks.domain.evidence import EvidenceLocationCandidate
from tasks.domain.tasks import IdentityDisplay, LocationDisplay
from tasks.ports.assignees import AssigneeEligibility
from tasks.ports.authorization import TaskCreateMode, TaskReadScope, TaskUpdateScope
from tasks.ports.locations import EvidenceLocationContext


class DjangoTaskAuthorization:
    def __init__(self) -> None:
        self._gateway = DjangoAuthorizationGateway()

    def authorize_create(self, actor_id: int) -> TaskCreateMode:
        try:
            self._gateway.authorize(actor_id, PermissionAction.TASK_CREATE_ASSIGN)
        except IdentityAPIError as error:
            if error.error_code != PERMISSION_DENIED:
                raise
            self._gateway.authorize(actor_id, PermissionAction.TASK_CREATE_SELF)
            return TaskCreateMode.SELF
        return TaskCreateMode.ASSIGN

    def authorize_read(self, actor_id: int) -> TaskReadScope:
        result = self._gateway.authorize(actor_id, PermissionAction.TASK_VIEW_SELF)
        if result.granted_by is PermissionAction.TASK_VIEW_ALL:
            return TaskReadScope.ALL
        return TaskReadScope.SELF

    def authorize_update(self, actor_id: int) -> TaskUpdateScope:
        result = self._gateway.authorize(actor_id, PermissionAction.TASK_UPDATE_SELF)
        if result.granted_by is PermissionAction.TASK_UPDATE_ANY:
            return TaskUpdateScope.ANY
        return TaskUpdateScope.SELF

    def authorize_delete(self, actor_id: int) -> None:
        self._gateway.authorize(actor_id, PermissionAction.TASK_DELETE_SELF)

    def authorize_override(self, actor_id: int) -> None:
        self._gateway.authorize(actor_id, PermissionAction.TASK_COMPLETE_OVERRIDE)

    def authorize_field_completion(self, actor_id: int) -> None:
        self._gateway.authorize(actor_id, PermissionAction.TASK_COMPLETE_FIELD)

    def authorize_photo_read(self, actor_id: int) -> TaskReadScope:
        result = self._gateway.authorize(actor_id, PermissionAction.PHOTO_VIEW_SELF)
        if result.granted_by is PermissionAction.PHOTO_VIEW_ALL:
            return TaskReadScope.ALL
        return TaskReadScope.SELF


class DjangoAssigneeDirectory:
    def lock_eligible(self, user_ids: tuple[int, ...]) -> AssigneeEligibility:
        requested = tuple(sorted(set(user_ids)))
        rows = tuple(User.objects.select_for_update().filter(pk__in=requested).order_by("id"))
        eligible = tuple(
            IdentityDisplay(row.pk, row.full_name)
            for row in rows
            if is_task_assignee_eligible(row.role, is_active=row.is_active)
        )
        eligible_ids = {row.id for row in eligible}
        violating = tuple(user_id for user_id in requested if user_id not in eligible_ids)
        return AssigneeEligibility(eligible, violating)

    def lock_and_reauthorize_self(self, actor_id: int) -> IdentityDisplay:
        User.objects.select_for_update().filter(pk=actor_id).only("id").first()
        DjangoAuthorizationGateway().authorize(actor_id, PermissionAction.TASK_CREATE_SELF)
        actor = User.objects.only("id", "full_name").get(pk=actor_id)
        return IdentityDisplay(actor.pk, actor.full_name)


class DjangoTaskLocationDirectory:
    def get(self, location_id: int) -> LocationDisplay | None:
        model = (
            Location.objects.filter(pk=location_id)
            .only("id", "code", "name", "is_active", "address")
            .first()
        )
        if model is None:
            return None
        return LocationDisplay(model.pk, model.code, model.name, model.is_active, model.address)

    def evidence_context(self, latitude: Decimal, longitude: Decimal) -> EvidenceLocationContext:
        config = Config.objects.get(pk=1)
        position = ValidatedPosition(latitude, longitude, Decimal("0"))
        candidates: list[EvidenceLocationCandidate] = []
        for model in Location.objects.filter(is_active=True).order_by("id"):
            distance = haversine_distance_m(
                position.coordinates,
                Coordinates(model.latitude, model.longitude),
            )
            if (
                classify_geofence(distance, model.radius_m)
                is LocationValidationResult.INSIDE_GEOFENCE
            ):
                candidates.append(
                    EvidenceLocationCandidate(
                        model.pk,
                        model.code,
                        model.name,
                        Decimal(str(distance)).quantize(Decimal("0.001")),
                    )
                )
        return EvidenceLocationContext(
            config.task_gps_good_accuracy_m,
            config.task_gps_low_accuracy_m,
            tuple(candidates),
        )
