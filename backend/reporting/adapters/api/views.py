from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import cast

from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.error_codes import VALIDATION_FAILED
from core.errors import IdentityAPIError
from reporting.adapters.api.permissions import ReportingPermission
from reporting.adapters.api.serializers import (
    AttendanceReportSerializer,
    TaskReportSerializer,
    attendance_payload,
    task_payload,
)
from reporting.application.container import ReportingContainer
from reporting.application.dto import ReportFilters

REPORT_PARAMETERS = [
    OpenApiParameter("start_date", str, required=True),
    OpenApiParameter("end_date", str, required=True),
    OpenApiParameter("user_id", int, required=False),
]
EXPORT_PARAMETERS = [
    *REPORT_PARAMETERS,
    OpenApiParameter("include_sensitive_coordinates", bool, required=False),
]


class ReportingView(APIView):
    permission_classes = (ReportingPermission,)
    container_provider: Callable[[], ReportingContainer] | None = None
    export = False

    def container(self) -> ReportingContainer:
        if self.container_provider is None:
            raise RuntimeError("reporting container is not configured")
        return cast("ReportingContainer", self.container_provider())

    def check_permission(self, actor_id: int) -> None:
        if self.export:
            self.container().queries._dependencies.authorization.authorize_export(actor_id)
        else:
            self.container().queries._dependencies.authorization.authorize_view(actor_id)

    def filters(self, request: Request) -> ReportFilters:
        allowed = {"start_date", "end_date", "user_id", "include_sensitive_coordinates"}
        extra = set(request.query_params) - allowed
        if extra or request.data:
            raise IdentityAPIError(VALIDATION_FAILED, status_code=400)
        try:
            start_date = date.fromisoformat(request.query_params["start_date"])
            end_date = date.fromisoformat(request.query_params["end_date"])
        except (KeyError, ValueError) as error:
            raise IdentityAPIError(VALIDATION_FAILED, status_code=400) from error
        if start_date > end_date:
            raise IdentityAPIError(VALIDATION_FAILED, status_code=400)
        raw_user_id = request.query_params.get("user_id")
        include_raw = request.query_params.get("include_sensitive_coordinates", "false")
        try:
            user_id = int(raw_user_id) if raw_user_id else None
        except ValueError as error:
            raise IdentityAPIError(VALIDATION_FAILED, status_code=400) from error
        return ReportFilters(
            actor_id=cast(int, request.user.pk),
            start_date=start_date,
            end_date=end_date,
            user_id=user_id,
            include_sensitive_coordinates=include_raw.casefold() == "true",
        )


class AttendanceReportView(ReportingView):
    @extend_schema(
        operation_id="reports_attendance_retrieve",
        parameters=REPORT_PARAMETERS,
        responses=AttendanceReportSerializer,
    )
    def get(self, request: Request) -> Response:
        report = self.container().queries.attendance(self.filters(request))
        return _private(Response(attendance_payload(report)))


class TaskReportView(ReportingView):
    @extend_schema(
        operation_id="reports_tasks_retrieve",
        parameters=REPORT_PARAMETERS,
        responses=TaskReportSerializer,
    )
    def get(self, request: Request) -> Response:
        report = self.container().queries.tasks(self.filters(request))
        return _private(Response(task_payload(report)))


class AttendanceExportView(ReportingView):
    export = True

    @extend_schema(
        operation_id="reports_attendance_export",
        parameters=EXPORT_PARAMETERS,
        responses={(200, "text/csv"): OpenApiTypes.STR},
    )
    def get(self, request: Request) -> HttpResponse:
        content = self.container().queries.export_attendance(self.filters(request))
        return _csv(content, "attendance-report.csv")


class TaskExportView(ReportingView):
    export = True

    @extend_schema(
        operation_id="reports_tasks_export",
        parameters=REPORT_PARAMETERS,
        responses={(200, "text/csv"): OpenApiTypes.STR},
    )
    def get(self, request: Request) -> HttpResponse:
        content = self.container().queries.export_tasks(self.filters(request))
        return _csv(content, "task-report.csv")


def _private(response: Response) -> Response:
    response["Cache-Control"] = "private, no-store"
    return response


def _csv(content: str, filename: str) -> HttpResponse:
    response = HttpResponse(content, content_type="text/csv; charset=utf-8")
    response["Cache-Control"] = "private, no-store"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
