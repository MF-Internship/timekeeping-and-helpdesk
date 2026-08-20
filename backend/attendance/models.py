from __future__ import annotations

from typing import Any, ClassVar

from django.conf import settings
from django.db import models

from attendance.domain.attempts import AttendanceAttemptOutcome
from attendance.domain.attendance import (
    AttendanceAnomalyReason,
    AttendanceKind,
    AttendanceResolutionMethod,
    LocationValidationResult,
)


class Attendance(models.Model):
    user: models.ForeignKey[Any, Any] = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT
    )
    kind: models.CharField[str, str] = models.CharField(max_length=3)
    work_date: models.DateField[Any, Any] = models.DateField()
    recorded_at: models.DateTimeField[Any, Any] = models.DateTimeField()
    captured_at: models.DateTimeField[Any, Any] = models.DateTimeField(null=True, blank=True)
    captured_latitude: models.DecimalField[Any, Any] = models.DecimalField(
        max_digits=18, decimal_places=15
    )
    captured_longitude: models.DecimalField[Any, Any] = models.DecimalField(
        max_digits=18, decimal_places=15
    )
    accuracy_m: models.DecimalField[Any, Any] = models.DecimalField(max_digits=10, decimal_places=3)
    location: models.ForeignKey[Any, Any] = models.ForeignKey(
        "locations.Location", on_delete=models.PROTECT
    )
    distance_m: models.DecimalField[Any, Any] = models.DecimalField(max_digits=12, decimal_places=3)
    validation_result: models.CharField[str, str] = models.CharField(max_length=32)
    resolution_method: models.CharField[str, str] = models.CharField(max_length=32)
    device_metadata: models.JSONField[dict[str, object], dict[str, object]] = models.JSONField(
        default=dict, db_default={}
    )
    request_ip: models.GenericIPAddressField[Any, Any] = models.GenericIPAddressField(
        null=True, blank=True
    )

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=models.Q(kind__in=[item.value for item in AttendanceKind]),
                name="attendance_kind_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(captured_latitude__gte=-90, captured_latitude__lte=90),
                name="attendance_latitude_range",
            ),
            models.CheckConstraint(
                condition=models.Q(captured_longitude__gte=-180, captured_longitude__lte=180),
                name="attendance_longitude_range",
            ),
            models.CheckConstraint(
                condition=models.Q(accuracy_m__gte=0), name="attendance_accuracy_nonnegative"
            ),
            models.CheckConstraint(
                condition=models.Q(distance_m__gte=0), name="attendance_distance_nonnegative"
            ),
            models.CheckConstraint(
                condition=models.Q(
                    validation_result=LocationValidationResult.INSIDE_GEOFENCE.value
                ),
                name="attendance_validation_inside",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    resolution_method__in=[item.value for item in AttendanceResolutionMethod]
                ),
                name="attendance_resolution_valid",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=["user", "work_date", "recorded_at", "id"],
                name="attendance_timeline_idx",
            )
        ]


class AttendanceSession(models.Model):
    user: models.ForeignKey[Any, Any] = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT
    )
    work_date: models.DateField[Any, Any] = models.DateField()
    check_in: models.OneToOneField[Any, Any] = models.OneToOneField(
        Attendance, on_delete=models.PROTECT, related_name="opened_session"
    )
    check_out: models.OneToOneField[Any, Any] = models.OneToOneField(
        Attendance,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="closed_session",
    )
    duration_minutes: models.DecimalField[Any, Any] = models.DecimalField(
        max_digits=12, decimal_places=6, null=True, blank=True
    )
    closed_by_job: models.BooleanField[bool, bool] = models.BooleanField(
        default=False, db_default=False
    )
    created_at: models.DateTimeField[Any, Any] = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(check_out__isnull=True, closed_by_job=False),
                name="uniq_open_session_per_user",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        check_out__isnull=True,
                        duration_minutes__isnull=True,
                        closed_by_job=False,
                    )
                    | models.Q(
                        check_out__isnull=False,
                        duration_minutes__isnull=False,
                        closed_by_job=False,
                    )
                    | models.Q(
                        check_out__isnull=True,
                        duration_minutes__isnull=True,
                        closed_by_job=True,
                    )
                ),
                name="attendance_session_shape",
            ),
            models.CheckConstraint(
                condition=models.Q(duration_minutes__isnull=True)
                | models.Q(duration_minutes__gte=0),
                name="attendance_duration_nonnegative",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["user", "work_date", "id"], name="attendance_session_idx"),
            models.Index(
                fields=["work_date", "id"],
                condition=models.Q(check_out__isnull=True, closed_by_job=False),
                name="attendance_reconcile_idx",
            ),
        ]


