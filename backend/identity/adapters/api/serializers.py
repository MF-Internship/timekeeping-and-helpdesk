from __future__ import annotations

from typing import Any, cast

from rest_framework import serializers

from core.error_codes import SERVER_OWNED_FIELD
from core.errors import IdentityAPIError
from identity.domain.accounts import AccountSnapshot
from identity.domain.authorization import Role, effective_capabilities


class StrictInputSerializer(serializers.Serializer[Any]):
    allowed_fields: frozenset[str] = frozenset()
    server_owned_fields: frozenset[str] = frozenset()

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict):
            return cast(dict[str, Any], super().to_internal_value(data))
        unexpected = set(data) - self.allowed_fields
        if unexpected:
            raise IdentityAPIError(
                SERVER_OWNED_FIELD,
                status_code=400,
            )
        return cast(dict[str, Any], super().to_internal_value(data))


class LoginSerializer(StrictInputSerializer):
    allowed_fields = frozenset({"username", "password"})
    username = serializers.CharField(allow_blank=False)
    password = serializers.CharField(allow_blank=False, trim_whitespace=False, write_only=True)


class EmptySerializer(StrictInputSerializer):
    allowed_fields = frozenset()


class RuntimeRoleField(serializers.CharField):
    def to_internal_value(self, data: Any) -> str:
        value = super().to_internal_value(data)
        try:
            Role(value)
        except ValueError as error:
            raise serializers.ValidationError("Vai trò không hợp lệ.") from error
        return value


class NullableBlankCharField(serializers.CharField):
    def run_validation(self, data: Any = serializers.empty) -> str | None:
        if isinstance(data, str) and not data.strip():
            return None
        return cast(str | None, super().run_validation(data))


class NullableBlankEmailField(serializers.EmailField):
    def run_validation(self, data: Any = serializers.empty) -> str | None:
        if isinstance(data, str) and not data.strip():
            return None
        return cast(str | None, super().run_validation(data))


class ProfileSerializer(StrictInputSerializer):
    allowed_fields = frozenset({"full_name", "phone", "email"})
    full_name = serializers.CharField(required=False, allow_blank=False)
    phone = NullableBlankCharField(required=False, allow_null=True, allow_blank=True)
    email = NullableBlankEmailField(required=False, allow_null=True, allow_blank=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if not attrs:
            raise serializers.ValidationError({"non_field_errors": ["Cần ít nhất một trường."]})
        return attrs


class PasswordChangeSerializer(StrictInputSerializer):
    allowed_fields = frozenset({"current_password", "new_password"})
    current_password = serializers.CharField(trim_whitespace=False, write_only=True)
    new_password = serializers.CharField(trim_whitespace=False, write_only=True)


class UserCreateSerializer(StrictInputSerializer):
    allowed_fields = frozenset({"username", "full_name", "phone", "email", "role"})
    username = serializers.CharField(allow_blank=False)
    full_name = serializers.CharField(allow_blank=False)
    phone = NullableBlankCharField(required=False, allow_null=True, allow_blank=True)
    email = NullableBlankEmailField(required=False, allow_null=True, allow_blank=True)
    role = RuntimeRoleField()


class RoleSerializer(StrictInputSerializer):
    allowed_fields = frozenset({"role"})
    role = RuntimeRoleField()


class StatusSerializer(StrictInputSerializer):
    allowed_fields = frozenset({"is_active"})
    is_active = serializers.BooleanField()


class AdminUserSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    phone = serializers.CharField(read_only=True, allow_null=True)
    email = serializers.EmailField(read_only=True, allow_null=True)
    role = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    must_change_password = serializers.BooleanField(read_only=True)
    last_login = serializers.DateTimeField(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)


class SelfUserSerializer(AdminUserSerializer):
    capabilities = serializers.ListField(child=serializers.CharField(), read_only=True)


class LoginResponseSerializer(serializers.Serializer[Any]):
    access = serializers.CharField(read_only=True)
    role = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    must_change_password = serializers.BooleanField(read_only=True)
    capabilities = serializers.ListField(child=serializers.CharField(), read_only=True)


class AccessResponseSerializer(serializers.Serializer[Any]):
    access = serializers.CharField(read_only=True)


class GeneratedUserResultSerializer(serializers.Serializer[Any]):
    user = AdminUserSerializer(read_only=True)
    generated_password = serializers.CharField(read_only=True)


class ResetPasswordResultSerializer(serializers.Serializer[Any]):
    user_id = serializers.IntegerField(read_only=True)
    must_change_password = serializers.BooleanField(read_only=True)
    generated_password = serializers.CharField(read_only=True)


class UserPageSerializer(serializers.Serializer[Any]):
    count = serializers.IntegerField(read_only=True)
    next = serializers.CharField(read_only=True, allow_null=True)
    previous = serializers.CharField(read_only=True, allow_null=True)
    results = AdminUserSerializer(many=True, read_only=True)


class IdentityErrorSerializer(serializers.Serializer[Any]):
    error_code = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)
    details = serializers.DictField(read_only=True)
    request_id = serializers.UUIDField(read_only=True)
    error = serializers.CharField(read_only=True)


def admin_user(account: AccountSnapshot) -> dict[str, Any]:
    return {
        "id": account.id,
        "username": account.username,
        "full_name": account.full_name,
        "phone": account.phone,
        "email": account.email,
        "role": account.role.value,
        "is_active": account.is_active,
        "must_change_password": account.must_change_password,
        "last_login": account.last_login,
        "created_at": account.created_at,
    }


def self_user(account: AccountSnapshot) -> dict[str, Any]:
    value = admin_user(account)
    value["capabilities"] = sorted(action.value for action in effective_capabilities(account.role))
    return value
