from __future__ import annotations

import base64
import binascii
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
    allowed_hosts: tuple[str, ...]
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
    web_push_vapid_public_key: str
    web_push_vapid_private_key: str
    web_push_vapid_subject: str
    push_subscription_encryption_keys: tuple[str, ...]
    web_push_enabled: bool
    web_push_allowed_origins: tuple[str, ...]


def load_runtime_settings(values: Mapping[str, str]) -> RuntimeSettings:
    environment = _environment(values)
    database_url = _required(values, "DATABASE_URL")
    _validate_postgresql_url(database_url, "DATABASE_URL")
    secret_key = _required(values, "DJANGO_SECRET_KEY")
    origin_credential = _origin_credential(values)
    redis_url, redis_key_prefix, bucket = _resource_values(values, environment)
    web_push = _web_push_values(values, environment)
    return RuntimeSettings(
        environment=environment,
        allowed_hosts=_allowed_hosts(values, environment),
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
        web_push_vapid_public_key=web_push[0],
        web_push_vapid_private_key=web_push[1],
        web_push_vapid_subject=web_push[2],
        push_subscription_encryption_keys=web_push[3],
        web_push_enabled=web_push[4],
        web_push_allowed_origins=web_push[5],
    )


def _web_push_values(
    values: Mapping[str, str], environment: EnvironmentName
) -> tuple[str, str, str, tuple[str, ...], bool, tuple[str, ...]]:
    defaults = (
        "development-vapid-public-key",
        "development-vapid-private-key",
        "mailto:development@example.invalid",
        "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
    )
    keys = (
        "WEB_PUSH_VAPID_PUBLIC_KEY",
        "WEB_PUSH_VAPID_PRIVATE_KEY",
        "WEB_PUSH_VAPID_SUBJECT",
        "PUSH_SUBSCRIPTION_ENCRYPTION_KEY",
    )
    resolved, enabled, origins_raw = _resolve_web_push_strings(values, environment, keys, defaults)
    if not enabled:
        return resolved[0], resolved[1], resolved[2], (), False, ()
    encryption_keys, origins = _validate_enabled_web_push(resolved, origins_raw)
    return resolved[0], resolved[1], resolved[2], encryption_keys, enabled, origins


def _validate_enabled_web_push(
    resolved: tuple[str, ...], origins_raw: str
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    subject = resolved[2]
    if not subject.startswith(("mailto:", "https://")):
        raise ConfigurationError("WEB_PUSH_VAPID_SUBJECT")
    _validate_vapid_pair(resolved[0], resolved[1])
    encryption_keys = tuple(item.strip() for item in resolved[3].split(",") if item.strip())
    if not encryption_keys:
        raise ConfigurationError("PUSH_SUBSCRIPTION_ENCRYPTION_KEY")
    for encryption_key in encryption_keys:
        _validate_encryption_key(encryption_key)
    origins = tuple(part.strip() for part in origins_raw.split(",") if part.strip())
    if not origins or any(not _is_exact_https_origin(origin) for origin in origins):
        raise ConfigurationError("WEB_PUSH_ALLOWED_ORIGINS")
    return encryption_keys, origins


def _validate_encryption_key(value: str) -> None:
    try:
        decoded = base64.urlsafe_b64decode(value.encode("ascii"))
    except (ValueError, UnicodeEncodeError, binascii.Error) as error:
        raise ConfigurationError("PUSH_SUBSCRIPTION_ENCRYPTION_KEY") from error
    if len(decoded) != 32:
        raise ConfigurationError("PUSH_SUBSCRIPTION_ENCRYPTION_KEY")


def _validate_vapid_pair(public_value: str, private_value: str) -> None:
    try:
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        from py_vapid import Vapid02  # type: ignore[import-untyped]

        vapid = Vapid02.from_string(private_value)
        derived = vapid.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        encoded = base64.urlsafe_b64encode(derived).rstrip(b"=").decode("ascii")
    except (ValueError, TypeError, UnicodeError) as error:
        raise ConfigurationError(
            "WEB_PUSH_VAPID_PUBLIC_KEY", "WEB_PUSH_VAPID_PRIVATE_KEY"
        ) from error
    if encoded != public_value.rstrip("="):
        raise ConfigurationError("WEB_PUSH_VAPID_PUBLIC_KEY", "WEB_PUSH_VAPID_PRIVATE_KEY")


def _resolve_web_push_strings(
    values: Mapping[str, str],
    environment: EnvironmentName,
    keys: tuple[str, ...],
    defaults: tuple[str, ...],
) -> tuple[tuple[str, ...], bool, str]:
    if environment is EnvironmentName.DEVELOPMENT:
        resolved = tuple(
            values.get(key, default) for key, default in zip(keys, defaults, strict=True)
        )
        enabled_raw = values.get("WEB_PUSH_ENABLED", "false").casefold()
        if enabled_raw not in {"true", "false"}:
            raise ConfigurationError("WEB_PUSH_ENABLED")
        return (
            resolved,
            enabled_raw == "true",
            values.get("WEB_PUSH_ALLOWED_ORIGINS", "https://push.example.invalid"),
        )
    enabled = _boolean(values, "WEB_PUSH_ENABLED")
    if not enabled:
        return tuple(values.get(key, "") for key in keys), False, ""
    resolved = tuple(_required(values, key) for key in keys)
    return resolved, enabled, _required(values, "WEB_PUSH_ALLOWED_ORIGINS")


def _is_exact_https_origin(value: str) -> bool:
    parsed = urlsplit(value)
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
        and parsed.path in ("", "/")
        and not parsed.query
        and not parsed.fragment
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


def _allowed_hosts(values: Mapping[str, str], environment: EnvironmentName) -> tuple[str, ...]:
    if environment is EnvironmentName.DEVELOPMENT:
        raw = values.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost,testserver")
    else:
        raw = _required(values, "DJANGO_ALLOWED_HOSTS")
    hosts = tuple(item.strip() for item in raw.split(",") if item.strip())
    if not hosts or any(
        host == "*" or "://" in host or "/" in host or any(char.isspace() for char in host)
        for host in hosts
    ):
        raise ConfigurationError("DJANGO_ALLOWED_HOSTS")
    return hosts


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
