from __future__ import annotations

from datetime import date

from django.db.models import QuerySet

from locations.domain.config import ConfigSnapshot
from locations.domain.holidays import HolidaySnapshot
from locations.domain.locations import LocationCandidate, LocationKind, LocationSnapshot
from locations.models import Config, Holiday, Location


def location_snapshot(model: Location) -> LocationSnapshot:
    parent = model.parent
    return LocationSnapshot(
        model.pk,
        model.code,
        model.name,
        LocationKind(model.kind),
        parent.pk if parent is not None else None,
        parent.code if parent is not None else None,
        model.address,
        model.latitude,
        model.longitude,
        model.radius_m,
        model.is_active,
        model.version,
    )


def config_snapshot(model: Config) -> ConfigSnapshot:
    return ConfigSnapshot(
        model.pk,
        model.timezone,
        tuple(model.working_weekdays),
        model.default_radius_m,
        model.max_radius_m,
        model.max_attendance_accuracy_m,
        model.task_gps_good_accuracy_m,
        model.task_gps_low_accuracy_m,
        model.shift_start,
        model.shift_end,
        model.late_grace_minutes,
        model.early_checkout_grace_minutes,
        model.late_checkout_grace_minutes,
    )


def holiday_snapshot(model: Holiday) -> HolidaySnapshot:
    return HolidaySnapshot(model.pk, model.date, model.name)


class DjangoLocationRepository:
    def _query(self, lock: bool = False) -> QuerySet[Location]:
        query = Location.objects.select_related("parent")
        # ``parent`` is nullable, so PostgreSQL rejects an unrestricted
        # ``FOR UPDATE`` across the outer join. Only the Location row owns the
        # mutable state and optimistic version guarded by this lock.
        return query.select_for_update(of=("self",)) if lock else query

    def list(
        self,
        *,
        kind: str | None = None,
        parent_id: int | None = None,
        is_active: bool | None = None,
    ) -> tuple[LocationSnapshot, ...]:
        query = self._query()
        if kind is not None:
            query = query.filter(kind=kind)
        if parent_id is not None:
            query = query.filter(parent_id=parent_id)
        if is_active is not None:
            query = query.filter(is_active=is_active)
        return tuple(location_snapshot(item) for item in query.order_by("kind", "code", "id"))

    def get(self, location_id: int, *, lock: bool = False) -> LocationSnapshot | None:
        model = self._query(lock).filter(pk=location_id).first()
        return location_snapshot(model) if model else None

    def all_by_code(self, *, lock: bool = False) -> dict[str, LocationSnapshot]:
        return {item.code: location_snapshot(item) for item in self._query(lock).order_by("id")}

    def create_source(self, values: dict[str, object]) -> LocationSnapshot:
        return location_snapshot(Location.objects.create(**values))

    def reconcile_source(
        self, code: str, values: dict[str, object], version: int
    ) -> LocationSnapshot:
        Location.objects.filter(code=code).update(**values, version=version)
        return location_snapshot(self._query().get(code=code))

    def set_parent(self, code: str, parent_code: str | None) -> LocationSnapshot:
        parent_id = None
        if parent_code is not None:
            parent_id = (
                Location.objects.filter(code=parent_code).values_list("id", flat=True).first()
            )
        model = self._query().get(code=code)
        if model.parent_id != parent_id:  # type: ignore[attr-defined]
            Location.objects.filter(code=code).update(parent_id=parent_id)
            model = self._query().get(code=code)
        return location_snapshot(model)

    def update(
        self, location_id: int, candidate: LocationCandidate, version: int
    ) -> LocationSnapshot:
        model = Location.objects.select_related("parent").get(pk=location_id)
        model.name = candidate.name
        model.address = candidate.address
        model.latitude = candidate.latitude
        model.longitude = candidate.longitude
        model.radius_m = candidate.radius_m
        model.is_active = candidate.is_active
        model.version = version
        model.save(
            update_fields=[
                "name",
                "address",
                "latitude",
                "longitude",
                "radius_m",
                "is_active",
                "version",
            ]
        )
        return location_snapshot(model)


class DjangoConfigRepository:
    def get(self, *, lock: bool = False) -> ConfigSnapshot | None:
        query = Config.objects.select_for_update() if lock else Config.objects
        model = query.filter(pk=1).first()
        return config_snapshot(model) if model else None

    def create(self, config: ConfigSnapshot) -> ConfigSnapshot:
        model = Config.objects.create(**_config_values(config))
        return config_snapshot(model)

    def update(self, config: ConfigSnapshot) -> ConfigSnapshot:
        Config.objects.filter(pk=1).update(**_config_values(config))
        return config_snapshot(Config.objects.get(pk=1))


def _config_values(config: ConfigSnapshot) -> dict[str, object]:
    return {
        "id": 1,
        "timezone": config.timezone,
        "working_weekdays": list(config.working_weekdays),
        "default_radius_m": config.default_radius_m,
        "max_radius_m": config.max_radius_m,
        "max_attendance_accuracy_m": config.max_attendance_accuracy_m,
        "task_gps_good_accuracy_m": config.task_gps_good_accuracy_m,
        "task_gps_low_accuracy_m": config.task_gps_low_accuracy_m,
        "shift_start": config.shift_start,
        "shift_end": config.shift_end,
        "late_grace_minutes": config.late_grace_minutes,
        "early_checkout_grace_minutes": config.early_checkout_grace_minutes,
        "late_checkout_grace_minutes": config.late_checkout_grace_minutes,
    }


class DjangoHolidayRepository:
    def list(self) -> tuple[HolidaySnapshot, ...]:
        return tuple(holiday_snapshot(item) for item in Holiday.objects.order_by("date", "id"))

    def create(self, value_date: date, name: str) -> HolidaySnapshot:
        return holiday_snapshot(Holiday.objects.create(date=value_date, name=name))

    def get(self, holiday_id: int, *, lock: bool = False) -> HolidaySnapshot | None:
        query = Holiday.objects.select_for_update() if lock else Holiday.objects
        model = query.filter(pk=holiday_id).first()
        return holiday_snapshot(model) if model else None

    def delete(self, holiday_id: int) -> None:
        Holiday.objects.filter(pk=holiday_id).delete()
