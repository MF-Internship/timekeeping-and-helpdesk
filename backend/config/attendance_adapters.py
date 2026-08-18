from decimal import Decimal

from attendance.application.dto import ConfigSnapshot, ReferenceSnapshot
from attendance.domain.attendance import LocationSnapshot, decimal_distance
from identity.application.authorization import DjangoAuthorizationGateway
from identity.domain.authorization import PermissionAction
from locations.domain.geofence import haversine_distance_m
from locations.domain.locations import Coordinates
from locations.models import Config, Location


class DjangoAttendanceAuthorization:
    def __init__(self) -> None:
        self._gateway = DjangoAuthorizationGateway()

    def authorize_check_in(self, actor_id: int) -> None:
        self._gateway.authorize(actor_id, PermissionAction.ATTENDANCE_CHECK_IN_SELF)

    def authorize_check_out(self, actor_id: int) -> None:
        self._gateway.authorize(actor_id, PermissionAction.ATTENDANCE_CHECK_OUT_SELF)

    def authorize_view_self(self, actor_id: int) -> None:
        self._gateway.authorize(actor_id, PermissionAction.ATTENDANCE_VIEW_SELF)


class DjangoAttendanceReferenceData:
    def load_locked(self) -> ReferenceSnapshot:
        config = Config.objects.select_for_update().get(pk=1)
        rows = tuple(Location.objects.order_by("code", "id"))
        if len(rows) != 76:
            raise RuntimeError("attendance reference data is not ready")
        return ReferenceSnapshot(
            _config_snapshot(config), tuple(_location_snapshot(row) for row in rows)
        )

    def distance_m(
        self, latitude: Decimal, longitude: Decimal, location: LocationSnapshot
    ) -> Decimal:
        value = haversine_distance_m(
            Coordinates(latitude, longitude), Coordinates(location.latitude, location.longitude)
        )
        return decimal_distance(value)


def _config_snapshot(model: Config) -> ConfigSnapshot:
    return ConfigSnapshot(
        model.max_attendance_accuracy_m,
        model.timezone,
        model.shift_start,
        model.shift_end,
        model.late_grace_minutes,
        model.early_checkout_grace_minutes,
        model.late_checkout_grace_minutes,
    )


def _location_snapshot(model: Location) -> LocationSnapshot:
    return LocationSnapshot(
        model.pk,
        model.code,
        model.name,
        model.address,
        model.latitude,
        model.longitude,
        model.radius_m,
        model.is_active,
    )
