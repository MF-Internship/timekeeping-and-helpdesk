import pytest

from identity.models import User


@pytest.mark.unit
def test_user_model_has_only_canonical_business_fields() -> None:
    fields = {field.name for field in User._meta.fields}
    assert {
        "id",
        "username",
        "password",
        "full_name",
        "phone",
        "email",
        "role",
        "is_active",
        "must_change_password",
        "last_login",
        "created_at",
    } == fields
    assert User._meta.get_field("username").unique
    assert User._meta.get_field("phone").null
    assert User._meta.get_field("email").null
