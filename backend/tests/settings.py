import os

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://app_runtime:local_runtime_only@127.0.0.1:5432/timekeeping",
)
os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key-longer-than-thirty-two-characters")
os.environ.setdefault("DJANGO_DEBUG", "false")
os.environ.setdefault("API_DOCS_ENABLED", "true")
os.environ.setdefault("DJANGO_CACHE_BACKEND", "locmem")
os.environ.setdefault("REDIS_URL", "rediss://user:password@redis.invalid/0")
os.environ.setdefault("REDIS_KEY_PREFIX", "timekeeping-test")
os.environ.setdefault("R2_BUCKET", "timekeeping-test")
os.environ.setdefault("ORIGIN_CREDENTIAL_HEADER", "X-Origin-Credential")
os.environ.setdefault("ORIGIN_CREDENTIAL", "test-origin-credential-at-least-32-chars")

from config.settings import *  # noqa: F403
