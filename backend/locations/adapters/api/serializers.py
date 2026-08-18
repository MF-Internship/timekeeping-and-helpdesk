from __future__ import annotations

from typing import Any

from rest_framework import serializers

from core.error_codes import SERVER_OWNED_FIELD
from core.errors import IdentityAPIError
from locations.domain.locations import LocationKind, LocationWarning


class StrictSerializer(serializers.Serializer[Any]):
    allowed_fields: frozenset[str] = frozenset()

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if isinstance(data, dict) and set(data) - self.allowed_fields:
            raise IdentityAPIError(SERVER_OWNED_FIELD, status_code=400)
        return super().to_internal_value(data)


class LocationSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField(read_only=True)
    code = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    kind = serializers.CharField(read_only=True)
    parent_id = serializers.IntegerField(read_only=True, allow_null=True)
    parent_code = serializers.CharField(read_only=True, allow_null=True)
    address = serializers.CharField(read_only=True)
    latitude = serializers.DecimalField(read_only=True, max_digits=18, decimal_places=15)
    longitude = serializers.DecimalField(read_only=True, max_digits=18, decimal_places=15)
    radius_m = serializers.DecimalField(read_only=True, max_digits=10, decimal_places=3)
    is_active = serializers.BooleanField(read_only=True)
    version = serializers.IntegerField(read_only=True)


class LocationUpdateSerializer(StrictSerializer):
    allowed_fields = frozenset(
        {"version", "name", "address", "latitude", "longitude", "radius_m", "is_active", "reason"}
    )
    version = serializers.IntegerField(min_value=1)
    name = serializers.CharField(required=False, allow_blank=False)
    address = serializers.CharField(required=False, allow_blank=False)
    latitude = serializers.DecimalField(required=False, max_digits=18, decimal_places=15)
    longitude = serializers.DecimalField(required=False, max_digits=18, decimal_places=15)
    radius_m = serializers.DecimalField(required=False, max_digits=10, decimal_places=3)
    is_active = serializers.BooleanField(required=False)
    reason = serializers.CharField(required=False, allow_blank=False, max_length=500)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        mutable = set(attrs) - {"version", "reason"}
        if not mutable:
            raise serializers.ValidationError({"non_field_errors": ["Cần trường thay đổi."]})
        return attrs


class ConfigSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField(read_only=True)
    timezone = serializers.CharField(read_only=True)
    working_weekdays = serializers.ListField(child=serializers.IntegerField(), read_only=True)
    default_radius_m = serializers.DecimalField(read_only=True, max_digits=10, decimal_places=3)
    max_radius_m = serializers.DecimalField(read_only=True, max_digits=10, decimal_places=3)
    max_attendance_accuracy_m = serializers.DecimalField(
        read_only=True, max_digits=10, decimal_places=3
    )
    task_gps_good_accuracy_m = serializers.DecimalField(
        read_only=True, max_digits=10, decimal_places=3
    )
    task_gps_low_accuracy_m = serializers.DecimalField(
        read_only=True, max_digits=10, decimal_places=3
    )
    shift_start = serializers.TimeField(read_only=True)
    shift_end = serializers.TimeField(read_only=True)
    late_grace_minutes = serializers.IntegerField(read_only=True)
    early_checkout_grace_minutes = serializers.IntegerField(read_only=True)
    late_checkout_grace_minutes = serializers.IntegerField(read_only=True)


class ConfigUpdateSerializer(StrictSerializer):
    allowed_fields = frozenset(
        {
            "working_weekdays",
            "default_radius_m",
            "max_radius_m",
            "max_attendance_accuracy_m",
            "task_gps_good_accuracy_m",
            "task_gps_low_accuracy_m",
            "shift_start",
            "shift_end",
            "late_grace_minutes",
            "early_checkout_grace_minutes",
            "late_checkout_grace_minutes",
        }
    )
    working_weekdays = serializers.ListField(child=serializers.IntegerField(), required=False)
    default_radius_m = serializers.DecimalField(required=False, max_digits=10, decimal_places=3)
    max_radius_m = serializers.DecimalField(required=False, max_digits=10, decimal_places=3)
    max_attendance_accuracy_m = serializers.DecimalField(
        required=False, max_digits=10, decimal_places=3
    )
    task_gps_good_accuracy_m = serializers.DecimalField(
        required=False, max_digits=10, decimal_places=3
    )
    task_gps_low_accuracy_m = serializers.DecimalField(
        required=False, max_digits=10, decimal_places=3
    )
    shift_start = serializers.TimeField(required=False)
    shift_end = serializers.TimeField(required=False)
    late_grace_minutes = serializers.IntegerField(required=False, min_value=0)
    early_checkout_grace_minutes = serializers.IntegerField(required=False, min_value=0)
    late_checkout_grace_minutes = serializers.IntegerField(required=False, min_value=0)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if not attrs:
            raise serializers.ValidationError({"non_field_errors": ["Cần ít nhất một trường."]})
        return attrs


class HolidaySerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField(read_only=True)
    date = serializers.DateField(read_only=True)
    name = serializers.CharField(read_only=True)


class HolidayCreateSerializer(StrictSerializer):
    allowed_fields = frozenset({"date", "name"})
    date = serializers.DateField()
    name = serializers.CharField(allow_blank=False, max_length=255)


class WarningSerializer(serializers.Serializer[Any]):
    code = serializers.ChoiceField(
        choices=[value.value for value in LocationWarning], read_only=True
    )
    related_location_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    related_location_codes = serializers.ListField(child=serializers.CharField(), required=False)
    radius_m = serializers.DecimalField(max_digits=10, decimal_places=3, required=False)
    threshold_m = serializers.DecimalField(max_digits=10, decimal_places=3, required=False)

    def to_representation(self, instance: Any) -> dict[str, Any]:
        representation = super().to_representation(instance)
        return {
            key: value for key, value in representation.items() if value is not None and value != []
        }


class LocationUpdateResultSerializer(serializers.Serializer[Any]):
    location = LocationSerializer(read_only=True)
    warnings = WarningSerializer(many=True, read_only=True)


class ConfigUpdateResultSerializer(serializers.Serializer[Any]):
    config = ConfigSerializer(read_only=True)
    warnings = WarningSerializer(many=True, read_only=True)


def validate_kind(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return LocationKind(value).value
    except ValueError as error:
        raise serializers.ValidationError({"kind": ["Giá trị không hợp lệ."]}) from error
