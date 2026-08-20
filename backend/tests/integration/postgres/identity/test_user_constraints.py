from __future__ import annotations

import pytest
from django.db import DatabaseError, IntegrityError, connection, transaction

from identity.models import User


def create(username: str, **values: object) -> User:
    defaults = {"full_name": "A User", "role": "HELPDESK"}
    defaults.update(values)
    return User.objects.create(username=username, password="hash", **defaults)


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.integration
def test_user_constraints_defaults_and_contact_non_uniqueness() -> None:
    first = create("first", phone="123", email="shared@example.com")
    second = create("second", phone="123", email="shared@example.com")
    assert first.phone == second.phone
    assert first.email == second.email

    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO identity_user (password, username, full_name, role, created_at) "
            "VALUES ('hash', 'ddl-default', 'DDL Default', 'LEADER', now()) "
            "RETURNING is_active, must_change_password"
        )
        assert cursor.fetchone() == (True, True)

    for username, values in (
        ("first", {}),
        ("blank-user", {"full_name": "   "}),
        ("role-user", {"role": "ADMIN"}),
    ):
        with pytest.raises(IntegrityError), transaction.atomic():
            create(username, **values)
    with pytest.raises(DatabaseError), transaction.atomic():
        create("   ")


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.integration
def test_username_is_immutable_in_postgresql() -> None:
    account = create("immutable")
    account.username = "changed"
    with pytest.raises(DatabaseError), transaction.atomic():
        account.save(update_fields=["username"])
    account.refresh_from_db()
    assert account.username == "immutable"
