import pytest

from identity.models import User
from tests.integration.api.identity.helpers import manager_client


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
@pytest.mark.parametrize(
    "payload,code",
    [
        ({"username": "missing-role", "full_name": "Missing"}, "VALIDATION_FAILED"),
        (
            {"username": "bad-email", "full_name": "Bad", "role": "HELPDESK", "email": "bad"},
            "VALIDATION_FAILED",
        ),
        ({"username": "manager", "full_name": "Manager", "role": "MANAGER"}, "PERMISSION_DENIED"),
        (
            {"username": "owned", "full_name": "Owned", "role": "HELPDESK", "is_active": False},
            "SERVER_OWNED_FIELD",
        ),
    ],
)
def test_create_rejects_invalid_or_server_owned_inputs(
    payload: dict[str, object], code: str
) -> None:
    api, _manager = manager_client(f"create-{code.lower()}")
    before = User.objects.count()
    response = api.post("/api/v1/users/", payload)
    assert response.json()["error_code"] == code
    assert User.objects.count() == before


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_duplicate_username_is_rejected_while_duplicate_optional_contacts_are_allowed() -> None:
    api, _manager = manager_client("duplicate-manager")
    payload = {
        "username": "duplicate-worker",
        "full_name": "Worker",
        "role": "HELPDESK",
        "phone": "0900000000",
        "email": "shared@example.com",
    }
    assert api.post("/api/v1/users/", payload).status_code == 201
    duplicate = api.post("/api/v1/users/", payload)
    assert duplicate.status_code == 400
    assert duplicate.json()["error_code"] == "VALIDATION_FAILED"
    payload["username"] = "second-worker"
    assert api.post("/api/v1/users/", payload).status_code == 201


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_create_blank_contacts_are_persisted_and_returned_as_null() -> None:
    api, _manager = manager_client("blank-create-manager")

    response = api.post(
        "/api/v1/users/",
        {
            "username": "blank-create-worker",
            "full_name": "Worker",
            "role": "HELPDESK",
            "phone": " ",
            "email": "",
        },
    )

    assert response.status_code == 201
    assert response.json()["user"]["phone"] is None
    assert response.json()["user"]["email"] is None
    created = User.objects.get(username="blank-create-worker")
    assert created.phone is None and created.email is None
