from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from audit.models import AuditLog, OutboxEvent
from identity.domain.authorization import Role, effective_capabilities
from identity.models import User

ORIGIN = "test-origin-credential-at-least-32-chars"


def client() -> APIClient:
    return APIClient(HTTP_X_ORIGIN_CREDENTIAL=ORIGIN)


def user(
    username: str,
    role: str,
    **options: object,
) -> User:
    return User.objects.create_user(
        username=username,
        password=str(options.get("password", "SafePassword123!")),
        full_name=username.title(),
        role=role,
        must_change_password=bool(options.get("must_change", False)),
        is_active=bool(options.get("active", True)),
    )


def login(api: APIClient, username: str, password: str = "SafePassword123!") -> object:
    return api.post("/api/v1/auth/login", {"username": username, "password": password})


def assert_refresh_denied(raw_refresh: str) -> None:
    stale = client()
    stale.cookies["refresh_token"] = raw_refresh
    denied = stale.post("/api/v1/auth/refresh", {})
    assert denied.status_code == 401
    assert denied.json()["error_code"] == "INVALID_TOKEN"


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_login_refresh_rotation_and_reuse_denial() -> None:
    user("help", "HELPDESK")
    api = client()
    response = login(api, "help")
    assert response.status_code == 200
    assert "refresh" not in response.json()
    assert set(response.json()) == {
        "access",
        "role",
        "is_active",
        "must_change_password",
        "capabilities",
    }
    old = api.cookies["refresh_token"].value
    assert api.cookies["refresh_token"]["httponly"] is True
    assert api.cookies["refresh_token"]["secure"] is True
    assert api.cookies["refresh_token"]["samesite"] == "Strict"
    assert api.cookies["refresh_token"]["path"] == "/api/v1/auth/"

    rotated = api.post("/api/v1/auth/refresh", {})
    assert rotated.status_code == 200
    assert set(rotated.json()) == {"access"}
    assert api.cookies["refresh_token"].value != old

    attacker = client()
    attacker.cookies["refresh_token"] = old
    denied = attacker.post("/api/v1/auth/refresh", {})
    assert denied.status_code == 401
    assert denied.json()["error_code"] == "INVALID_TOKEN"
    assert "refresh_token" not in denied.cookies


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_access_claims_and_controlled_expiry_boundary() -> None:
    user("claims", "HELPDESK")
    response = login(client(), "claims")
    token = AccessToken(response.json()["access"], verify=False)
    assert set(token.payload) == {"user_id", "exp", "jti", "token_type"}
    expiry = datetime.fromtimestamp(int(token["exp"]), tz=UTC)
    token.check_exp(current_time=expiry - timedelta(microseconds=1))
    with pytest.raises(TokenError):
        token.check_exp(current_time=expiry)


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_login_and_me_capabilities_match_the_canonical_policy_for_every_role() -> None:
    for role in Role:
        account = user(f"cap-{role.value.lower()}", role.value)
        api = client()
        signed_in = login(api, account.username)
        expected = sorted(action.value for action in effective_capabilities(role))
        assert signed_in.json()["capabilities"] == expected
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {signed_in.json()['access']}")
        assert api.get("/api/v1/me/").json()["capabilities"] == expected


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_login_failures_are_non_enumerating_and_inactive_access_is_checked() -> None:
    inactive = user("inactive", "HELPDESK", active=False)
    api = client()
    unknown = login(api, "missing")
    wrong = login(api, "inactive", "WrongPassword123!")
    locked = login(api, "inactive")
    assert [
        (item.status_code, item.json()["error_code"], item.json()["message"])
        for item in (unknown, wrong, locked)
    ] == [
        (401, "INVALID_CREDENTIALS", unknown.json()["message"]),
        (401, "INVALID_CREDENTIALS", unknown.json()["message"]),
        (401, "INVALID_CREDENTIALS", unknown.json()["message"]),
    ]

    inactive.is_active = True
    inactive.save(update_fields=["is_active"])
    signed_in = login(api, "inactive")
    access = signed_in.json()["access"]
    inactive.is_active = False
    inactive.save(update_fields=["is_active"])
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    denied = api.get("/api/v1/me/")
    assert denied.status_code == 401
    assert denied.json()["error_code"] == "ACCOUNT_INACTIVE"


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_refresh_rejects_missing_malformed_expired_and_invalid_signature_cases() -> None:
    account = user("refresh-cases", "HELPDESK")
    api = client()
    login(api, account.username)
    valid_refresh = api.cookies["refresh_token"].value
    invalid_parts = valid_refresh.split(".")
    invalid_parts[2] = ("A" if invalid_parts[2][0] != "A" else "B") + invalid_parts[2][1:]
    invalid_signature = ".".join(invalid_parts)

    for raw in (None, "malformed", invalid_signature):
        candidate = client()
        if raw is not None:
            candidate.cookies["refresh_token"] = raw
        denied = candidate.post("/api/v1/auth/refresh", {})
        assert denied.status_code == 401
        assert denied.json()["error_code"] == "INVALID_TOKEN"
        assert "refresh_token" not in denied.cookies

    expired = RefreshToken.for_user(account)
    expired.set_exp(lifetime=timedelta(seconds=-1))
    expired_client = client()
    expired_client.cookies["refresh_token"] = str(expired)
    assert expired_client.post("/api/v1/auth/refresh", {}).json()["error_code"] == "INVALID_TOKEN"


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_refresh_rejects_body_injection_inactive_and_forced_accounts() -> None:
    account = user("refresh-state", "HELPDESK")
    api = client()
    signed_in = login(api, account.username)
    valid_refresh = api.cookies["refresh_token"].value
    injected = api.post("/api/v1/auth/refresh", {"refresh_token": valid_refresh})
    assert injected.status_code == 400
    assert injected.json()["error_code"] == "SERVER_OWNED_FIELD"

    account.must_change_password = True
    account.save(update_fields=["must_change_password"])
    forced = api.post("/api/v1/auth/refresh", {})
    assert forced.status_code == 403
    assert forced.json()["error_code"] == "PASSWORD_CHANGE_REQUIRED"
    account.must_change_password = False
    account.is_active = False
    account.save(update_fields=["must_change_password", "is_active"])
    inactive = api.post("/api/v1/auth/refresh", {})
    assert inactive.status_code == 401
    assert inactive.json()["error_code"] == "ACCOUNT_INACTIVE"
    assert signed_in.json()["access"]


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_authorization_and_manager_target_precede_password_and_payload() -> None:
    helpdesk = user("forced-help", "HELPDESK", must_change=True)
    manager = user("manager", "MANAGER", must_change=True)
    api = client()

    help_login = login(api, helpdesk.username)
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {help_login.json()['access']}")
    unauthorized = api.post("/api/v1/users/", {})
    assert unauthorized.status_code == 403
    assert unauthorized.json()["error_code"] == "PERMISSION_DENIED"

    manager_login = login(api, manager.username)
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {manager_login.json()['access']}")
    forced = api.post("/api/v1/users/", {})
    assert forced.status_code == 403
    assert forced.json()["error_code"] == "PASSWORD_CHANGE_REQUIRED"

    manager.must_change_password = False
    manager.save(update_fields=["must_change_password"])
    manager_login = login(api, manager.username)
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {manager_login.json()['access']}")
    protected = api.patch(f"/api/v1/users/{manager.pk}/", {"role": "HELPDESK"})
    assert protected.status_code == 403
    assert protected.json()["error_code"] == "PERMISSION_DENIED"
    assert AuditLog.objects.count() == 0
    assert OutboxEvent.objects.count() == 0

    for method, path in (
        (api.patch, f"/api/v1/users/{manager.pk}/role"),
        (api.patch, f"/api/v1/users/{manager.pk}/status"),
        (api.post, f"/api/v1/users/{manager.pk}/reset-password"),
    ):
        denied = method(path, {"unexpected": "value"})
        assert denied.status_code == 403
        assert denied.json()["error_code"] == "PERMISSION_DENIED"


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_password_change_revokes_old_refresh_and_returns_working_pair() -> None:
    account = user("forced", "HELPDESK", must_change=True)
    api = client()
    signed_in = login(api, account.username)
    old_refresh = api.cookies["refresh_token"].value
    access = signed_in.json()["access"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert api.get("/api/v1/me/").json()["error_code"] == "PASSWORD_CHANGE_REQUIRED"

    changed = api.post(
        "/api/v1/change-password",
        {"current_password": "SafePassword123!", "new_password": "NewSafePassword456!"},
    )
    assert changed.status_code == 200
    new_refresh = api.cookies["refresh_token"].value
    assert new_refresh != old_refresh
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {changed.json()['access']}")
    assert api.get("/api/v1/me/").status_code == 200

    api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert api.get("/api/v1/me/").status_code == 200

    old_client = client()
    old_client.cookies["refresh_token"] = old_refresh
    assert old_client.post("/api/v1/auth/refresh", {}).json()["error_code"] == "INVALID_TOKEN"
    assert api.post("/api/v1/auth/refresh", {}).status_code == 200


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_manager_admin_happy_path() -> None:
    manager = user("manager-admin", "MANAGER")
    api = client()
    signed_in = login(api, manager.username)
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {signed_in.json()['access']}")

    created = api.post(
        "/api/v1/users/",
        {"username": "worker", "full_name": "Worker", "role": "HELPDESK"},
    )
    assert created.status_code == 201
    initial_password = created.json()["generated_password"]
    assert "generated_password" not in created.json()["user"]
    target_id = created.json()["user"]["id"]
    directory = api.get("/api/v1/users/?q=worker&role=HELPDESK&is_active=true")
    assert directory.status_code == 200
    assert [item["id"] for item in directory.json()["results"]] == [target_id]
    profile = api.patch(f"/api/v1/users/{target_id}/", {"full_name": "Updated Worker"})
    assert profile.status_code == 200
    assert api.patch(f"/api/v1/users/{target_id}/role", {"role": "LEADER"}).status_code == 200
    assert api.patch(f"/api/v1/users/{target_id}/status", {"is_active": False}).status_code == 200
    reset = api.post(f"/api/v1/users/{target_id}/reset-password", {})
    assert reset.status_code == 200
    reset_password = reset.json()["generated_password"]
    assert reset_password != initial_password
    persisted_evidence = str(list(AuditLog.objects.values())) + str(
        list(OutboxEvent.objects.values())
    )
    assert initial_password not in persisted_evidence
    assert reset_password not in persisted_evidence


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_generated_password_can_login_repeatedly_but_business_gate_remains() -> None:
    manager = user("generated-manager", "MANAGER")
    admin = client()
    manager_login = login(admin, manager.username)
    admin.credentials(HTTP_AUTHORIZATION=f"Bearer {manager_login.json()['access']}")
    created = admin.post(
        "/api/v1/users/",
        {"username": "generated-worker", "full_name": "Worker", "role": "HELPDESK"},
    )
    generated = created.json()["generated_password"]
    for _ in range(2):
        worker = client()
        signed_in = login(worker, "generated-worker", generated)
        assert signed_in.status_code == 200
        worker.credentials(HTTP_AUTHORIZATION=f"Bearer {signed_in.json()['access']}")
        blocked = worker.get("/api/v1/me/")
        assert blocked.status_code == 403
        assert blocked.json()["error_code"] == "PASSWORD_CHANGE_REQUIRED"


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_logout_globally_revokes_two_devices_but_not_existing_access() -> None:
    manager = user("logout-manager", "MANAGER")
    first = client()
    first_login = login(first, manager.username)
    first_refresh = first.cookies["refresh_token"].value
    second = client()
    second_login = login(second, manager.username)
    second_refresh = second.cookies["refresh_token"].value
    first.credentials(HTTP_AUTHORIZATION=f"Bearer {first_login.json()['access']}")
    assert first.post("/api/v1/auth/logout", {}).status_code == 204
    for refresh in (first_refresh, second_refresh):
        assert_refresh_denied(refresh)
    second.credentials(HTTP_AUTHORIZATION=f"Bearer {second_login.json()['access']}")
    assert second.get("/api/v1/me/").status_code == 200


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_negative_filters_roles_server_fields_and_leader_mutation_denials() -> None:
    manager = user("negative-manager", "MANAGER")
    target = user("negative-target", "HELPDESK")
    api = client()
    signed_in = login(api, manager.username)
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {signed_in.json()['access']}")

    for query in ("role=ADMIN", "is_active=maybe", "page=0"):
        denied = api.get(f"/api/v1/users/?{query}")
        assert denied.status_code == 400
        assert denied.json()["error_code"] == "VALIDATION_FAILED"
    assert (
        api.post(
            "/api/v1/users/",
            {"username": "bad-email", "full_name": "Bad", "role": "HELPDESK", "email": "bad"},
        ).status_code
        == 400
    )
    manager_role = api.post(
        "/api/v1/users/",
        {"username": "forbidden-manager", "full_name": "No", "role": "MANAGER"},
    )
    assert manager_role.status_code == 403
    assert manager_role.json()["error_code"] == "PERMISSION_DENIED"
    injected = api.patch(f"/api/v1/users/{target.pk}/", {"role": "HELPDESK"})
    assert injected.status_code == 400
    assert injected.json()["error_code"] == "SERVER_OWNED_FIELD"
    self_injection = api.patch("/api/v1/me/", {"user_id": target.pk})
    assert self_injection.json()["error_code"] == "SERVER_OWNED_FIELD"

    leader = user("denied-leader", "LEADER")
    leader_api = client()
    leader_login = login(leader_api, leader.username)
    leader_api.credentials(HTTP_AUTHORIZATION=f"Bearer {leader_login.json()['access']}")
    denied = leader_api.post("/api/v1/users/", {})
    assert denied.status_code == 403
    assert denied.json()["error_code"] == "PERMISSION_DENIED"


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_logout_uses_access_actor_and_repeated_cookie_states_add_no_success_evidence() -> None:
    account = user("logout-contract", "HELPDESK")
    api = client()
    signed_in = login(api, account.username)
    raw_refresh = api.cookies["refresh_token"].value
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {signed_in.json()['access']}")
    del api.cookies["refresh_token"]
    missing = api.post("/api/v1/auth/logout", {})
    assert missing.status_code == 204
    assert AuditLog.objects.count() == 1
    evidence_count = AuditLog.objects.count()

    api.cookies["refresh_token"] = raw_refresh
    assert api.post("/api/v1/auth/logout", {}).status_code == 204
    assert AuditLog.objects.count() == evidence_count
    api.cookies["refresh_token"] = raw_refresh
    reused = api.post("/api/v1/auth/logout", {})
    assert reused.status_code == 204
    assert AuditLog.objects.count() == evidence_count
