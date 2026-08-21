# Quickstart: Release Hardening

Run from the repository root.

## Prerequisites

- Node.js 22 and npm
- Python 3.12 and uv
- PostgreSQL 17 test service matching the CI identity/database contract
- Git Bash or another POSIX shell on Windows

Install dependencies without modifying locks:

```bash
uv sync --project backend --locked
npm --prefix frontend ci
```

Export isolated PostgreSQL test DSNs and scoped non-production settings described by `.env.example`. Do not use production credentials.

## Targeted checks

```bash
npm --prefix frontend run format:check
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run test
npm --prefix frontend run build

uv run --project backend ruff format --check backend scripts
uv run --project backend ruff check backend scripts
uv run --project backend mypy backend/core backend/config backend/operations backend/identity backend/audit backend/locations backend/attendance backend/tasks backend/notifications scripts
uv run --project backend python scripts/migration_check.py check
uv run --project backend python backend/manage.py makemigrations --check --dry-run --settings=tests.settings
uv run --project backend python scripts/generate_openapi.py --check
uv run --project backend python scripts/check_openapi.py --all
npm --prefix frontend run api:check
uv run --project backend python scripts/check_contract_drift.py
uv run --project backend python scripts/deployment_check.py isolation
```

## Full gate

```bash
scripts/check_all.sh
```

Expected: every machine-verifiable category passes, committed locks/contracts remain unchanged, and the repository remains clean except for intentional Feature 016 changes.

The 2026-08-21 clean-run simulation removed disposable build/test/tool caches, completed `uv sync --locked` and `npm ci`, and used an isolated PostgreSQL 17 service. Local shells must use Node 22 as declared by `.nvmrc`; running another major is a detectable environment mismatch even when the tests are deliberately robust to it.

`production-ready` and `recovery-ready` are expected to remain non-green while Feature 014/016 real-environment evidence is pending. See `docs/DEFERRED_WORK.md`.
