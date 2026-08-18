from collections.abc import Callable

from django.urls import URLPattern, path

from identity.adapters.api.permissions import LogoutAuthorizer, TargetLookup
from identity.adapters.api.views import (
    ChangePasswordView,
    LoginView,
    LogoutView,
    MeView,
    RefreshView,
    UserDetailView,
    UserListCreateView,
    UserResetPasswordView,
    UserRoleView,
    UserStatusView,
)
from identity.application.container import IdentityContainer


def identity_urlpatterns(
    container_provider: Callable[[], IdentityContainer],
    target_lookup: TargetLookup,
    logout_authorizer: LogoutAuthorizer,
) -> list[URLPattern]:
    injected: dict[str, object] = {
        "container_provider": container_provider,
        "target_lookup": target_lookup,
        "logout_authorizer": logout_authorizer,
    }
    return _authentication_paths(injected) + _user_admin_paths(injected)


def _authentication_paths(injected: dict[str, object]) -> list[URLPattern]:
    return [
        path("auth/login", LoginView.as_view(**injected), name="auth-login"),
        path("auth/refresh", RefreshView.as_view(**injected), name="auth-refresh"),
        path("auth/logout", LogoutView.as_view(**injected), name="auth-logout"),
        path("me/", MeView.as_view(**injected), name="identity-me"),
        path(
            "change-password",
            ChangePasswordView.as_view(**injected),
            name="identity-change-password",
        ),
        path("users/", UserListCreateView.as_view(**injected), name="users-list"),
    ]


def _user_admin_paths(injected: dict[str, object]) -> list[URLPattern]:
    return [
        path(
            "users/<str:user_id>/",
            UserDetailView.as_view(**injected),
            name="users-detail",
        ),
        path(
            "users/<str:user_id>/role",
            UserRoleView.as_view(**injected),
            name="users-role",
        ),
        path(
            "users/<str:user_id>/status",
            UserStatusView.as_view(**injected),
            name="users-status",
        ),
        path(
            "users/<str:user_id>/reset-password",
            UserResetPasswordView.as_view(**injected),
            name="users-reset-password",
        ),
    ]
