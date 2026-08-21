#!/usr/bin/env bash
set -euo pipefail

mode="${1:---all}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
export ORIGIN_CREDENTIAL_HEADER="X-Origin-Credential"
export ORIGIN_CREDENTIAL="test-origin-credential-at-least-32-chars"

case "$mode" in
  --all|--fast)
    run_backend=true
    run_frontend=true
    ;;
  --backend)
    run_backend=true
    run_frontend=false
    ;;
  --frontend)
    run_backend=false
    run_frontend=true
    ;;
  *)
    echo "usage: scripts/check_feature_002_convergence.sh [--fast|--all|--backend|--frontend]" >&2
    exit 2
    ;;
esac

if [[ "$run_backend" == true ]]; then
  uv run --project backend pytest -q \
    backend/tests/unit/identity/test_authentication_services.py \
    backend/tests/unit/identity/test_self_service.py \
    backend/tests/unit/identity/test_user_admin.py \
    backend/tests/unit/identity/test_throttles.py \
    backend/tests/contract/identity/test_api_contract.py
fi

if [[ "$run_frontend" == true ]]; then
  npm --prefix frontend run test -- --run \
    tests/unit/errors/api-error.test.ts \
    tests/unit/messages.test.ts \
    tests/unit/identity/auth-forms.test.tsx
fi

if [[ "$mode" == "--fast" || "$mode" == "--frontend" ]]; then
  exit 0
fi

uv run --project backend pytest -q \
  backend/tests/integration/api/identity/test_logout.py \
  backend/tests/integration/api/identity/test_user_mutations.py \
  backend/tests/integration/api/identity/test_reset_password.py \
  backend/tests/integration/api/identity/test_auth_throttles.py \
  backend/tests/integration/api/identity/test_access_expiry.py

uv run --project backend pytest -q \
  backend/tests/integration/postgres/identity/test_login_vs_logout.py \
  backend/tests/integration/postgres/identity/test_login_vs_password_reset.py \
  backend/tests/integration/postgres/identity/test_login_vs_self_password_change.py \
  backend/tests/integration/postgres/identity/test_login_vs_deactivation.py \
  backend/tests/integration/postgres/identity/test_refresh_vs_logout.py \
  backend/tests/integration/postgres/identity/test_refresh_vs_password_reset.py \
  backend/tests/integration/postgres/identity/test_refresh_vs_self_password_change.py \
  backend/tests/integration/postgres/identity/test_refresh_vs_deactivation.py \
  backend/tests/integration/postgres/identity/test_revocation_first_races.py \
  backend/tests/integration/postgres/identity/test_throttle_shared_cache.py \
  backend/tests/integration/postgres/identity/test_concurrent_global_revocation.py
