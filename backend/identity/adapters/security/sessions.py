from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from django.db import IntegrityError
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from identity.models import User
from identity.ports.sessions import IssuedSession, RevocationReason


class InvalidSessionError(ValueError):
    pass


def _canonical_refresh(user: User) -> RefreshToken:
    token = RefreshToken.for_user(user)
    token.payload.pop("iat", None)
    return token


class SimpleJWTSessionRepository:
    def issue(self, user_id: int) -> IssuedSession:
        user = User.objects.select_for_update().get(pk=user_id)
        token = _canonical_refresh(user)
        access = token.access_token
        access.payload.pop("iat", None)
        return IssuedSession(access=str(access), refresh=str(token))

    def rotate(self, refresh: str) -> IssuedSession:
        try:
            old = RefreshToken(cast(Any, refresh))
            user_id = int(old["user_id"])
        except (TokenError, KeyError, TypeError, ValueError) as error:
            raise InvalidSessionError from error
        user = User.objects.select_for_update().get(pk=user_id)
        if not user.is_active:
            raise InvalidSessionError("inactive")
        if BlacklistedToken.objects.filter(token__jti=str(old["jti"])).exists():
            raise InvalidSessionError("consumed")
        try:
            old.blacklist()
        except (TokenError, IntegrityError) as error:
            raise InvalidSessionError from error
        token = _canonical_refresh(user)
        access = token.access_token
        access.payload.pop("iat", None)
        return IssuedSession(access=str(access), refresh=str(token))

    def revoke_all(self, user_id: int, reason: RevocationReason) -> int:
        User.objects.select_for_update().get(pk=user_id)
        outstanding = OutstandingToken.objects.filter(
            user_id=user_id,
            expires_at__gt=datetime.now(UTC),
            blacklistedtoken__isnull=True,
        )
        count = 0
        for token in outstanding.iterator():
            _, created = BlacklistedToken.objects.get_or_create(token=token)
            count += int(created)
        return count

    def refresh_owner(self, refresh: str) -> int:
        try:
            return int(RefreshToken(cast(Any, refresh))["user_id"])
        except (TokenError, KeyError, TypeError, ValueError) as error:
            raise InvalidSessionError from error
