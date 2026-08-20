from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlencode

from rest_framework import serializers

from core.error_codes import SERVER_OWNED_FIELD
from core.errors import IdentityAPIError
from tasks.application.queries import GroupedTaskListProjection, TaskItemProjection
from tasks.domain.tasks import (
    IdentityDisplay,
    LocationDisplay,
    TaskReadSnapshot,
    TaskStatus,
    TaskUpdateSnapshot,
)

ORDINARY_TASK_STATUS_CHOICES = tuple(
    (value.value, value.value)
    for value in (TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED)
)


class TaskCreateSerializer(serializers.Serializer[Any]):
    title = serializers.CharField(allow_blank=False, trim_whitespace=True)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    assigned_date = serializers.DateField()
    location_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    expected_location = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=500, trim_whitespace=True
    )
    assignee_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, allow_empty=False
    )


class TaskUpdateSerializer(serializers.Serializer[Any]):
    title = serializers.CharField(required=False, allow_blank=False, trim_whitespace=True)
    description = serializers.CharField(required=False, allow_blank=True)
    location_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    expected_location = serializers.CharField(
        required=False, allow_blank=True, max_length=500, trim_whitespace=True
    )
    assignee_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, allow_empty=False
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if not attrs:
            raise serializers.ValidationError({"non_field_errors": ["empty update"]})
        return attrs


class TaskStatusSerializer(serializers.Serializer[Any]):
    status = serializers.ChoiceField(choices=ORDINARY_TASK_STATUS_CHOICES)
    note = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    block_reason = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class TaskOverrideSerializer(serializers.Serializer[Any]):
    completion_note = serializers.CharField(allow_blank=False, trim_whitespace=True)


class EvidenceUploadSerializer(serializers.Serializer[Any]):
    mime = serializers.ChoiceField(choices=("image/jpeg", "image/png", "image/webp"))
    size_bytes = serializers.IntegerField(min_value=1, max_value=5 * 1024 * 1024)
    checksum_sha256 = serializers.RegexField(r"^[0-9a-f]{64}$")


class EvidenceUploadIntentSerializer(serializers.Serializer[Any]):
    upload_id = serializers.UUIDField()
    upload_url = serializers.URLField()
    headers = serializers.DictField(child=serializers.CharField())
    expires_at = serializers.DateTimeField()


class TaskFieldCompletionSerializer(serializers.Serializer[Any]):
    upload_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1, max_length=5, allow_empty=False
    )
    latitude = serializers.DecimalField(
        max_digits=18, decimal_places=15, min_value=-90, max_value=90
    )
    longitude = serializers.DecimalField(
        max_digits=18, decimal_places=15, min_value=-180, max_value=180
    )
    accuracy_m = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=0)
    captured_at = serializers.DateTimeField()
    selected_location_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    completion_note = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class PhotoAccessSerializer(serializers.Serializer[Any]):
    url = serializers.URLField()
    expires_at = serializers.DateTimeField()


class TaskUserSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    full_name = serializers.CharField()


class TaskPhotoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    mime = serializers.ChoiceField(choices=("image/jpeg", "image/png", "image/webp"))
    size_bytes = serializers.IntegerField(min_value=1)


class TaskLocationSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    code = serializers.CharField()
    name = serializers.CharField()
    is_active = serializers.BooleanField()
    address = serializers.CharField(allow_blank=True)


class TaskAssigneeSerializer(serializers.Serializer[Any]):
    user = TaskUserSerializer()
    assigned_at = serializers.DateTimeField()


class TaskLifecycleUpdateSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    actor = TaskUserSerializer()
    status = serializers.ChoiceField(choices=[value.value for value in TaskStatus])
    recorded_at = serializers.DateTimeField()
    note = serializers.CharField(allow_null=True)
    block_reason = serializers.CharField(allow_null=True)
    completion_method = serializers.CharField(allow_null=True)
    completion_note = serializers.CharField(allow_null=True)
    captured_latitude = serializers.CharField(allow_null=True)
    captured_longitude = serializers.CharField(allow_null=True)
    accuracy_m = serializers.CharField(allow_null=True)
    captured_at = serializers.DateTimeField(allow_null=True)
    gps_quality = serializers.CharField(allow_null=True)
    actual_location_id = serializers.IntegerField(allow_null=True)
    actual_location = TaskLocationSerializer(allow_null=True)
    validation_result = serializers.CharField(allow_null=True)
    resolution_method = serializers.CharField(allow_null=True)
    distance_m = serializers.CharField(allow_null=True)
    location_candidates = serializers.ListField(child=serializers.IntegerField())
    photos = TaskPhotoSerializer(many=True)
    resolved_address = serializers.CharField(allow_null=True)
    maps_url = serializers.URLField(allow_null=True)


class TaskItemSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    title = serializers.CharField()
    description = serializers.CharField()
    created_by = TaskUserSerializer()
    assigned_date = serializers.DateField()
    status = serializers.ChoiceField(choices=[value.value for value in TaskStatus])
    location = TaskLocationSerializer(allow_null=True)
    expected_location = serializers.CharField(allow_blank=True)
    assignees = TaskAssigneeSerializer(many=True)
    completed_by = TaskUserSerializer(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)
    completion_method = serializers.CharField(allow_null=True)
    completion_note = serializers.CharField(allow_null=True)
    block_reason = serializers.CharField(allow_null=True)
    group = serializers.CharField()
    overdue_days = serializers.IntegerField(allow_null=True)


class TaskDetailSerializer(TaskItemSerializer):
    updates = TaskLifecycleUpdateSerializer(many=True)


