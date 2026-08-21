#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

export APP_ENV="${APP_ENV:-development}"
export DATABASE_URL="${DATABASE_URL:-postgresql://runtime_check:runtime_check@127.0.0.1:5432/timekeeping_check}"
export DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-release-check-only-secret-key-at-least-32-characters}"
export DJANGO_DEBUG="${DJANGO_DEBUG:-false}"
export API_DOCS_ENABLED="${API_DOCS_ENABLED:-true}"
export DJANGO_CACHE_BACKEND="${DJANGO_CACHE_BACKEND:-locmem}"
export REDIS_URL="${REDIS_URL:-rediss://release-check:release-check@redis.invalid/0}"
export REDIS_KEY_PREFIX="${REDIS_KEY_PREFIX:-timekeeping-development-release-check}"
export R2_BUCKET="${R2_BUCKET:-timekeeping-development-release-check}"
export ORIGIN_CREDENTIAL_HEADER="${ORIGIN_CREDENTIAL_HEADER:-X-Origin-Credential}"
export ORIGIN_CREDENTIAL="${ORIGIN_CREDENTIAL:-release-check-origin-credential-at-least-32-chars}"
export WEB_PUSH_ENABLED="${WEB_PUSH_ENABLED:-false}"

uv run --project backend python backend/manage.py check

(
    export APP_ENV="production"
    export DJANGO_ALLOWED_HOSTS="release-check.invalid"
    export DATABASE_URL="postgresql://runtime_check:runtime_check@db.release-check.invalid/timekeeping"
    export DJANGO_SECRET_KEY="release-check-only-9f2e4d6c8b1a3e5f7d0c2b4a6e8f1d3c"
    export DJANGO_DEBUG="false"
    export API_DOCS_ENABLED="false"
    export DJANGO_CACHE_BACKEND="database"
    export REDIS_URL="rediss://release-check:release-check@redis.release-check.invalid/0"
    export REDIS_KEY_PREFIX="timekeeping-production-release-check"
    export R2_BUCKET="timekeeping-production-release-check"
    export S3_ENDPOINT="https://storage.release-check.invalid"
    export S3_ACCESS_KEY_ID="release-check-access-key"
    export S3_SECRET_ACCESS_KEY="release-check-secret-key"
    export WEB_PUSH_ENABLED="false"
    uv run --project backend python backend/manage.py check --deploy --fail-level WARNING
)
