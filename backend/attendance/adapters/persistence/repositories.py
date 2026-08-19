from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from django.db.models import QuerySet, Sum

from attendance.application.dto import (
    AcceptedPunchRequest,
    AttendanceSnapshot,
    SessionProjection,
)
from attendance.domain.attendance import (
    AttendanceAnomalyReason,
    AttendanceKind,
    AttendanceResolutionMethod,
    LocationSnapshot,
    LocationValidationResult,
)
from attendance.domain.sessions import SessionSnapshot, duration_minutes
from attendance.models import Attendance, AttendanceAnomaly, AttendanceSession


def _location_snapshot(model: Any) -> LocationSnapshot:
    return LocationSnapshot(
        id=model.pk,
        code=model.code,
        name=model.name,
        address=model.address,
        latitude=model.latitude,
        longitude=model.longitude,
        radius_m=model.radius_m,
        is_active=model.is_active,
    )


def attendance_snapshot(model: Attendance) -> AttendanceSnapshot:
    return AttendanceSnapshot(
        model.pk,
        model.user_id,  # type: ignore[attr-defined]
        AttendanceKind(model.kind),
        model.work_date,
        model.recorded_at,
        model.captured_at,
        model.captured_latitude,
        model.captured_longitude,
        model.accuracy_m,
        _location_snapshot(model.location),
        model.distance_m,
        LocationValidationResult(model.validation_result),
        AttendanceResolutionMethod(model.resolution_method),
    )


def session_snapshot(model: AttendanceSession) -> SessionSnapshot:
    return SessionSnapshot(
        model.pk,
        model.user_id,  # type: ignore[attr-defined]
        model.work_date,
        model.check_in_id,  # type: ignore[attr-defined]
        model.check_out_id,  # type: ignore[attr-defined]
        model.duration_minutes,
        model.closed_by_job,
    )


def session_projection(model: AttendanceSession) -> SessionProjection:
    check_out = model.check_out
    return SessionProjection(
        model.pk,
        model.work_date,
        model.check_in.recorded_at,
        check_out.recorded_at if check_out else None,
        model.check_in.location_id,
        check_out.location_id if check_out else None,
        model.duration_minutes,
        model.closed_by_job,
    )


class DjangoAttendanceRepository:
    def open_session(self, user_id: int, *, lock: bool = False) -> SessionSnapshot | None:
        query = AttendanceSession.objects.filter(
            user_id=user_id, check_out__isnull=True, closed_by_job=False
        )
        if lock:
            query = query.select_for_update()
        model = query.first()
        return session_snapshot(model) if model else None

    def create_attendance(self, request: AcceptedPunchRequest) -> AttendanceSnapshot:
        match = request.match
        model = Attendance.objects.create(
            user_id=request.user_id,
            kind=request.kind.value,
            work_date=request.work_date,
            recorded_at=request.recorded_at,
            captured_at=request.command.captured_at,
            captured_latitude=request.command.latitude,
            captured_longitude=request.command.longitude,
            accuracy_m=request.command.accuracy_m,
            location_id=match.location.id,
            distance_m=match.distance_m,
            validation_result=LocationValidationResult.INSIDE_GEOFENCE.value,
            resolution_method=request.resolution.value,
            device_metadata=request.command.device_metadata or {},
            request_ip=request.command.request_ip,
        )
        return attendance_snapshot(Attendance.objects.select_related("location").get(pk=model.pk))

    def open_new_session(self, attendance: AttendanceSnapshot) -> SessionProjection:
        model = AttendanceSession.objects.create(
            user_id=attendance.user_id,
            work_date=attendance.work_date,
            check_in_id=attendance.id,
        )
        return self._projection(model.pk)

    def close_session(
        self, session: SessionSnapshot, attendance: AttendanceSnapshot
    ) -> SessionProjection:
        model = AttendanceSession.objects.select_related("check_in").get(pk=session.id)
        model.check_out_id = attendance.id  # type: ignore[attr-defined]
        model.duration_minutes = duration_minutes(
            model.check_in.recorded_at, attendance.recorded_at
        )
        model.save(update_fields=["check_out", "duration_minutes"])
        return self._projection(model.pk)

    def punches(self, user_id: int, work_date: date) -> tuple[AttendanceSnapshot, ...]:
        query = Attendance.objects.select_related("location").filter(
            user_id=user_id, work_date=work_date
        )
        return tuple(attendance_snapshot(item) for item in query.order_by("recorded_at", "id"))

    def sessions(self, user_id: int, work_date: date) -> tuple[SessionProjection, ...]:
        query = self._session_query().filter(user_id=user_id, work_date=work_date)
        return tuple(session_projection(item) for item in query.order_by("id"))

    def replace_anomalies(
        self,
        attendance_id: int,
        removable_reasons: tuple[AttendanceAnomalyReason, ...],
        reasons: tuple[AttendanceAnomalyReason, ...],
    ) -> None:
        AttendanceAnomaly.objects.filter(
            attendance_id=attendance_id,
            reason__in=[reason.value for reason in removable_reasons],
        ).delete()
        AttendanceAnomaly.objects.bulk_create(
            [
                AttendanceAnomaly(attendance_id=attendance_id, reason=reason.value, metadata={})
                for reason in reasons
            ]
        )

    def total_duration(self, user_id: int, work_date: date) -> Decimal:
        result = AttendanceSession.objects.filter(
            user_id=user_id,
            work_date=work_date,
            check_out__isnull=False,
            closed_by_job=False,
        ).aggregate(total=Sum("duration_minutes"))["total"]
        return result or Decimal("0.000000")

    def _projection(self, session_id: int) -> SessionProjection:
        return session_projection(self._session_query().get(pk=session_id))

    @staticmethod
    def _session_query() -> QuerySet[AttendanceSession]:
        return AttendanceSession.objects.select_related(
            "check_in", "check_in__location", "check_out", "check_out__location"
        )