class AttendanceAttempt(models.Model):
    user: models.ForeignKey[Any, Any] = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT
    )
    kind: models.CharField[str, str] = models.CharField(max_length=3)
    work_date: models.DateField[Any, Any] = models.DateField()
    recorded_at: models.DateTimeField[Any, Any] = models.DateTimeField()
    outcome: models.CharField[str, str] = models.CharField(max_length=32)
    attendance: models.OneToOneField[Any, Any] = models.OneToOneField(
        Attendance, null=True, blank=True, on_delete=models.PROTECT, related_name="attempt"
    )
    captured_latitude: models.DecimalField[Any, Any] = models.DecimalField(
        max_digits=18, decimal_places=15
    )
    captured_longitude: models.DecimalField[Any, Any] = models.DecimalField(
        max_digits=18, decimal_places=15
    )
    accuracy_m: models.DecimalField[Any, Any] = models.DecimalField(max_digits=10, decimal_places=3)
    nearest_location: models.ForeignKey[Any, Any] = models.ForeignKey(
        "locations.Location", null=True, blank=True, on_delete=models.PROTECT
    )
    nearest_distance_m: models.DecimalField[Any, Any] = models.DecimalField(
        max_digits=12, decimal_places=3, null=True, blank=True
    )
    candidate_count: models.PositiveSmallIntegerField[int, int] = models.PositiveSmallIntegerField(
        null=True, blank=True
    )
    device_metadata: models.JSONField[dict[str, object], dict[str, object]] = models.JSONField(
        default=dict, db_default={}
    )
    request_ip: models.GenericIPAddressField[Any, Any] = models.GenericIPAddressField(
        null=True, blank=True
    )

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=models.Q(kind__in=[item.value for item in AttendanceKind]),
                name="attendance_attempt_kind_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(outcome__in=[item.value for item in AttendanceAttemptOutcome]),
                name="attendance_attempt_outcome_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        outcome=AttendanceAttemptOutcome.ACCEPTED.value,
                        attendance__isnull=False,
                    )
                    | (
                        ~models.Q(outcome=AttendanceAttemptOutcome.ACCEPTED.value)
                        & models.Q(attendance__isnull=True)
                    )
                ),
                name="attendance_attempt_link_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(nearest_location__isnull=True, nearest_distance_m__isnull=True)
                    | models.Q(nearest_location__isnull=False, nearest_distance_m__isnull=False)
                ),
                name="attendance_attempt_nearest_pair",
            ),
            models.CheckConstraint(
                condition=models.Q(captured_latitude__gte=-90, captured_latitude__lte=90),
                name="attendance_attempt_lat_range",
            ),
            models.CheckConstraint(
                condition=models.Q(captured_longitude__gte=-180, captured_longitude__lte=180),
                name="attendance_attempt_lon_range",
            ),
            models.CheckConstraint(
                condition=models.Q(accuracy_m__gte=0), name="attendance_attempt_accuracy_nonneg"
            ),
            models.CheckConstraint(
                condition=models.Q(nearest_distance_m__isnull=True)
                | models.Q(nearest_distance_m__gte=0),
                name="attendance_attempt_distance_nonneg",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=["user", "work_date", "recorded_at", "id"],
                name="attendance_attempt_time_idx",
            ),
            models.Index(fields=["work_date", "outcome"], name="attendance_attempt_outcome_idx"),
            models.Index(
                fields=["nearest_location", "outcome"], name="attendance_attempt_nearest_idx"
            ),
        ]


class AttendanceAnomaly(models.Model):
    attendance: models.ForeignKey[Any, Any] = models.ForeignKey(
        Attendance, on_delete=models.PROTECT, related_name="anomalies"
    )
    reason: models.CharField[str, str] = models.CharField(max_length=32)
    metadata: models.JSONField[dict[str, object], dict[str, object]] = models.JSONField(
        default=dict, db_default={}
    )
    created_at: models.DateTimeField[Any, Any] = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["attendance", "reason"], name="attendance_anomaly_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(reason__in=[item.value for item in AttendanceAnomalyReason]),
                name="attendance_anomaly_reason_valid",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["reason", "created_at", "id"], name="attendance_anomaly_idx")
        ]
