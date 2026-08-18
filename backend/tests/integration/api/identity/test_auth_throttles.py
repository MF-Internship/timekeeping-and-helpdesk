from unittest.mock import patch

import pytest
from django.core.cache import caches
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

from audit.models import AuditLog, OutboxEvent
from core.cache import THROTTLE_CACHE_ALIAS
from identity.adapters.api.throttles import LoginThrottle
from tests.integration.api.identity.helpers import api_client


@pytest.fixture(autouse=True)
def clear_throttle_cache() -> None:
    caches[THROTTLE_CACHE_ALIAS].clear()


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_login_over_limit_is_canonical_and_has_no_business_side_effect() -> None:
    api = api_client()
    for _ in range(10):
        response = api.post("/api/v1/auth/login", {"username": "missing", "password": "wrong"})
        assert response.status_code == 401

    limited = api.post("/api/v1/auth/login", {"username": "missing", "password": "wrong"})

    assert limited.status_code == 429
    assert limited.json()["error_code"] == "THROTTLED"
    assert int(limited["Retry-After"]) >= 1
    assert OutstandingToken.objects.count() == 0
    assert AuditLog.objects.count() == 0
    assert OutboxEvent.objects.count() == 0


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_throttle_cache_failure_is_canonical_and_fail_closed() -> None:
    with patch.object(LoginThrottle.cache, "get", side_effect=RuntimeError("unavailable")):
        response = api_client().post(
            "/api/v1/auth/login", {"username": "missing", "password": "wrong"}
        )

    assert response.status_code == 503
    assert response.json()["error_code"] == "SERVICE_UNAVAILABLE"
    assert OutstandingToken.objects.count() == 0
    assert AuditLog.objects.count() == 0
    assert OutboxEvent.objects.count() == 0
