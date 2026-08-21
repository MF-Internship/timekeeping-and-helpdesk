# Contract: Machine-Verifiable Release Gate

## Entry point

`scripts/check_all.sh` is the repository-root full release gate.

## Preconditions

- Supported Node, Python, and PostgreSQL versions are available.
- npm and uv dependencies are installed from committed locks without mutation.
- `DATABASE_URL` and `POSTGRES_TEST_DATABASE_URL` identify an isolated PostgreSQL test service.
- Only scoped non-production values are supplied for required backend configuration.
- Git merge-base history is available for API compatibility checks.

## Required ordered categories

1. Backend format check, lint, strict types, maintainability, architecture/convergence.
2. Backend unit, architecture, contract, API integration, PostgreSQL integration, and concurrency tests.
3. Backend OpenAPI generation, schema safety, drift, compatibility, migration safety, and deployment isolation.
4. Frontend generated-schema drift, format check, lint, strict types, unit/architecture/contract tests, and production build.

The entry point exits non-zero on the first required failure and does not modify authored or generated source.

## Write/fix commands

- Frontend formatting: `npm --prefix frontend run format`
- Backend formatting: `uv run --project backend ruff format backend scripts`
- Backend safe lint fixes: `uv run --project backend ruff check --fix backend scripts`
- Generated frontend schema: `npm --prefix frontend run api:generate`

Write/fix commands are developer actions and are never invoked by CI.

## Non-goals

- The gate does not deploy staging or production.
- The gate does not fabricate secrets, backup/restore evidence, capacity evidence, device evidence, DNS/TLS state, or external Web Push delivery.
- The gate does not treat `production-ready` or `recovery-ready` as passing while mandatory evidence is unresolved.
