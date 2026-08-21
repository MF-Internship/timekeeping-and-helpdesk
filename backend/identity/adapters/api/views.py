from __future__ import annotations

from collections.abc import Callable
from typing import Never, cast

from django.db import IntegrityError
from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.error_codes import INVALID_TOKEN, VALIDATION_FAILED
from core.errors import IdentityAPIError
from identity.adapters.api.permissions import (
    CanonicalIdentityPermission,
    TargetLookup,
)
from identity.adapters.api.serializers import (
    AccessResponseSerializer,
    AdminUserSerializer,
    EmptySerializer,
    GeneratedUserResultSerializer,
    IdentityErrorSerializer,
    LoginResponseSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    ProfileSerializer,
    ResetPasswordResultSerializer,
    RoleSerializer,
    SelfUserSerializer,
    StatusSerializer,
    UserCreateSerializer,
    UserPageSerializer,
    admin_user,
    self_user,
)
from identity.adapters.api.throttles import (
    LoginThrottle,
    PasswordChangeThrottle,
    RefreshThrottle,
)
from identity.application.container import IdentityContainer
from identity.application.dto import PasswordChangeRequest, ProfileUpdateRequest, UserCreateRequest
from identity.application.queries import MAX_PAGE_SIZE, PAGE_SIZE, UserFilters, UserPage
from identity.domain.authorization import PermissionAction, Role

REFRESH_COOKIE = "refresh_token"
REFRESH_PATH = "/api/v1/auth/"


class IdentityView(APIView):
    container_provider: Callable[[], IdentityContainer] | None = None
    target_lookup: TargetLookup | None = None

    def container(self) -> IdentityContainer:
        if self.container_provider is None:
            raise RuntimeError("identity container is not configured")
        return self.container_provider()


def _set_refresh(response: Response, value: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        value,
        httponly=True,
        secure=True,
        samesite="Strict",
        path=REFRESH_PATH,
        max_age=7 * 24 * 60 * 60,
    )


def _clear_refresh(response: Response) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        "",
        httponly=True,
        secure=True,
        samesite="Strict",
        path=REFRESH_PATH,
        max_age=0,
        expires="Thu, 01 Jan 1970 00:00:00 GMT",
    )


def _no_store(response: Response) -> Response:
    response["Cache-Control"] = "private, no-store"
    return response


def _actor_id(request: Request) -> int:
    return cast(int, request.user.pk)


def _target_id(raw_user_id: str) -> int:
    try:
        user_id = int(raw_user_id)
    except ValueError as error:
        raise Http404 from error
    if user_id < 1:
        raise Http404
    return user_id


def _user_filters(request: Request) -> tuple[UserFilters, int, int]:
    role_raw = request.query_params.get("role")
    active_raw = request.query_params.get("is_active")
    if "page" in request.query_params:
        _raise_invalid_filter("page", "Hãy sử dụng offset và limit.")
    try:
        role = None if role_raw is None else Role(role_raw)
        active = None if active_raw is None else {"true": True, "false": False}[active_raw.lower()]
        offset = int(request.query_params.get("offset", "0"))
        limit = int(request.query_params.get("limit", str(PAGE_SIZE)))
    except (ValueError, KeyError) as error:
        field = _invalid_filter_field(request, role_raw)
        _raise_invalid_filter(field, "Giá trị không hợp lệ.", cause=error)
    if offset < 0 or limit < 1 or limit > MAX_PAGE_SIZE:
        _raise_invalid_filter("pagination", "Offset hoặc limit không hợp lệ.")
    return UserFilters(request.query_params.get("q"), role, active), offset, limit


def _invalid_filter_field(request: Request, role_raw: str | None) -> str:
    if request.query_params.get("offset"):
        return "offset"
    if request.query_params.get("limit"):
        return "limit"
    return "role" if role_raw else "is_active"


def _raise_invalid_filter(field: str, message: str, *, cause: Exception | None = None) -> Never:
    error = IdentityAPIError(
        VALIDATION_FAILED,
        status_code=400,
        details={field: [message]},
    )
    if cause is not None:
        raise error from cause
    raise error


def _user_page_response(request: Request, result: UserPage) -> Response:
    payload = {
        "count": result.count,
        "next": _offset_link(request, result.offset + result.limit)
        if result.offset + result.limit < result.count
        else None,
        "previous": _offset_link(request, max(0, result.offset - result.limit))
        if result.offset > 0
        else None,
        "results": [admin_user(item) for item in result.results],
    }
    return _no_store(Response(payload))


def _offset_link(request: Request, offset: int) -> str:
    query = request.query_params.copy()
    query["offset"] = str(offset)
    query["limit"] = query.get("limit", str(PAGE_SIZE))
    return f"{request.path}?{query.urlencode()}"


