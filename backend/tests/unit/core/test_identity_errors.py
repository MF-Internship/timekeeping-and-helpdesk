from core.error_codes import (
    ACCOUNT_INACTIVE,
    INVALID_CREDENTIALS,
    INVALID_TOKEN,
    PASSWORD_CHANGE_REQUIRED,
    SERVER_OWNED_FIELD,
    SERVICE_UNAVAILABLE,
    THROTTLED,
)
from core.messages import ERROR_MESSAGES


def test_identity_errors_have_centralized_vietnamese_messages() -> None:
    identity_codes = {
        INVALID_CREDENTIALS,
        INVALID_TOKEN,
        ACCOUNT_INACTIVE,
        PASSWORD_CHANGE_REQUIRED,
        SERVER_OWNED_FIELD,
        THROTTLED,
        SERVICE_UNAVAILABLE,
    }
    assert identity_codes <= ERROR_MESSAGES.keys()
    assert all(ERROR_MESSAGES[code].strip() for code in identity_codes)
