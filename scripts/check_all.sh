#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
export ORIGIN_CREDENTIAL_HEADER="X-Origin-Credential"
export ORIGIN_CREDENTIAL="test-origin-credential-at-least-32-chars"
export WEB_PUSH_VAPID_PUBLIC_KEY="test-web-push-public-key"
export WEB_PUSH_VAPID_PRIVATE_KEY="test-web-push-private-key"
export WEB_PUSH_VAPID_SUBJECT="mailto:test@example.invalid"
export PUSH_SUBSCRIPTION_ENCRYPTION_KEY="MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="

maintainability_paths=(backend/core backend/config backend/operations backend/identity backend/audit backend/locations backend/attendance backend/tasks backend/notifications scripts frontend/src/shared/api/client.ts)
if [[ -n "${CHECK_ALL_MAINTAINABILITY_PATH:-}" ]]; then
  maintainability_paths=("$CHECK_ALL_MAINTAINABILITY_PATH")
fi

uv run --project backend ruff format --check backend scripts
uv run --project backend ruff check backend scripts
uv run --project backend mypy backend/core backend/config backend/operations backend/identity backend/audit backend/locations backend/attendance backend/tasks backend/notifications scripts
uv run --project backend python scripts/check_function_length.py "${maintainability_paths[@]}"
scripts/check_feature_002_convergence.sh --all
uv run --project backend pytest backend/tests/unit backend/tests/architecture backend/tests/contract backend/tests/integration/api
uv run --project backend pytest -m postgres backend/tests/integration/postgres
uv run --project backend python scripts/generate_openapi.py --check
uv run --project backend python scripts/check_openapi.py --all
uv run --project backend python scripts/check_contract_drift.py
uv run --project backend python scripts/migration_check.py check
uv run --project backend python scripts/deployment_check.py isolation
scripts/check_openapi_compatibility.sh
npm --prefix frontend run api:check
npm --prefix frontend run format:check
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run test
npm --prefix frontend run build
