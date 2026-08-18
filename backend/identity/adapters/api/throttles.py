from __future__ import annotations

import math
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from hashlib import blake2b
from threading import RLock
from typing import Any, cast

from django.core.cache import caches
from django.core.cache.backends.base import BaseCache
from django.core.cache.backends.db import DatabaseCache
from django.core.cache.backends.locmem import LocMemCache
from django.core.cache.backends.redis import RedisCache
from django.db import connections, router, transaction
from rest_framework.throttling import SimpleRateThrottle

from core.cache import THROTTLE_CACHE_ALIAS
from core.error_codes import SERVICE_UNAVAILABLE, THROTTLED
from core.errors import IdentityAPIError

_LOCAL_SERIALIZATION_LOCK = RLock()


def _stable_lock_id(key: str) -> int:
    digest = blake2b(key.encode(), digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=True)


@contextmanager
def _database_serialization(cache: DatabaseCache, key: str) -> Iterator[None]:
    database = router.db_for_write(cache.cache_model_class)
    lock_id = _stable_lock_id(cache.make_key(key))
    with transaction.atomic(using=database):
        with connections[database].cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [lock_id])
        yield


@contextmanager
def _redis_serialization(cache: RedisCache, key: str) -> Iterator[None]:
    lock_key = cache.make_key(f"{key}:serialization")
    client = cast(Any, cache)._cache.get_client(lock_key, write=True)
    lock = client.lock(lock_key, timeout=5, blocking_timeout=5)
    with lock:
        yield


@contextmanager
def _local_serialization() -> Iterator[None]:
    with _LOCAL_SERIALIZATION_LOCK:
        yield


def _cache_serialization(cache: BaseCache, key: str) -> AbstractContextManager[None]:
    if isinstance(cache, DatabaseCache):
        return _database_serialization(cache, key)
    if isinstance(cache, RedisCache):
        return _redis_serialization(cache, key)
    if isinstance(cache, LocMemCache):
        return _local_serialization()
    raise RuntimeError("Unsupported throttle cache backend")


class CanonicalRateThrottle(SimpleRateThrottle):
    cache = caches[THROTTLE_CACHE_ALIAS]
    duration: int
    num_requests: int

    def allow_request(self, request: Any, view: Any) -> bool:
        if self.rate is None:
            return True
        key = self.get_cache_key(request, view)
        if key is None:
            return True
        self.key = key
        self.now = self.timer()
        try:
            with _cache_serialization(self.cache, key):
                allowed = self._record_attempt()
        except Exception as error:
            raise IdentityAPIError(SERVICE_UNAVAILABLE, status_code=503) from error
        if allowed:
            return True
        retry_after = max(1, math.ceil(self.wait() or 1))
        throttle_error = IdentityAPIError(THROTTLED, status_code=429)
        throttle_error.headers["Retry-After"] = str(retry_after)
        raise throttle_error

    def _record_attempt(self) -> bool:
        self.history = self.cache.get(self.key, [])
        while self.history and self.history[-1] <= self.now - self.duration:
            self.history.pop()
        if len(self.history) >= self.num_requests:
            return False
        self.history.insert(0, self.now)
        stored = cast(Any, self.cache).set(self.key, self.history, self.duration)
        if stored is False:
            raise RuntimeError("Throttle cache write failed")
        return True


class ClientIPThrottle(CanonicalRateThrottle):
    def get_cache_key(self, request: Any, view: Any) -> str:
        canonical_ip = str(request.META.get("REMOTE_ADDR", ""))
        return self.cache_format % {"scope": self.scope, "ident": canonical_ip}


class LoginThrottle(ClientIPThrottle):
    scope = "login"


class RefreshThrottle(ClientIPThrottle):
    scope = "refresh"


class PasswordChangeThrottle(CanonicalRateThrottle):
    scope = "password_change"

    def get_cache_key(self, request: Any, view: Any) -> str | None:
        user_id = getattr(getattr(request, "user", None), "pk", None)
        if user_id is None:
            return None
        return self.cache_format % {"scope": self.scope, "ident": str(user_id)}
