from typing import Any

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken, TokenError
from rest_framework_simplejwt.settings import api_settings

from core.error_codes import ACCOUNT_INACTIVE, INVALID_TOKEN
from core.errors import IdentityAPIError
from identity.models import User


class DatabaseBackedJWTAuthentication(JWTAuthentication):
    """JWT authentication whose user lookup always reads current database state."""

    def authenticate(self, request: Any) -> Any:
        try:
            result = super().authenticate(request)
        except (AuthenticationFailed, InvalidToken, TokenError) as error:
            raise IdentityAPIError(INVALID_TOKEN, status_code=401) from error
        return result

    def get_user(self, validated_token: Any) -> Any:
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
            user = User.objects.get(**{api_settings.USER_ID_FIELD: user_id})
        except (KeyError, TypeError, ValueError, User.DoesNotExist) as error:
            raise IdentityAPIError(INVALID_TOKEN, status_code=401) from error
        if not user.is_active:
            raise IdentityAPIError(ACCOUNT_INACTIVE, status_code=401)
        return user
