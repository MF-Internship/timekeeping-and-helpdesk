#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

maintainability_paths=(backend/core backend/config backend/operations backend/identity backend/audit scripts frontend/src/shared/api/client.ts)
if [[ -n "${CHECK_ALL_MAINTAINABILITY_PATH:-}" ]]; then
  maintainability_paths=("$CHECK_ALL_MAINTAINABILITY_PATH")
fi

uv run --project backend ruff format --check backend scripts
uv run --project backend ruff check backend scripts
uv run --project backend mypy backend/core backend/config backend/operations backend/identity backend/audit scripts
uv run --project backend python scripts/check_function_length.py "${maintainability_paths[@]}"
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
