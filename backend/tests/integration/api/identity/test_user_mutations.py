import pytest

from tests.integration.api.identity.helpers import create_user, manager_client


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_distinct_admin_mutations_accept_only_their_owned_fields() -> None:
    api, _manager = manager_client("mutation-manager")
    target = create_user("mutation-target")
    assert api.patch(f"/api/v1/users/{target.pk}/", {"full_name": "Updated"}).status_code == 200
    assert api.patch(f"/api/v1/users/{target.pk}/role", {"role": "LEADER"}).status_code == 200
    assert api.patch(f"/api/v1/users/{target.pk}/status", {"is_active": False}).status_code == 200
    injected = api.patch(f"/api/v1/users/{target.pk}/", {"role": "HELPDESK"})
    assert injected.status_code == 400
    assert injected.json()["error_code"] == "SERVER_OWNED_FIELD"
    missing = api.patch("/api/v1/users/999999/status", {"is_active": False})
    assert missing.status_code == 404


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_admin_mutations_reject_invalid_email_empty_and_body_injection() -> None:
    api, _manager = manager_client("mutation-negative-manager")
    target = create_user("mutation-negative-target")
    invalid_email = api.patch(f"/api/v1/users/{target.pk}/", {"email": "invalid"})
    assert invalid_email.status_code == 400
    assert invalid_email.json()["error_code"] == "VALIDATION_FAILED"
    empty_role = api.patch(f"/api/v1/users/{target.pk}/role", {})
    assert empty_role.status_code == 400
    injected = api.patch(
        f"/api/v1/users/{target.pk}/status", {"is_active": False, "user_id": target.pk}
    )
    assert injected.json()["error_code"] == "SERVER_OWNED_FIELD"


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_admin_profile_blank_contacts_are_persisted_and_returned_as_null() -> None:
    api, _manager = manager_client("blank-admin-manager")
    target = create_user("blank-admin-target")
    target.phone = "0900"
    target.email = "target@example.com"
    target.save(update_fields=["phone", "email"])

    response = api.patch(
        f"/api/v1/users/{target.pk}/",
        {"phone": "", "email": "   "},
    )

    assert response.status_code == 200
    assert response.json()["phone"] is None
    assert response.json()["email"] is None
    target.refresh_from_db()
    assert target.phone is None and target.email is None
