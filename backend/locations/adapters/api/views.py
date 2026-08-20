from __future__ import annotations

from collections.abc import Callable
from typing import cast

from django.http import Http404, HttpRequest
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.error_codes import NOT_FOUND, VALIDATION_FAILED
from core.errors import IdentityAPIError
from identity.ports.authorization import PermissionAction
from locations.adapters.api.permissions import CanonicalLocationPermission
from locations.adapters.api.serializers import (
    ConfigSerializer,
    ConfigUpdateResultSerializer,
    ConfigUpdateSerializer,
    HolidayCreateSerializer,
    HolidaySerializer,
    LocationSerializer,
    LocationUpdateResultSerializer,
    LocationUpdateSerializer,
    WarningSerializer,
    validate_kind,
)
from locations.application.container import LocationsContainer
from locations.application.dto import CreateHolidayRequest, UpdateLocationRequest
from locations.domain.locations import LocationKind

FOUNDATION_ERROR = OpenApiResponse(response={"$ref": "#/components/schemas/FoundationError"})


def _positive_id(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as error:
        raise IdentityAPIError(NOT_FOUND, status_code=404) from error
    if value < 1:
        raise IdentityAPIError(NOT_FOUND, status_code=404)
    return value


def _actor_id(request: Request) -> int:
    return cast(int, request.user.pk)


class LocationsView(APIView):
    permission_classes = (CanonicalLocationPermission,)
    container_provider: Callable[[], LocationsContainer] | None = None

    def container(self) -> LocationsContainer:
        if self.container_provider is None:
            raise RuntimeError("locations container is not configured")
        return self.container_provider()


class LocationListView(LocationsView):
    serializer_class = LocationSerializer

    def http_method_not_allowed(
        self, request: HttpRequest, *args: object, **kwargs: object
    ) -> Response:
        raise Http404

    @staticmethod
    def permission_action(method: str) -> PermissionAction:
        return PermissionAction.LOCATION_VIEW

    @extend_schema(
        operation_id="locations_list",
        parameters=[
            OpenApiParameter(
                "kind", str, enum=[value.value for value in LocationKind], required=False
            ),
            OpenApiParameter("parent", int, required=False),
            OpenApiParameter("is_active", bool, required=False),
        ],
        responses={
            200: LocationSerializer(many=True),
            400: FOUNDATION_ERROR,
            401: FOUNDATION_ERROR,
            403: FOUNDATION_ERROR,
        },
    )
    def get(self, request: Request) -> Response:
        if set(request.query_params) - {"kind", "parent", "is_active"}:
            raise IdentityAPIError(VALIDATION_FAILED, status_code=400)
        kind = validate_kind(request.query_params.get("kind"))
        parent_raw = request.query_params.get("parent")
        active_raw = request.query_params.get("is_active")
        try:
            parent_id = None if parent_raw is None else _positive_id(parent_raw)
            is_active = (
                None if active_raw is None else {"true": True, "false": False}[active_raw.lower()]
            )
        except (KeyError, IdentityAPIError) as error:
            raise IdentityAPIError(VALIDATION_FAILED, status_code=400) from error
        values = self.container().location_queries.list(
            kind=kind, parent_id=parent_id, is_active=is_active
        )
        return Response(LocationSerializer(values, many=True).data)


class LocationDetailView(LocationsView):
    serializer_class = LocationUpdateSerializer

    def http_method_not_allowed(
        self, request: HttpRequest, *args: object, **kwargs: object
    ) -> Response:
        raise Http404

    @staticmethod
    def permission_action(method: str) -> PermissionAction:
        return PermissionAction.LOCATION_MANAGE

    @extend_schema(
        operation_id="locations_partial_update",
        request=LocationUpdateSerializer,
        responses={
            200: LocationUpdateResultSerializer,
            400: FOUNDATION_ERROR,
            401: FOUNDATION_ERROR,
            403: FOUNDATION_ERROR,
            404: FOUNDATION_ERROR,
            409: FOUNDATION_ERROR,
        },
    )
    def patch(self, request: Request, location_id: str) -> Response:
        parsed_id = _positive_id(location_id)
        serializer = LocationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result, warnings = self.container().location_admin.update(
            _actor_id(request), parsed_id, UpdateLocationRequest(**serializer.validated_data)
        )
        return Response(
            {
                "location": LocationSerializer(result).data,
                "warnings": WarningSerializer(warnings, many=True).data,
            }
        )


class ConfigView(LocationsView):
    serializer_class = ConfigUpdateSerializer

    @staticmethod
    def permission_action(method: str) -> PermissionAction:
        return (
            PermissionAction.CONFIG_VIEW
            if method == "GET"
            else PermissionAction.CONFIG_MANAGE_ATTENDANCE
        )

    @extend_schema(
        operation_id="config_retrieve",
        responses={
            200: ConfigSerializer,
            401: FOUNDATION_ERROR,
            403: FOUNDATION_ERROR,
            404: FOUNDATION_ERROR,
        },
    )
    def get(self, request: Request) -> Response:
        config = self.container().config_queries.get()
        if config is None:
            raise IdentityAPIError(NOT_FOUND, status_code=404)
        return Response(ConfigSerializer(config).data)

    @extend_schema(
        operation_id="config_partial_update",
        request=ConfigUpdateSerializer,
        responses={
            200: ConfigUpdateResultSerializer,
            400: FOUNDATION_ERROR,
            401: FOUNDATION_ERROR,
            403: FOUNDATION_ERROR,
            404: FOUNDATION_ERROR,
        },
    )
    def patch(self, request: Request) -> Response:
        serializer = ConfigUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        config, warnings = self.container().config_admin.update(
            _actor_id(request), dict(serializer.validated_data)
        )
        return Response(
            {
                "config": ConfigSerializer(config).data,
                "warnings": WarningSerializer(warnings, many=True).data,
            }
        )


class HolidayListCreateView(LocationsView):
    serializer_class = HolidayCreateSerializer

    @staticmethod
    def permission_action(method: str) -> PermissionAction:
        return PermissionAction.HOLIDAY_MANAGE

    @extend_schema(
        operation_id="holidays_list",
        responses={
            200: HolidaySerializer(many=True),
            401: FOUNDATION_ERROR,
            403: FOUNDATION_ERROR,
        },
    )
    def get(self, request: Request) -> Response:
        values = self.container().holidays.list(_actor_id(request))
        return Response(HolidaySerializer(values, many=True).data)

    @extend_schema(
        operation_id="holidays_create",
        request=HolidayCreateSerializer,
        responses={
            201: HolidaySerializer,
            400: FOUNDATION_ERROR,
            401: FOUNDATION_ERROR,
            403: FOUNDATION_ERROR,
        },
    )
    def post(self, request: Request) -> Response:
        serializer = HolidayCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        created = self.container().holidays.create(
            _actor_id(request), CreateHolidayRequest(**serializer.validated_data)
        )
        return Response(HolidaySerializer(created).data, status=201)


class HolidayDetailView(LocationsView):
    serializer_class = HolidaySerializer

    @staticmethod
    def permission_action(method: str) -> PermissionAction:
        return PermissionAction.HOLIDAY_MANAGE

    @extend_schema(
        operation_id="holidays_destroy",
        responses={
            204: None,
            401: FOUNDATION_ERROR,
            403: FOUNDATION_ERROR,
            404: FOUNDATION_ERROR,
        },
    )
    def delete(self, request: Request, holiday_id: str) -> Response:
        self.container().holidays.delete(_actor_id(request), _positive_id(holiday_id))
        return Response(status=204)
