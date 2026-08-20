from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiExample,
    PolymorphicProxySerializer,
    extend_schema,
    extend_schema_view,
)
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from attendance.adapters.api.permissions import CanonicalAttendancePermission
from attendance.adapters.api.serializers import (
    AttendanceCommandResultSerializer,
    AttendanceCommandSerializer,
    AttendanceErrorSerializer,
    GpsBoundaryErrorSerializer,
    InvalidLocationChoiceErrorSerializer,
    LocationChoiceRequiredErrorSerializer,
    NoOpenSessionErrorSerializer,
    SessionAlreadyOpenErrorSerializer,
    TodayAttendanceSerializer,
    command_result_payload,
    today_payload,
)
from attendance.application.container import AttendanceContainer
from attendance.application.dto import AttendanceCommand
from attendance.ports.authorization import AttendanceAuthorization
from core.error_codes import VALIDATION_FAILED
from core.errors import IdentityAPIError


class AttendanceView(APIView):
    permission_classes = (CanonicalAttendancePermission,)
    container_provider: Callable[[], AttendanceContainer] | None = None

    def container(self) -> AttendanceContainer:
        if self.container_provider is None:
            raise RuntimeError("attendance container is not configured")
        return self.container_provider()

    @staticmethod
    def authorize(authorization: AttendanceAuthorization, actor_id: int) -> None:
        raise NotImplementedError


class AttendanceCommandView(AttendanceView):
    command_name = ""

    @extend_schema(
        operation_id="attendance_command_create",
        request=AttendanceCommandSerializer,
        responses={201: AttendanceCommandResultSerializer},
    )
    def post(self, request: Request) -> Response:
        receipt_time = timezone.now()
        serializer = AttendanceCommandSerializer(
            data=request.data, context={"receipt_time": receipt_time}
        )
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as error:
            raise IdentityAPIError(VALIDATION_FAILED, status_code=400) from error
        command = AttendanceCommand(
            **serializer.validated_data,
            device_metadata=_device_metadata(request),
            request_ip=request.META.get("REMOTE_ADDR"),
        )
        actor_id = cast(int, request.user.pk)
        service = self.container().commands
        result = (
            service.check_in(actor_id, command)
            if self.command_name == "in"
            else service.check_out(actor_id, command)
        )
        return Response(command_result_payload(result), status=201)


COMMAND_COMMON_RESPONSES = {
    201: AttendanceCommandResultSerializer,
    400: AttendanceErrorSerializer,
    401: AttendanceErrorSerializer,
    403: AttendanceErrorSerializer,
}
COMMAND_UNPROCESSABLE_RESPONSE = PolymorphicProxySerializer(
    component_name="AttendanceUnprocessableError",
    serializers=[GpsBoundaryErrorSerializer, InvalidLocationChoiceErrorSerializer],
    resource_type_field_name=None,
)


def _error_example(name: str, code: str, status: int, **extra: object) -> OpenApiExample:
    return OpenApiExample(
        name,
        value={
            "error_code": code,
            "message": "Yêu cầu chấm công không được chấp nhận.",
            "details": {},
            "request_id": "00000000-0000-4000-8000-000000000000",
            "error": code,
            **extra,
        },
        response_only=True,
        status_codes=[str(status)],
    )


CANDIDATES = [
    {"id": 1, "code": "LOCATION_A", "name": "Location A", "distance_m": "10.000"},
    {"id": 2, "code": "LOCATION_B", "name": "Location B", "distance_m": "20.000"},
]
COMMON_COMMAND_EXAMPLES = [
    _error_example(
        "Location choice required", "LOCATION_CHOICE_REQUIRED", 409, location_candidates=CANDIDATES
    ),
    _error_example("Weak GPS", "WEAK_GPS", 422),
    _error_example("Outside radius", "OUTSIDE_RADIUS", 422),
    _error_example(
        "Invalid choice", "INVALID_LOCATION_CHOICE", 422, location_candidates=CANDIDATES[:1]
    ),
]


@extend_schema_view(
    post=extend_schema(
        operation_id="attendance_check_in",
        responses={
            **COMMAND_COMMON_RESPONSES,
            409: PolymorphicProxySerializer(
                component_name="CheckInConflictError",
                serializers=[
                    SessionAlreadyOpenErrorSerializer,
                    LocationChoiceRequiredErrorSerializer,
                ],
                resource_type_field_name=None,
            ),
            422: COMMAND_UNPROCESSABLE_RESPONSE,
        },
        examples=[
            _error_example("Session already open", "SESSION_ALREADY_OPEN", 409),
            *COMMON_COMMAND_EXAMPLES,
        ],
    )
)
class CheckInView(AttendanceCommandView):
    command_name = "in"

    @staticmethod
    def authorize(authorization: AttendanceAuthorization, actor_id: int) -> None:
        authorization.authorize_check_in(actor_id)


@extend_schema_view(
    post=extend_schema(
        operation_id="attendance_check_out",
        responses={
            **COMMAND_COMMON_RESPONSES,
            409: PolymorphicProxySerializer(
                component_name="CheckOutConflictError",
                serializers=[NoOpenSessionErrorSerializer, LocationChoiceRequiredErrorSerializer],
                resource_type_field_name=None,
            ),
            422: COMMAND_UNPROCESSABLE_RESPONSE,
        },
        examples=[
            _error_example("No open session", "NO_OPEN_SESSION", 409),
            *COMMON_COMMAND_EXAMPLES,
        ],
    )
)
class CheckOutView(AttendanceCommandView):
    command_name = "out"

    @staticmethod
    def authorize(authorization: AttendanceAuthorization, actor_id: int) -> None:
        authorization.authorize_check_out(actor_id)


class TodayAttendanceView(AttendanceView):
    @staticmethod
    def authorize(authorization: AttendanceAuthorization, actor_id: int) -> None:
        authorization.authorize_view_self(actor_id)

    @extend_schema(
        operation_id="attendance_today_retrieve",
        responses={200: TodayAttendanceSerializer},
    )
    def get(self, request: Request) -> Response:
        if request.query_params or request.data:
            raise IdentityAPIError(VALIDATION_FAILED, status_code=400)
        actor_id = cast(int, request.user.pk)
        return Response(today_payload(self.container().queries.today(actor_id)))


def _device_metadata(request: Request) -> dict[str, Any]:
    user_agent = request.META.get("HTTP_USER_AGENT")
    return {"user_agent": user_agent[:255]} if user_agent else {}
