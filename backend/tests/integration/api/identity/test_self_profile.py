import pytest

from tests.integration.api.identity.helpers import authenticated_client, create_user


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_self_profile_is_actor_derived_and_rejects_server_owned_identity() -> None:
    manager = create_user("self-manager", "MANAGER")
    other = create_user("other")
    api = authenticated_client(manager)
    updated = api.patch("/api/v1/me/", {"full_name": "Updated Manager"})
    assert updated.status_code == 200
    assert updated.json()["id"] == manager.pk
    denied = api.patch("/api/v1/me/", {"user_id": other.pk, "username": "other"})
    assert denied.status_code == 400
    assert denied.json()["error_code"] == "SERVER_OWNED_FIELD"


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_self_profile_blank_contacts_are_persisted_and_returned_as_null() -> None:
    user = create_user("blank-self")
    user.phone = "0900"
    user.email = "self@example.com"
    user.save(update_fields=["phone", "email"])

    response = authenticated_client(user).patch("/api/v1/me/", {"phone": " ", "email": ""})

    assert response.status_code == 200
    assert response.json()["phone"] is None
    assert response.json()["email"] is None
    user.refresh_from_db()
    assert user.phone is None and user.email is None
