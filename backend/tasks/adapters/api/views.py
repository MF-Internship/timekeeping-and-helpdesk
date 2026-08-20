from __future__ import annotations

from collections.abc import Callable
from typing import cast

from drf_spectacular.utils import (  # type: ignore[attr-defined]
    OpenApiParameter,
    OpenApiRequest,
    OpenApiTypes,
    extend_schema,
)
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.error_codes import NOT_FOUND
from core.errors import IdentityAPIError
from tasks.adapters.api.permissions import CanonicalTaskPermission
from tasks.adapters.api.serializers import (
    EvidenceUploadIntentSerializer,
    EvidenceUploadSerializer,
    GroupedTaskListSerializer,
    InactiveAssigneeErrorSerializer,
    PhotoAccessSerializer,
    TaskAlreadyCompletedErrorSerializer,
    TaskCreateSerializer,
    TaskDetailSerializer,
    TaskErrorSerializer,
    TaskFieldCompletionSerializer,
    TaskOverrideSerializer,
    TaskStatusSerializer,
    TaskUpdateSerializer,
    grouped_payload,
    reject_owned_fields,
    task_payload,
)
from tasks.application.container import TaskContainer
from tasks.application.dto import (
    AccessTaskPhotoCommand,
    ChangeTaskStatusCommand,
    CompleteTaskFieldCommand,
    CompleteTaskOverrideCommand,
    CreateEvidenceUploadCommand,
    CreateTaskCommand,
    DeleteTaskCommand,
    UpdateTaskCommand,
)
from tasks.domain.tasks import TaskStatus
from tasks.ports.authorization import TaskAuthorization, TaskCreateMode

ERRORS = {400: TaskErrorSerializer, 401: TaskErrorSerializer, 403: TaskErrorSerializer}
READ_ERRORS = {401: TaskErrorSerializer, 403: TaskErrorSerializer}
CREATE_REQUEST_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["title", "assigned_date"],
    "properties": {
        "title": {"type": "string", "minLength": 1},
        "description": {"type": "string", "default": ""},
        "assigned_date": {"type": "string", "format": "date"},
        "location_id": {"type": ["integer", "null"], "minimum": 1},
        "expected_location": {"type": "string", "maxLength": 500, "default": ""},
        "assignee_ids": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "integer", "minimum": 1},
        },
    },
}
OWNED_FIELDS = frozenset(
    {
        "created_by",
        "created_by_id",
        "status",
        "completed_by",
        "completed_at",
        "completion_method",
        "completion_note",
        "block_reason",
        "group",
        "overdue_days",
        "updates",
        "captured_latitude",
        "captured_longitude",
        "accuracy_m",
        "captured_at",
        "gps_quality",
        "actual_location_id",
        "validation_result",
        "resolution_method",
        "distance_m",
        "location_candidates",
        "photos",
        "deleted_at",
    }
)


class TaskView(APIView):
    permission_classes = (CanonicalTaskPermission,)
    container_provider: Callable[[], TaskContainer] | None = None

    def container(self) -> TaskContainer:
        if self.container_provider is None:
            raise RuntimeError("task container is not configured")
        return self.container_provider()

    def authorize(self, authorization: TaskAuthorization, actor_id: int, method: str) -> None:
        raise NotImplementedError


class TaskListCreateView(TaskView):
    create_mode: TaskCreateMode | None = None

    def authorize(self, authorization: TaskAuthorization, actor_id: int, method: str) -> None:
        if method == "GET":
            authorization.authorize_read(actor_id)
        else:
            self.create_mode = authorization.authorize_create(actor_id)

    @extend_schema(operation_id="tasks_list", responses={200: GroupedTaskListSerializer, **ERRORS})
    def get(self, request: Request) -> Response:
        if request.query_params or request.data:
            from core.error_codes import VALIDATION_FAILED

            raise IdentityAPIError(VALIDATION_FAILED, status_code=400)
        return Response(grouped_payload(self.container().queries.list(_actor_id(request))))

    @extend_schema(
        operation_id="tasks_create",
        request=OpenApiRequest(CREATE_REQUEST_SCHEMA),
        responses={201: TaskDetailSerializer, 422: InactiveAssigneeErrorSerializer, **ERRORS},
    )
    def post(self, request: Request) -> Response:
        mode = self.create_mode
        if mode is None:
            raise RuntimeError("create mode was not authorized")
        allowed = {"title", "description", "assigned_date", "location_id", "expected_location"}
        if mode is TaskCreateMode.ASSIGN:
            allowed.add("assignee_ids")
        reject_owned_fields(
            request.data,
            allowed=frozenset(allowed),
            owned=OWNED_FIELDS | ({"assignee_ids"} if mode is TaskCreateMode.SELF else set()),
        )
        serializer = TaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        command = CreateTaskCommand(
            actor_id=_actor_id(request), title=values["title"],
            description=values.get("description", ""), assigned_date=values["assigned_date"],
            location_id=values.get("location_id"),
            assignee_ids=tuple(values.get("assignee_ids", ())),
            expected_location=values.get("expected_location", ""),
        )
        task = self.container().commands.create(command)
        detail = self.container().queries.detail(_actor_id(request), task.id)
        return Response(task_payload(detail, include_updates=True), status=201)


