from __future__ import annotations

import os
from datetime import timedelta
from importlib.util import find_spec
from pathlib import Path
from urllib.parse import unquote, urlsplit

from core.cache import (
    THROTTLE_CACHE_ALIAS,
    THROTTLE_CACHE_TABLE,
    cache_backend_path,
    is_process_local_backend,
)
from core.deployment import (
    ConfigurationError,
    EnvironmentName,
    RuntimeSettings,
    load_runtime_settings,
)

BASE_DIR = Path(__file__).resolve().parent.parent
RUNTIME = load_runtime_settings(os.environ)


def _database_configuration(dsn: str) -> dict[str, str | int]:
    parsed = urlsplit(dsn)
    configuration: dict[str, str | int] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path.lstrip("/")),
        "HOST": parsed.hostname or "",
        "PORT": parsed.port or 5432,
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
    }
    return configuration


def _cache_configuration(runtime: RuntimeSettings) -> dict[str, dict[str, object]]:
    backend = cache_backend_path(runtime.cache_backend)
    if runtime.environment is not EnvironmentName.DEVELOPMENT and is_process_local_backend(backend):
        raise ConfigurationError("DJANGO_CACHE_BACKEND")
    if runtime.cache_backend == "redis" and find_spec("redis") is None:
        raise ConfigurationError("DJANGO_CACHE_BACKEND")
    location = {
        "locmem": THROTTLE_CACHE_ALIAS,
        "database": THROTTLE_CACHE_TABLE,
        "redis": runtime.redis_url,
    }[runtime.cache_backend]
    return {THROTTLE_CACHE_ALIAS: {"BACKEND": backend, "LOCATION": location}}


SECRET_KEY = RUNTIME.secret_key
DEBUG = RUNTIME.debug
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "rest_framework",
    "drf_spectacular",
    "rest_framework_simplejwt.token_blacklist",
    "operations",
    "identity",
    "audit",
    "locations",
]

MIDDLEWARE = [
    "core.middleware.RequestIdentityMiddleware",
    "core.middleware.OriginCredentialMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {"default": _database_configuration(RUNTIME.database_url)}
CACHES = _cache_configuration(RUNTIME)

API_DOCS_ENABLED = RUNTIME.api_docs_enabled
ORIGIN_CREDENTIAL_HEADER = RUNTIME.origin_credential_header
ORIGIN_CREDENTIAL = RUNTIME.origin_credential
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "identity.adapters.security.authentication.DatabaseBackedJWTAuthentication"
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
    "UNAUTHENTICATED_TOKEN": None,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "core.errors.drf_exception_handler",
}
AUTH_USER_MODEL = "identity.User"
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Timekeeping and Helpdesk API",
    "VERSION": "1.0.0",
    "OAS_VERSION": "3.0.3",
    "COMPONENT_SPLIT_PATCH": False,
    "SERVE_INCLUDE_SCHEMA": True,
    "ENUM_GENERATE_CHOICE_DESCRIPTION": False,
    "APPEND_COMPONENTS": {
        "schemas": {
            "FoundationError": {
                "type": "object",
                "required": ["error_code", "message", "details", "request_id", "error"],
                "properties": {
                    "error_code": {
                        "type": "string",
                        "description": "Governance-authorized error code.",
                    },
                    "message": {"type": "string"},
                    "details": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "request_id": {"type": "string", "format": "uuid"},
                    "error": {"type": "string", "deprecated": True},
                },
            }
        }
    },
}
CSRF_FAILURE_VIEW = "config.handlers.csrf_failure"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"correlation": {"()": "core.logging.CorrelationFilter"}},
    "formatters": {
        "correlated": {
            "format": (
                "%(levelname)s %(name)s request_id=%(request_id)s "
                "correlation_id=%(correlation_id)s %(message)s"
            )
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["correlation"],
            "formatter": "correlated",
        }
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}

LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
