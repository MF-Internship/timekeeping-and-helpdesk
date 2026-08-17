from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlsplit

from core.cache import CACHE_BACKEND_CHOICES


class EnvironmentName(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class ConfigurationError(ValueError):
    def __init__(self, *keys: str) -> None:
        self.keys = keys
        super().__init__(f"invalid configuration: {', '.join(keys)}")


@dataclass(frozen=True, slots=True)
class RuntimeSettings:
    environment: EnvironmentName
    database_url: str
    secret_key: str
    debug: bool
    api_docs_enabled: bool
    cache_backend: str
    redis_url: str
    redis_key_prefix: str
    bucket: str
    origin_credential_header: str
    origin_credential: str


def load_runtime_settings(values: Mapping[str, str]) -> RuntimeSettings:
    environment = _environment(values)
    database_url = _required(values, "DATABASE_URL")
    _validate_postgresql_url(database_url, "DATABASE_URL")
    secret_key = _required(values, "DJANGO_SECRET_KEY")
    origin_credential = _origin_credential(values)
    redis_url, redis_key_prefix, bucket = _resource_values(values, environment)
    return RuntimeSettings(
        environment=environment,
        database_url=database_url,
        secret_key=secret_key,
        debug=_boolean(values, "DJANGO_DEBUG"),
        api_docs_enabled=_boolean(values, "API_DOCS_ENABLED"),
        cache_backend=_cache_backend(values, environment),
        redis_url=redis_url,
        redis_key_prefix=redis_key_prefix,
        bucket=bucket,
        origin_credential_header=_required(values, "ORIGIN_CREDENTIAL_HEADER"),
        origin_credential=origin_credential,
    )


def _origin_credential(values: Mapping[str, str]) -> str:
    credential = _required(values, "ORIGIN_CREDENTIAL")
    if len(credential) < 32:
        raise ConfigurationError("ORIGIN_CREDENTIAL")
    if values.get("REDIS_RESULT_BACKEND_URL"):
        raise ConfigurationError("REDIS_RESULT_BACKEND_URL")
    return credential


def _resource_values(
    values: Mapping[str, str], environment: EnvironmentName
) -> tuple[str, str, str]:
    redis_url = _required(values, "REDIS_URL")
    redis_key_prefix = _required(values, "REDIS_KEY_PREFIX")
    bucket = _required(values, "R2_BUCKET")
    if environment is not EnvironmentName.DEVELOPMENT:
        _validate_non_development_resources(
            environment,
            redis_url=redis_url,
            redis_key_prefix=redis_key_prefix,
            bucket=bucket,
        )
    return redis_url, redis_key_prefix, bucket


def dsn_identity(dsn: str, key: str) -> tuple[str, int | None, str, str | None]:
    _validate_postgresql_url(dsn, key)
    parsed = urlsplit(dsn)
    return parsed.hostname or "", parsed.port, parsed.path.lstrip("/"), parsed.username


def validate_database_separation(runtime_dsn: str, admin_dsn: str) -> None:
    if dsn_identity(runtime_dsn, "DATABASE_URL") == dsn_identity(
        admin_dsn,
        "DATABASE_ADMIN_URL",
    ):
        raise ConfigurationError("DATABASE_URL", "DATABASE_ADMIN_URL")


def _environment(values: Mapping[str, str]) -> EnvironmentName:
    raw = _required(values, "APP_ENV")
    try:
        return EnvironmentName(raw)
    except ValueError as error:
        raise ConfigurationError("APP_ENV") from error


def _required(values: Mapping[str, str], key: str) -> str:
    value = values.get(key)
    if value is None or not value.strip() or value == "UNRESOLVED":
        raise ConfigurationError(key)
    return value


def _boolean(values: Mapping[str, str], key: str) -> bool:
    raw = _required(values, key).casefold()
    if raw == "true":
        return True
    if raw == "false":
        return False
    raise ConfigurationError(key)


def _cache_backend(values: Mapping[str, str], environment: EnvironmentName) -> str:
    if "DJANGO_CACHE_BACKEND" not in values and environment is EnvironmentName.DEVELOPMENT:
        return "locmem"
    choice = _required(values, "DJANGO_CACHE_BACKEND")
    if choice not in CACHE_BACKEND_CHOICES:
        raise ConfigurationError("DJANGO_CACHE_BACKEND")
    return choice


def _validate_postgresql_url(value: str, key: str) -> None:
    parsed = urlsplit(value)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname or not parsed.path:
        raise ConfigurationError(key)


def _validate_non_development_resources(
    environment: EnvironmentName,
    *,
    redis_url: str,
    redis_key_prefix: str,
    bucket: str,
) -> None:
    parsed = urlsplit(redis_url)
    if parsed.scheme != "rediss" or parsed.password is None:
        raise ConfigurationError("REDIS_URL")
    if environment.value not in redis_key_prefix:
        raise ConfigurationError("REDIS_KEY_PREFIX")
    if environment.value not in bucket:
        raise ConfigurationError("R2_BUCKET")