class TaskDetailView(TaskView):
    def authorize(self, authorization: TaskAuthorization, actor_id: int, method: str) -> None:
        if method == "GET":
            authorization.authorize_read(actor_id)
        elif method == "DELETE":
            authorization.authorize_delete(actor_id)
        else:
            authorization.authorize_update(actor_id)

    @extend_schema(
        operation_id="tasks_retrieve",
        responses={200: TaskDetailSerializer, 404: TaskErrorSerializer, **READ_ERRORS},
    )
    def get(self, request: Request, task_id: str) -> Response:
        detail = self.container().queries.detail(_actor_id(request), _task_id(task_id))
        return Response(task_payload(detail, include_updates=True))

    @extend_schema(
        operation_id="tasks_partial_update",
        request=TaskUpdateSerializer,
        responses={
            200: TaskDetailSerializer,
            404: TaskErrorSerializer,
            422: InactiveAssigneeErrorSerializer,
            **ERRORS,
        },
    )
    def patch(self, request: Request, task_id: str) -> Response:
        reject_owned_fields(
            request.data,
            allowed=frozenset(
                {"title", "description", "location_id", "expected_location", "assignee_ids"}
            ),
            owned=OWNED_FIELDS | {"assigned_date"},
        )
        serializer = TaskUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        command = UpdateTaskCommand(
            actor_id=_actor_id(request), task_id=_task_id(task_id),
            title=values.get("title"), description=values.get("description"),
            location_id=values.get("location_id"), replace_location="location_id" in values,
            assignee_ids=(tuple(values["assignee_ids"]) if "assignee_ids" in values else None),
            expected_location=values.get("expected_location"),
            replace_expected_location="expected_location" in values,
        )
        task = self.container().commands.update(command)
        detail = self.container().queries.detail(_actor_id(request), task.id)
        return Response(task_payload(detail, include_updates=True))

    @extend_schema(
        operation_id="tasks_destroy",
        request=None,
        responses={204: None, 404: TaskErrorSerializer, 409: TaskErrorSerializer, **ERRORS},
    )
    def delete(self, request: Request, task_id: str) -> Response:
        self.container().commands.delete(DeleteTaskCommand(_actor_id(request), _task_id(task_id)))
        return Response(status=204)


class TaskStatusView(TaskView):
    def authorize(self, authorization: TaskAuthorization, actor_id: int, method: str) -> None:
        authorization.authorize_update(actor_id)

    @extend_schema(
        operation_id="tasks_status_create",
        request=TaskStatusSerializer,
        responses={
            200: TaskDetailSerializer,
            404: TaskErrorSerializer,
            422: TaskErrorSerializer,
            **ERRORS,
        },
    )
    def post(self, request: Request, task_id: str) -> Response:
        reject_owned_fields(
            request.data,
            allowed=frozenset({"status", "note", "block_reason"}),
            owned=OWNED_FIELDS - {"status", "block_reason"},
        )
        serializer = TaskStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        task = self.container().commands.change_status(
            ChangeTaskStatusCommand(
                _actor_id(request),
                _task_id(task_id),
                TaskStatus(values["status"]),
                values.get("note"),
                values.get("block_reason"),
            )
        )
        detail = self.container().queries.detail(_actor_id(request), task.id)
        return Response(task_payload(detail, include_updates=True))


