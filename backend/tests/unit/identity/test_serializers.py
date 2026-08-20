import pytest

from identity.adapters.api.serializers import ProfileSerializer, UserCreateSerializer


@pytest.mark.unit
@pytest.mark.parametrize("blank", ["", "   "])
def test_optional_contact_blanks_normalize_to_null(blank: str) -> None:
    create = UserCreateSerializer(
        data={
            "username": "worker",
            "full_name": "Worker",
            "role": "HELPDESK",
            "phone": blank,
            "email": blank,
        }
    )
    profile = ProfileSerializer(data={"phone": blank, "email": blank}, partial=True)

    assert create.is_valid(), create.errors
    assert profile.is_valid(), profile.errors
    assert create.validated_data["phone"] is None
    assert create.validated_data["email"] is None
    assert profile.validated_data["phone"] is None
    assert profile.validated_data["email"] is None


@pytest.mark.unit
def test_optional_email_still_rejects_invalid_nonblank_value() -> None:
    serializer = ProfileSerializer(data={"email": "invalid"}, partial=True)

    assert not serializer.is_valid()
    assert "email" in serializer.errors
