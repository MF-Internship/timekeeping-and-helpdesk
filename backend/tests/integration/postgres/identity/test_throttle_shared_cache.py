from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.core.cache.backends.db import DatabaseCache
from django.db import close_old_connections
from rest_framework.test import APIRequestFactory

from core.cache import THROTTLE_CACHE_TABLE
from core.errors import IdentityAPIError
from identity.adapters.api.throttles import LoginThrottle


class FixedTimeLoginThrottle(LoginThrottle):
    timer = staticmethod(lambda: 1_000.0)


def _database_cache() -> DatabaseCache:
    return DatabaseCache(THROTTLE_CACHE_TABLE, {"OPTIONS": {}})


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.integration
def test_competing_workers_share_one_database_cache_quota() -> None:
    workers = 24
    barrier = Barrier(workers)
    _database_cache().clear()

    def attempt(_index: int) -> str:
        close_old_connections()
        try:
            throttle = FixedTimeLoginThrottle()
            throttle.cache = _database_cache()
            request = APIRequestFactory().post("/", {}, REMOTE_ADDR="192.0.2.44")
            barrier.wait()
            try:
                throttle.allow_request(request, object())
            except IdentityAPIError as error:
                return error.error_code
            return "ALLOWED"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        outcomes = list(executor.map(attempt, range(workers)))

    assert outcomes.count("ALLOWED") == 10
    assert outcomes.count("THROTTLED") == workers - 10
