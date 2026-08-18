from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from rest_framework import serializers

from attendance.adapters.api.maps import attendance_maps_url
from attendance.application.dto import CommandResult, TodayAttendance
from attendance.domain.attendance import LocationMatch
from core.error_codes import SERVER_OWNED_FIELD
from core.errors import IdentityAPIError


class AttendanceCommandSerializer(serializers.Serializer[Any]):
    allowed_fields = frozenset(
        {"latitude", "longitude", "accuracy_m", "captured_at", "selected_location_id"}
    )
    latitude = serializers.DecimalField(
        max_digits=18, decimal_places=15, min_value=-90, max_value=90
    )
    longitude = serializers.DecimalField(
        max_digits=18, decimal_places=15, min_value=-180, max_value=180
    )
    accuracy_m = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=0)
    captured_at = serializers.DateTimeField(required=False, allow_null=True)
    selected_location_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if isinstance(data, dict) and set(data) - self.allowed_fields:
            raise IdentityAPIError(SERVER_OWNED_FIELD, status_code=400)
        return super().to_internal_value(data)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        captured_at = attrs.get("captured_at")
        receipt_time = self.context.get("receipt_time")
        if (
            captured_at is not None
            and isinstance(receipt_time, datetime)
            and receipt_time - captured_at > timedelta(seconds=60)
        ):
            raise serializers.ValidationError({"captured_at": ["Mẫu GPS đã quá hạn."]})
        return attrs


class AttendanceLocationSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField(read_only=True)
    code = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    address = serializers.CharField(read_only=True)


class LocationCandidateSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField(source="location.id", read_only=True)
    code = serializers.CharField(source="location.code", read_only=True)
    name = serializers.CharField(source="location.name", read_only=True)
    distance_m = serializers.DecimalField(max_digits=12, decimal_places=3, read_only=True)


class AttendanceErrorSerializer(serializers.Serializer[Any]):
    error_code = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)
    details = serializers.DictField(read_only=True)
    request_id = serializers.UUIDField(read_only=True)
    error = serializers.CharField(read_only=True)


class SessionAlreadyOpenErrorSerializer(AttendanceErrorSerializer):
    error_code = serializers.ChoiceField(  # type: ignore[assignment]
        choices=["SESSION_ALREADY_OPEN"], read_only=True
    )


class NoOpenSessionErrorSerializer(AttendanceErrorSerializer):
    error_code = serializers.ChoiceField(  # type: ignore[assignment]
        choices=["NO_OPEN_SESSION"], read_only=True
    )


class GpsBoundaryErrorSerializer(AttendanceErrorSerializer):
    error_code = serializers.ChoiceField(  # type: ignore[assignment]
        choices=["WEAK_GPS", "OUTSIDE_RADIUS"], read_only=True
    )


class LocationChoiceRequiredErrorSerializer(AttendanceErrorSerializer):
    error_code = serializers.ChoiceField(  # type: ignore[assignment]
        choices=["LOCATION_CHOICE_REQUIRED"], read_only=True
    )
    location_candidates = serializers.ListField(
        child=LocationCandidateSerializer(), min_length=2, read_only=True
    )


class InvalidLocationChoiceErrorSerializer(AttendanceErrorSerializer):
    error_code = serializers.ChoiceField(  # type: ignore[assignment]
        choices=["INVALID_LOCATION_CHOICE"], read_only=True
    )
    location_candidates = serializers.ListField(
        child=LocationCandidateSerializer(), min_length=1, read_only=True
    )


class AttendanceSessionSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField(read_only=True)
    work_date = serializers.DateField(read_only=True)
    check_in_at = serializers.DateTimeField(read_only=True)
    check_out_at = serializers.DateTimeField(read_only=True, allow_null=True)
    check_in_location_id = serializers.IntegerField(read_only=True)
    check_out_location_id = serializers.IntegerField(read_only=True, allow_null=True)
    duration_minutes = serializers.DecimalField(
        max_digits=14, decimal_places=6, read_only=True, allow_null=True
    )
    closed_by_job = serializers.BooleanField(read_only=True)


class AttendancePunchSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField(read_only=True)
    kind = serializers.CharField(read_only=True)
    work_date = serializers.DateField(read_only=True)
    recorded_at = serializers.DateTimeField(read_only=True)
    captured_at = serializers.DateTimeField(read_only=True, allow_null=True)
    captured_latitude = serializers.DecimalField(max_digits=18, decimal_places=15, read_only=True)
    captured_longitude = serializers.DecimalField(max_digits=18, decimal_places=15, read_only=True)
    accuracy_m = serializers.DecimalField(max_digits=10, decimal_places=3, read_only=True)
    location = AttendanceLocationSerializer(read_only=True)
    distance_m = serializers.DecimalField(max_digits=12, decimal_places=3, read_only=True)
    validation_result = serializers.CharField(read_only=True)
    resolution_method = serializers.CharField(read_only=True)
    maps_url = serializers.SerializerMethodField()
    resolved_address = serializers.CharField(source="location.address", read_only=True)

    def get_maps_url(self, value: Any) -> str:
        return attendance_maps_url(value.captured_latitude, value.captured_longitude)


class AttendanceCommandResultSerializer(serializers.Serializer[Any]):
    attendance = AttendancePunchSerializer(read_only=True)
    session = AttendanceSessionSerializer(read_only=True)
    punch_index = serializers.IntegerField(read_only=True, min_value=1)


class IndexedAttendancePunchSerializer(AttendancePunchSerializer):
    punch_index = serializers.IntegerField(read_only=True, min_value=1)


class TodayAttendanceSerializer(serializers.Serializer[Any]):
    work_date = serializers.DateField(read_only=True)
    punches = IndexedAttendancePunchSerializer(many=True, read_only=True)
    sessions = AttendanceSessionSerializer(many=True, read_only=True)
    total_duration_minutes = serializers.DecimalField(
        max_digits=14, decimal_places=6, read_only=True
    )
    has_open_session = serializers.BooleanField(read_only=True)


def command_result_payload(result: CommandResult) -> dict[str, Any]:
    return AttendanceCommandResultSerializer(result).data


def today_payload(result: TodayAttendance) -> dict[str, Any]:
    return {
        "work_date": result.work_date.isoformat(),
        "punches": [
            {**AttendancePunchSerializer(item.attendance).data, "punch_index": item.punch_index}
            for item in result.punches
        ],
        "sessions": AttendanceSessionSerializer(result.sessions, many=True).data,
        "total_duration_minutes": f"{result.total_duration_minutes:.6f}",
        "has_open_session": result.has_open_session,
    }


def candidate_payload(values: tuple[LocationMatch, ...]) -> list[dict[str, Any]]:
    return list(LocationCandidateSerializer(values, many=True).data)
