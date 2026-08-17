# Quickstart Target: Project Foundation and API Contract Baseline

This is the developer workflow the implementation must make possible. The current planning change does not create these commands or install dependencies.

## Prerequisites

- Python 3.12 and uv
- Node.js 22 LTS and npm
- Docker with Compose, or an equivalent local PostgreSQL 17 service
- Git (compatibility checks need a merge base)

## Configure and install

```bash
docker compose up -d postgres
uv sync --project backend --locked
npm --prefix frontend ci
```

Create an untracked application-runtime environment file from `.env.example` and fill only development values. It contains the normal PostgreSQL identity and must not contain the migration-admin key. If a migration command needs privileged credentials, inject them into that separate process using `deploy/migration.env.example`; never source them into the web application. Never place production credentials or full provider connection strings in `deploy/environments.yaml`. The runtime and migration-admin URLs must identify different PostgreSQL principals.

## Validate the backend

```bash
uv run --project backend python backend/manage.py check
uv run --project backend pytest backend/tests/unit backend/tests/architecture backend/tests/contract
uv run --project backend pytest -m postgres backend/tests/integration
uv run --project backend ruff format --check backend scripts
uv run --project backend ruff check backend scripts
uv run --project backend mypy backend/core backend/config backend/operations
```

The PostgreSQL-marked run must fail if PostgreSQL is unavailable or the active Django vendor is not `postgresql`.

## Validate generated contracts

```bash
uv run --project backend python scripts/generate_openapi.py --check
uv run --project backend python scripts/check_openapi.py --all
npm --prefix frontend run api:check
uv run --project backend python scripts/migration_check.py check
uv run --project backend python scripts/deployment_check.py isolation
```

To intentionally update an accepted additive contract, run the explicit OpenAPI update command first, review `contracts/openapi.yaml`, then update the frontend artifact and review `frontend/src/shared/api/schema.ts`. Check mode must never rewrite either file.

`deployment_check.py production-ready` and `deployment_check.py recovery-ready`
are expected to fail while approved production choices or operator measurements
remain `UNRESOLVED`; they list only safe manifest paths. They, `smoke`, and
`capacity_check.py measure` are operator checks rather than CI gates. Only
`isolation` and `migration_check.py check` are wired into contract CI.

Before any restore verification, provide `RECOVERY_DATABASE_URL` only to the
command process. The command must reject an identity equal to `DATABASE_URL` or
`DATABASE_ADMIN_URL` before opening a connection and must run read-only:

```bash
uv run --project backend python backend/manage.py verify_restore
```

Capacity measurement requires an untracked `*.identities` file with at least 50
distinct real accounts and concurrency at least 20. Store one short-lived access
token per distinct account on each line; the command sends it only as a Bearer
credential to an operator-selected HTTPS, idempotent `/api/v1/` probe. Run:

```bash
uv run --project backend python scripts/capacity_check.py measure \
  --identities operator-capacity.identities \
  --concurrency 20 \
  --target-url https://staging.example.invalid/api/v1/capacity-probe/ \
  --remediation-owner platform-operations \
  --output capacity-result.json
```

Eligible evidence requires
p95 at most 500 ms; a result above 500 ms is failed and requires a remediation
owner. Inputs below either minimum fail before network activity. Every opened
connection/resource must close on success and failure, and identities,
passwords, tokens, Bearer values, credentialed URLs, and secret values must be
absent from stdout, stderr, and result artifacts. Do not run it merely to make
the repository green; controlled fixtures and command output are not evidence
and cannot make production/recovery readiness true. Real results are recorded
only through the signed operator procedure in `docs/TRIEN_KHAI.md`.

The shipped staging/production cache selection is `database`. The static and
PostgreSQL checks must prove that its table is provisioned by the approved
`operations` migration, that settings use the same canonical table identity,
and that neither `config/` nor `core/` is a Django app.

## Validate the frontend

```bash
npm --prefix frontend run format:check
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend test
npm --prefix frontend run build
```

Frontend architecture tests prove that generated and handwritten API wrappers use `authenticatedFetch`, and shared state tests distinguish loading, empty, canonical failure, unexpected response, and network failure.

## Start and probe

With `API_DOCS_ENABLED=true` in development:

```bash
uv run --project backend python backend/manage.py runserver
npm --prefix frontend run dev
curl -i http://127.0.0.1:3000/api/v1/schema/
curl -i http://127.0.0.1:8000/api/v1/schema/
```

The frontend-proxy response on port 3000 is machine-readable, carries a server-generated
`X-Request-Id`, and has `Cache-Control: private, no-store`. Browser traffic uses
the Next proxy, which strips any client source-credential header before attaching
the server-held value. The second, direct-origin request on port 8000 intentionally
receives the canonical 403 because it has no source credential. With
`API_DOCS_ENABLED=false`, the schema route is absent.

The status-only smoke formatter accepts only the already-observed status and
must not print response headers or bodies:

```bash
uv run --project backend python scripts/deployment_check.py smoke --status 200
```

## Full local gate

The repository should expose one documented aggregate command that runs the same required checks as CI. On a clean checkout with prerequisites ready, setup, validation, application startup, and the schema/frontend transport probe must fit within the 15-minute success criterion.