class LoginView(IdentityView):
    permission_classes = (AllowAny,)
    throttle_classes = (LoginThrottle,)

    @extend_schema(
        operation_id="auth_login_create",
        auth=[],
        request=LoginSerializer,
        responses={
            200: LoginResponseSerializer,
            400: IdentityErrorSerializer,
            401: IdentityErrorSerializer,
            429: IdentityErrorSerializer,
            503: IdentityErrorSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        issued, account, capabilities = self.container().authentication.login(
            serializer.validated_data["username"], serializer.validated_data["password"]
        )
        response = Response(
            {
                "access": issued.access,
                "role": account.role.value,
                "is_active": account.is_active,
                "must_change_password": account.must_change_password,
                "capabilities": capabilities,
            }
        )
        _set_refresh(response, issued.refresh)
        return _no_store(response)


class RefreshView(IdentityView):
    permission_classes = (AllowAny,)
    throttle_classes = (RefreshThrottle,)

    @extend_schema(
        operation_id="auth_refresh_create",
        auth=[],
        request=EmptySerializer,
        responses={
            200: AccessResponseSerializer,
            400: IdentityErrorSerializer,
            401: IdentityErrorSerializer,
            403: IdentityErrorSerializer,
            429: IdentityErrorSerializer,
            503: IdentityErrorSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        EmptySerializer(data=request.data).is_valid(raise_exception=True)
        raw = request.COOKIES.get(REFRESH_COOKIE)
        if not raw:
            raise IdentityAPIError(INVALID_TOKEN, status_code=401)
        issued = self.container().authentication.refresh(raw)
        response = Response({"access": issued.access})
        _set_refresh(response, issued.refresh)
        return _no_store(response)


class LogoutView(IdentityView):
    permission_classes = (CanonicalIdentityPermission,)

    @extend_schema(
        operation_id="auth_logout_create",
        request=EmptySerializer,
        responses={
            204: None,
            400: IdentityErrorSerializer,
            401: IdentityErrorSerializer,
            403: IdentityErrorSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        EmptySerializer(data=request.data).is_valid(raise_exception=True)
        self.container().authentication.logout(_actor_id(request))
        response = Response(status=204)
        _clear_refresh(response)
        return _no_store(response)


class MeView(IdentityView):
    permission_classes = (CanonicalIdentityPermission,)

    @extend_schema(
        operation_id="identity_me_retrieve",
        responses={
            200: SelfUserSerializer,
            401: IdentityErrorSerializer,
            403: IdentityErrorSerializer,
        },
    )
    def get(self, request: Request) -> Response:
        return _no_store(Response(self_user(self.container().self_service.get(_actor_id(request)))))

    @extend_schema(
        operation_id="identity_me_partial_update",
        request=ProfileSerializer,
        responses={
            200: SelfUserSerializer,
            400: IdentityErrorSerializer,
            401: IdentityErrorSerializer,
            403: IdentityErrorSerializer,
        },
    )
    def patch(self, request: Request) -> Response:
        serializer = ProfileSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        account = self.container().self_service.update(
            _actor_id(request),
            ProfileUpdateRequest(**values, provided_fields=frozenset(values)),
        )
        return _no_store(Response(self_user(account)))


class ChangePasswordView(IdentityView):
    permission_classes = (CanonicalIdentityPermission,)
    password_change_exempt = True
    throttle_classes = (PasswordChangeThrottle,)

    @extend_schema(
        operation_id="identity_change_password_create",
        request=PasswordChangeSerializer,
        responses={
            200: AccessResponseSerializer,
            400: IdentityErrorSerializer,
            401: IdentityErrorSerializer,
            403: IdentityErrorSerializer,
            429: IdentityErrorSerializer,
            503: IdentityErrorSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            issued = self.container().self_service.change_password(
                _actor_id(request), PasswordChangeRequest(**serializer.validated_data)
            )
        except ValueError as error:
            field = "current_password" if str(error) == "current_password" else "new_password"
            raise IdentityAPIError(
                VALIDATION_FAILED,
                status_code=400,
                details={field: ["Mật khẩu không hợp lệ."]},
            ) from error
        response = Response({"access": issued.access})
        _set_refresh(response, issued.refresh)
        return _no_store(response)


class UserListCreateView(IdentityView):
    permission_classes = (CanonicalIdentityPermission,)

    @property
    def required_action(self) -> PermissionAction:
        return (
            PermissionAction.USER_VIEW
            if self.request.method == "GET"
            else PermissionAction.USER_MANAGE
        )

    @extend_schema(
        operation_id="users_list",
        parameters=[
            OpenApiParameter("q", str, required=False),
            OpenApiParameter("role", str, required=False),
            OpenApiParameter("is_active", bool, required=False),
            OpenApiParameter("offset", int, required=False, description="Vị trí bắt đầu, từ 0."),
            OpenApiParameter("limit", int, required=False, description="Số bản ghi, tối đa 100."),
        ],
        responses={
            200: UserPageSerializer,
            400: IdentityErrorSerializer,
            401: IdentityErrorSerializer,
            403: IdentityErrorSerializer,
        },
    )
    def get(self, request: Request) -> Response:
        try:
            filters, offset, limit = _user_filters(request)
            result = self.container().queries.list(filters, offset, limit)
        except ValueError as error:
            raise IdentityAPIError(
                VALIDATION_FAILED,
                status_code=400,
                details={"pagination": ["Offset hoặc limit không hợp lệ."]},
            ) from error
        return _user_page_response(request, result)

    @extend_schema(
        operation_id="users_create",
        request=UserCreateSerializer,
        responses={
            201: GeneratedUserResultSerializer,
            400: IdentityErrorSerializer,
            401: IdentityErrorSerializer,
            403: IdentityErrorSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            result = self.container().user_admin.create(
                _actor_id(request),
                UserCreateRequest(
                    username=data["username"],
                    full_name=data["full_name"],
                    role=Role(data["role"]),
                    phone=data.get("phone"),
                    email=data.get("email"),
                ),
            )
        except IntegrityError as error:
            raise IdentityAPIError(
                VALIDATION_FAILED,
                status_code=400,
                details={"username": ["Tên đăng nhập đã tồn tại."]},
            ) from error
        return _no_store(
            Response(
                {
                    "user": admin_user(result.account),
                    "generated_password": result.generated_password,
                },
                status=201,
            )
        )


class UserDetailView(IdentityView):
    permission_classes = (CanonicalIdentityPermission,)

    @property
    def required_action(self) -> PermissionAction:
        return (
            PermissionAction.USER_VIEW
            if self.request.method == "GET"
            else PermissionAction.USER_MANAGE
        )

    @property
    def protect_manager_target(self) -> bool:
        return self.request.method == "PATCH"

    @extend_schema(
        operation_id="users_retrieve",
        responses={
            200: AdminUserSerializer,
            401: IdentityErrorSerializer,
            403: IdentityErrorSerializer,
            404: IdentityErrorSerializer,
        },
    )
    def get(self, request: Request, user_id: str) -> Response:
        target_id = _target_id(user_id)
        account = self.container().users.get(target_id)
        if account is None:
            raise Http404
        return _no_store(Response(admin_user(account)))

    @extend_schema(
        operation_id="users_partial_update",
        request=ProfileSerializer,
        responses={
            200: AdminUserSerializer,
            400: IdentityErrorSerializer,
            401: IdentityErrorSerializer,
            403: IdentityErrorSerializer,
            404: IdentityErrorSerializer,
        },
    )
    def patch(self, request: Request, user_id: str) -> Response:
        target_id = _target_id(user_id)
        serializer = ProfileSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        try:
            account = self.container().user_admin.update_profile(
                _actor_id(request),
                target_id,
                ProfileUpdateRequest(**values, provided_fields=frozenset(values)),
            )
        except LookupError as error:
            raise Http404 from error
        return _no_store(Response(admin_user(account)))


class UserRoleView(IdentityView):
    permission_classes = (CanonicalIdentityPermission,)
    required_action = PermissionAction.USER_ASSIGN_ROLE
    protect_manager_target = True

    @extend_schema(
        operation_id="users_role_partial_update",
        request=RoleSerializer,
        responses={
            200: AdminUserSerializer,
            400: IdentityErrorSerializer,
            401: IdentityErrorSerializer,
            403: IdentityErrorSerializer,
            404: IdentityErrorSerializer,
        },
    )
    def patch(self, request: Request, user_id: str) -> Response:
        target_id = _target_id(user_id)
        serializer = RoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            account = self.container().user_admin.change_role(
                _actor_id(request), target_id, Role(serializer.validated_data["role"])
            )
        except LookupError as error:
            raise Http404 from error
        return _no_store(Response(admin_user(account)))


class UserStatusView(IdentityView):
    permission_classes = (CanonicalIdentityPermission,)
    required_action = PermissionAction.USER_MANAGE
    protect_manager_target = True

    @extend_schema(
        operation_id="users_status_partial_update",
        request=StatusSerializer,
        responses={
            200: AdminUserSerializer,
            400: IdentityErrorSerializer,
            401: IdentityErrorSerializer,
            403: IdentityErrorSerializer,
            404: IdentityErrorSerializer,
        },
    )
    def patch(self, request: Request, user_id: str) -> Response:
        target_id = _target_id(user_id)
        serializer = StatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            account = self.container().user_admin.change_status(
                _actor_id(request), target_id, serializer.validated_data["is_active"]
            )
        except LookupError as error:
            raise Http404 from error
        return _no_store(Response(admin_user(account)))


class UserResetPasswordView(IdentityView):
    permission_classes = (CanonicalIdentityPermission,)
    required_action = PermissionAction.USER_MANAGE
    protect_manager_target = True

    @extend_schema(
        operation_id="users_reset_password_create",
        request=EmptySerializer,
        responses={
            200: ResetPasswordResultSerializer,
            400: IdentityErrorSerializer,
            401: IdentityErrorSerializer,
            403: IdentityErrorSerializer,
            404: IdentityErrorSerializer,
        },
    )
    def post(self, request: Request, user_id: str) -> Response:
        target_id = _target_id(user_id)
        EmptySerializer(data=request.data).is_valid(raise_exception=True)
        try:
            result = self.container().user_admin.reset_password(_actor_id(request), target_id)
        except LookupError as error:
            raise Http404 from error
        return _no_store(
            Response(
                {
                    "user_id": result.account.id,
                    "must_change_password": True,
                    "generated_password": result.generated_password,
                }
            )
        )
