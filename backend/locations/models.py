from __future__ import annotations

from typing import Any, ClassVar

from django.db import models

from locations.domain.locations import LocationKind


class Location(models.Model):
    code: models.CharField[str, str] = models.CharField(max_length=32, unique=True)
    name: models.CharField[str, str] = models.CharField(max_length=255)
    kind: models.CharField[str, str] = models.CharField(
        max_length=32, choices=[(value.value, value.value) for value in LocationKind]
    )
    parent: models.ForeignKey[Location | None, Location | None] = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    address: models.CharField[str, str] = models.CharField(max_length=500)
    latitude: models.DecimalField[Any, Any] = models.DecimalField(max_digits=18, decimal_places=15)
    longitude: models.DecimalField[Any, Any] = models.DecimalField(max_digits=18, decimal_places=15)
    radius_m: models.DecimalField[Any, Any] = models.DecimalField(max_digits=10, decimal_places=3)
    is_active: models.BooleanField[bool, bool] = models.BooleanField(default=True, db_default=True)
    version: models.PositiveBigIntegerField[int, int] = models.PositiveBigIntegerField(
        default=1, db_default=1
    )

    class Meta:
        ordering = ("kind", "code", "id")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=~models.Q(code__regex=r"^\s*$"), name="location_code_nonblank"
            ),
            models.CheckConstraint(
                condition=~models.Q(name__regex=r"^\s*$"), name="location_name_nonblank"
            ),
            models.CheckConstraint(
                condition=~models.Q(address__regex=r"^\s*$"), name="location_address_nonblank"
            ),
            models.CheckConstraint(
                condition=models.Q(kind__in=[value.value for value in LocationKind]),
                name="location_kind_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(latitude__gte=-90, latitude__lte=90),
                name="location_latitude_range",
            ),
            models.CheckConstraint(
                condition=models.Q(longitude__gte=-180, longitude__lte=180),
                name="location_longitude_range",
            ),
            models.CheckConstraint(
                condition=models.Q(radius_m__gt=0, radius_m__lt=10_000_000),
                name="location_radius_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(version__gte=1), name="location_version_positive"
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["kind", "code"], name="location_kind_code_idx"),
            models.Index(fields=["parent"], name="location_parent_idx"),
            models.Index(fields=["is_active"], name="location_active_idx"),
        ]


class Config(models.Model):
    id: models.SmallIntegerField[int, int] = models.SmallIntegerField(primary_key=True, default=1)
    timezone: models.CharField[str, str] = models.CharField(
        max_length=64, default="Asia/Ho_Chi_Minh", db_default="Asia/Ho_Chi_Minh"
    )
    working_weekdays: models.JSONField[list[int], list[int]] = models.JSONField(
        default=list, db_default=[]
    )
    default_radius_m: models.DecimalField[Any, Any] = models.DecimalField(
        max_digits=10, decimal_places=3, default=50, db_default=50
    )
    max_radius_m: models.DecimalField[Any, Any] = models.DecimalField(
        max_digits=10, decimal_places=3, default=70, db_default=70
    )
    max_attendance_accuracy_m: models.DecimalField[Any, Any] = models.DecimalField(
        max_digits=10, decimal_places=3, default=25, db_default=25
    )
    task_gps_good_accuracy_m: models.DecimalField[Any, Any] = models.DecimalField(
        max_digits=10, decimal_places=3, default=25, db_default=25
    )
    task_gps_low_accuracy_m: models.DecimalField[Any, Any] = models.DecimalField(
        max_digits=10, decimal_places=3, default=100, db_default=100
    )
    shift_start: models.TimeField[Any, Any] = models.TimeField()
    shift_end: models.TimeField[Any, Any] = models.TimeField()
    late_grace_minutes: models.PositiveIntegerField[int, int] = models.PositiveIntegerField()
    early_checkout_grace_minutes: models.PositiveIntegerField[int, int] = (
        models.PositiveIntegerField()
    )
    late_checkout_grace_minutes: models.PositiveIntegerField[int, int] = (
        models.PositiveIntegerField(default=60, db_default=60)
    )

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(condition=models.Q(id=1), name="location_config_singleton"),
            models.CheckConstraint(
                condition=models.Q(timezone="Asia/Ho_Chi_Minh"),
                name="location_config_timezone_fixed",
            ),
            models.CheckConstraint(
                condition=models.Q(default_radius_m__gt=0, default_radius_m__lt=10_000_000),
                name="location_config_default_radius_finite",
            ),
            models.CheckConstraint(
                condition=models.Q(max_radius_m__gt=0, max_radius_m__lt=10_000_000),
                name="location_config_max_radius_finite",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    max_attendance_accuracy_m__gt=0,
                    max_attendance_accuracy_m__lt=10_000_000,
                ),
                name="location_config_attendance_accuracy_finite",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    task_gps_good_accuracy_m__gt=0,
                    task_gps_good_accuracy_m__lt=10_000_000,
                ),
                name="location_config_task_good_finite",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    task_gps_low_accuracy_m__gt=0,
                    task_gps_low_accuracy_m__lt=10_000_000,
                ),
                name="location_config_task_low_finite",
            ),
            models.CheckConstraint(
                condition=models.Q(default_radius_m__lte=models.F("max_radius_m")),
                name="location_config_default_lte_max",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    task_gps_good_accuracy_m__lte=models.F("task_gps_low_accuracy_m")
                ),
                name="location_config_task_good_lte_low",
            ),
            models.CheckConstraint(
                condition=models.Q(shift_start__lt=models.F("shift_end")),
                name="location_config_shift_order",
            ),
        ]


class Holiday(models.Model):
    date: models.DateField[Any, Any] = models.DateField(unique=True)
    name: models.CharField[str, str] = models.CharField(max_length=255)

    class Meta:
        ordering = ("date", "id")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=~models.Q(name__regex=r"^\s*$"), name="holiday_name_nonblank"
            )
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["date", "id"], name="holiday_date_id_idx")
        ]
