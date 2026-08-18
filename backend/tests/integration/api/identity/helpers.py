from __future__ import annotations

from rest_framework.test import APIClient

from identity.models import User

ORIGIN = "test-origin-credential-at-least-32-chars"
DEFAULT_PASSWORD = "SafePassword123!"


def api_client() -> APIClient:
    return APIClient(HTTP_X_ORIGIN_CREDENTIAL=ORIGIN)


def create_user(
    username: str,
    role: str = "HELPDESK",
    *,
    active: bool = True,
    must_change: bool = False,
) -> User:
    return User.objects.create_user(
        username=username,
        password=DEFAULT_PASSWORD,
        full_name=username.title(),
        role=role,
        is_active=active,
        must_change_password=must_change,
    )


def authenticated_client(user: User, password: str = DEFAULT_PASSWORD) -> APIClient:
    api = api_client()
    response = api.post("/api/v1/auth/login", {"username": user.username, "password": password})
    assert response.status_code == 200
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {response.json()['access']}")
    return api


def manager_client(username: str = "manager") -> tuple[APIClient, User]:
    manager = create_user(username, "MANAGER")
    return authenticated_client(manager), manager