class TaskOverrideView(TaskView):
    def authorize(self, authorization: TaskAuthorization, actor_id: int, method: str) -> None:
        authorization.authorize_override(actor_id)

    @extend_schema(
        operation_id="tasks_complete_override_create",
        request=TaskOverrideSerializer,
        responses={
            200: TaskDetailSerializer,
            404: TaskErrorSerializer,
            409: TaskAlreadyCompletedErrorSerializer,
            **ERRORS,
        },
    )
    def post(self, request: Request, task_id: str) -> Response:
        reject_owned_fields(
            request.data,
            allowed=frozenset({"completion_note"}),
            owned=OWNED_FIELDS - {"completion_note"},
        )
        serializer = TaskOverrideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = self.container().commands.complete_override(
            CompleteTaskOverrideCommand(
                _actor_id(request),
                _task_id(task_id),
                serializer.validated_data["completion_note"],
            )
        )
        detail = self.container().queries.detail(_actor_id(request), task.id)
        return Response(task_payload(detail, include_updates=True))


class TaskEvidenceUploadView(TaskView):
    def authorize(self, authorization: TaskAuthorization, actor_id: int, method: str) -> None:
        authorization.authorize_field_completion(actor_id)

    @extend_schema(
        operation_id="tasks_evidence_uploads_create",
        request=EvidenceUploadSerializer,
        responses={201: EvidenceUploadIntentSerializer, 404: TaskErrorSerializer, **ERRORS},
    )
    def post(self, request: Request, task_id: str) -> Response:
        serializer = EvidenceUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        result = self.container().evidence.create_upload(
            CreateEvidenceUploadCommand(
                _actor_id(request),
                _task_id(task_id),
                values["mime"],
                values["size_bytes"],
                values["checksum_sha256"],
            )
        )
        return Response(
            {
                "upload_id": result.upload_id,
                "upload_url": result.upload_url,
                "headers": result.headers,
                "expires_at": result.expires_at,
            },
            status=201,
        )


class TaskFieldCompletionView(TaskView):
    def authorize(self, authorization: TaskAuthorization, actor_id: int, method: str) -> None:
        authorization.authorize_field_completion(actor_id)

    @extend_schema(
        operation_id="tasks_complete_field_create",
        request=TaskFieldCompletionSerializer,
        parameters=[
            OpenApiParameter(
                "Idempotency-Key",
                OpenApiTypes.STR,
                OpenApiParameter.HEADER,
                required=True,
            )
        ],
        responses={
            200: TaskDetailSerializer,
            404: TaskErrorSerializer,
            409: TaskErrorSerializer,
            422: TaskErrorSerializer,
            **ERRORS,
        },
    )
    def post(self, request: Request, task_id: str) -> Response:
        serializer = TaskFieldCompletionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        key = request.headers.get("Idempotency-Key", "")
        task = self.container().evidence.complete_field(
            CompleteTaskFieldCommand(
                _actor_id(request),
                _task_id(task_id),
                key,
                tuple(str(value) for value in values["upload_ids"]),
                values["latitude"],
                values["longitude"],
                values["accuracy_m"],
                values.get("captured_at"),
                values.get("selected_location_id"),
                values.get("completion_note"),
            )
        )
        detail = self.container().queries.detail(_actor_id(request), task.id)
        return Response(task_payload(detail, include_updates=True))


class TaskPhotoAccessView(TaskView):
    def authorize(self, authorization: TaskAuthorization, actor_id: int, method: str) -> None:
        authorization.authorize_photo_read(actor_id)

    @extend_schema(
        operation_id="tasks_photos_access_create",
        request=None,
        responses={200: PhotoAccessSerializer, 404: TaskErrorSerializer, **READ_ERRORS},
    )
    def post(self, request: Request, task_id: str, photo_id: str) -> Response:
        result = self.container().evidence.access_photo(
            AccessTaskPhotoCommand(_actor_id(request), _task_id(task_id), _task_id(photo_id))
        )
        return Response({"url": result.url, "expires_at": result.expires_at})


def _actor_id(request: Request) -> int:
    return cast(int, request.user.pk)


def _task_id(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as error:
        raise IdentityAPIError(NOT_FOUND, status_code=404) from error
    if value < 1:
        raise IdentityAPIError(NOT_FOUND, status_code=404)
    return value
