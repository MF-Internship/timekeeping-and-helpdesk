from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.cache import caches
from rest_framework.test import APIRequestFactory

from core.cache import THROTTLE_CACHE_ALIAS
from core.errors import IdentityAPIError
from identity.adapters.api.throttles import (
    LoginThrottle,
    PasswordChangeThrottle,
    RefreshThrottle,
)


@pytest.fixture(autouse=True)
def clear_throttle_cache() -> None:
    caches[THROTTLE_CACHE_ALIAS].clear()


def _request(ip: str = "192.0.2.1", user_id: int | None = None):
    request = APIRequestFactory().post("/", {}, REMOTE_ADDR=ip)
    request.user = None if user_id is None else SimpleNamespace(pk=user_id)
    return request


@pytest.mark.parametrize(
    ("throttle_type", "limit", "user_id"),
    [(LoginThrottle, 10, None), (RefreshThrottle, 120, None), (PasswordChangeThrottle, 5, 7)],
)
def test_exact_limits_and_retry_after_use_controlled_time(
    throttle_type: type[LoginThrottle], limit: int, user_id: int | None
) -> None:
    now = 1_000.0
    request = _request(user_id=user_id)
    with patch.object(throttle_type, "timer", return_value=now):
        for _ in range(limit):
            assert throttle_type().allow_request(request, object()) is True
        with pytest.raises(IdentityAPIError) as caught:
            throttle_type().allow_request(request, object())
        assert caught.value.error_code == "THROTTLED"
        assert caught.value.headers == {"Retry-After": "60"}

    with patch.object(throttle_type, "timer", return_value=now + 60):
        assert throttle_type().allow_request(request, object()) is True


def test_client_ip_and_user_keys_are_isolated_and_shared_across_instances() -> None:
    first = _request("192.0.2.10")
    second = _request("192.0.2.11")
    for _ in range(10):
        LoginThrottle().allow_request(first, object())
    assert LoginThrottle().allow_request(second, object()) is True

    user_one = _request(user_id=1)
    user_two = _request(user_id=2)
    for _ in range(5):
        PasswordChangeThrottle().allow_request(user_one, object())
    assert PasswordChangeThrottle().allow_request(user_two, object()) is True


def test_cache_failure_is_fail_closed() -> None:
    with (
        patch.object(LoginThrottle.cache, "get", side_effect=RuntimeError("unavailable")),
        pytest.raises(IdentityAPIError) as caught,
    ):
        LoginThrottle().allow_request(_request(), object())
    assert caught.value.error_code == "SERVICE_UNAVAILABLE"
    assert caught.value.status_code == 503


def test_cache_write_failure_is_fail_closed() -> None:
    with (
        patch.object(LoginThrottle.cache, "set", return_value=False),
        pytest.raises(IdentityAPIError) as caught,
    ):
        LoginThrottle().allow_request(_request(), object())
    assert caught.value.error_code == "SERVICE_UNAVAILABLE"
    assert caught.value.status_code == 503
