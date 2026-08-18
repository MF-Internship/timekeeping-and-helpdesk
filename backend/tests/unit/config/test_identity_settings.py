from datetime import timedelta

import pytest
from django.conf import settings


@pytest.mark.unit
def test_identity_authentication_settings_are_canonical() -> None:
    assert settings.AUTH_USER_MODEL == "identity.User"
    assert {
        "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
        "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
        "ROTATE_REFRESH_TOKENS": True,
        "BLACKLIST_AFTER_ROTATION": True,
        "UPDATE_LAST_LOGIN": True,
    } == settings.SIMPLE_JWT