class GroupedTaskListSerializer(serializers.Serializer[Any]):
    business_date = serializers.DateField()
    overdue = TaskItemSerializer(many=True)
    today = TaskItemSerializer(many=True)
    upcoming = TaskItemSerializer(many=True)
    completed = TaskItemSerializer(many=True)


class TaskErrorSerializer(serializers.Serializer[Any]):
    error_code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.DictField()
    request_id = serializers.UUIDField()
    error = serializers.CharField()


class InactiveAssigneeDetailsSerializer(serializers.Serializer[Any]):
    assignee_ids = serializers.ListField(child=serializers.IntegerField())


class InactiveAssigneeErrorSerializer(serializers.Serializer[Any]):
    error_code = serializers.ChoiceField(choices=("INACTIVE_ASSIGNEE",))
    message = serializers.CharField()
    details = InactiveAssigneeDetailsSerializer()
    request_id = serializers.UUIDField()
    error = serializers.CharField()


class TaskAlreadyCompletedErrorSerializer(serializers.Serializer[Any]):
    error_code = serializers.ChoiceField(choices=("TASK_ALREADY_COMPLETED",))
    message = serializers.CharField()
    details = serializers.DictField()
    request_id = serializers.UUIDField()
    error = serializers.CharField()


def reject_owned_fields(
    data: object,
    *,
    allowed: frozenset[str],
    owned: frozenset[str],
) -> None:
    if not isinstance(data, Mapping):
        return
    supplied = {str(key) for key in data}
    forbidden = sorted(supplied & owned)
    if forbidden:
        raise IdentityAPIError(
            SERVER_OWNED_FIELD,
            status_code=400,
            details={"fields": forbidden},
        )
    unknown = sorted(supplied - allowed)
    if unknown:
        raise serializers.ValidationError({"fields": unknown})


def task_payload(item: TaskItemProjection, *, include_updates: bool) -> dict[str, object]:
    record = item.record
    task = record.task
    payload: dict[str, object] = {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "created_by": _user_payload(record.created_by),
        "assigned_date": task.assigned_date.isoformat(),
        "status": task.status.value,
        "location": _location_payload(record.location),
        "expected_location": (
            task.expected_location_text or _legacy_expected_location(record.location)
        ),
        "assignees": [
            {"user": _user_payload(link.user), "assigned_at": link.assigned_at.isoformat()}
            for link in record.assignees
        ],
        "completed_by": _user_payload(record.completed_by),
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "completion_method": task.completion_method.value if task.completion_method else None,
        "completion_note": task.completion_note,
        "block_reason": task.block_reason,
        "group": item.group.value,
        "overdue_days": item.overdue_days,
    }
    if include_updates:
        payload["updates"] = _updates_payload(record)
    return payload


def grouped_payload(projection: GroupedTaskListProjection) -> dict[str, object]:
    return {
        "business_date": projection.business_date.isoformat(),
        "overdue": [task_payload(item, include_updates=False) for item in projection.overdue],
        "today": [task_payload(item, include_updates=False) for item in projection.today],
        "upcoming": [task_payload(item, include_updates=False) for item in projection.upcoming],
        "completed": [task_payload(item, include_updates=False) for item in projection.completed],
    }


def _updates_payload(record: TaskReadSnapshot) -> list[dict[str, object]]:
    return [_update_payload(update, actor) for update, actor in record.updates]


def _update_payload(update: TaskUpdateSnapshot, actor: IdentityDisplay) -> dict[str, object]:
    return {
        "id": update.id,
        "actor": _user_payload(actor),
        "status": update.status.value,
        "recorded_at": update.recorded_at.isoformat(),
        "note": update.note,
        "block_reason": update.block_reason,
        "completion_method": update.completion_method.value if update.completion_method else None,
        "completion_note": update.completion_note,
        **_update_evidence_payload(update),
    }


def _update_evidence_payload(update: TaskUpdateSnapshot) -> dict[str, object]:
    return {
        "captured_latitude": update.captured_latitude,
        "captured_longitude": update.captured_longitude,
        "accuracy_m": update.accuracy_m,
        "captured_at": update.captured_at.isoformat() if update.captured_at else None,
        "gps_quality": update.gps_quality.value if update.gps_quality else None,
        "actual_location_id": update.actual_location_id,
        "actual_location": _location_payload(update.actual_location),
        "validation_result": update.validation_result,
        "resolution_method": update.resolution_method.value if update.resolution_method else None,
        "distance_m": update.distance_m,
        "location_candidates": list(update.location_candidates),
        "photos": [
            {"id": photo.id, "mime": photo.mime, "size_bytes": photo.size_bytes}
            for photo in update.photos
        ],
        "resolved_address": _resolved_address(update.actual_location),
        "maps_url": _maps_url(update.captured_latitude, update.captured_longitude),
    }


def _resolved_address(location: LocationDisplay | None) -> str | None:
    if location is None:
        return None
    return f"{location.name} — {location.address}" if location.address else location.name


def _maps_url(latitude: str | None, longitude: str | None) -> str | None:
    if latitude is None or longitude is None:
        return None
    return f"https://www.google.com/maps?{urlencode({'q': f'{latitude},{longitude}'})}"


def _user_payload(user: IdentityDisplay | None) -> dict[str, object] | None:
    if user is None:
        return None
    return {"id": user.id, "full_name": user.full_name}


def _location_payload(location: LocationDisplay | None) -> dict[str, object] | None:
    if location is None:
        return None
    return {
        "id": location.id,
        "code": location.code,
        "name": location.name,
        "is_active": location.is_active,
        "address": location.address,
    }


def _legacy_expected_location(location: LocationDisplay | None) -> str:
    return f"{location.code} — {location.name}" if location else ""
