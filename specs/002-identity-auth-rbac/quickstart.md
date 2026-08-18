# Quickstart Validation: Identity, Authentication and Canonical RBAC

This is a post-implementation validation guide, not implementation code. Expected behavior is defined by [api.md](./contracts/api.md), [events.md](./contracts/events.md), [frontend.md](./contracts/frontend.md), and [data-model.md](./data-model.md).

## Prerequisites

- Python 3.12 with `uv`
- Node.js 22 and npm
- Docker/Compose for PostgreSQL 17
- Repository-local development environment configured from `.env.example`; do not put real credentials in commands, shell history, screenshots, or artifacts

## Install locked dependencies

```bash
uv sync --project backend --locked
npm --prefix frontend ci
```

Expected: SimpleJWT is present through the backend lock; no unapproved broker, auth SDK, frontend state library, or alternate HTTP client is installed.

## Start PostgreSQL and apply migrations

```bash
docker compose up -d postgres
uv run --project backend python backend/manage.py migrate
uv run --project backend python scripts/migration_check.py check
```

Expected:

- PostgreSQL becomes healthy.
- Operations, identity, audit, Django auth, and token-blacklist migrations apply with one leaf per local app.
- Custom User is configured before auth/blacklist foreign keys.
- Migration safety reports no unapproved owner, missing DDL default, mixed contraction, or multiple leaf.

## Run focused backend verification

Pure policy/application tests:

```bash
uv run --project backend pytest backend/tests/unit/identity backend/tests/unit/audit
```

Expected: exact Role × Action matrix, five implications and grant provenance, assignable roles, Leader read-only behavior, Manager no check-in/out, password rules, action/target authorization before the forced-password gate and DTO validation, and safe audit/event payloads pass. Identity contains no Task/Attendance ownership policy.

HTTP contract tests:

```bash
uv run --project backend pytest backend/tests/integration/api/identity
```

Expected: login/refresh/logout, self/password flows, user administration, action-before-forced-password-before-DTO, target-before-forced-password-before-DTO, canonical errors, cookie attributes, list filters/pagination, and allow/deny scenarios pass. Logout succeeds only with a valid bearer access credential plus a valid, unrevoked, same-user refresh cookie; missing, malformed, expired, mismatched, or already-revoked refresh returns `INVALID_TOKEN` without success evidence.

Real PostgreSQL evidence:

```bash
POSTGRES_TEST_DATABASE_URL="$DATABASE_URL" uv run --project backend pytest -m postgres backend/tests/integration/postgres/identity backend/tests/integration/postgres/audit
```

Expected: tests assert PostgreSQL vendor and use real competing workers/transactions to prove migrations, constraints/triggers, duplicate-username race, same-refresh reuse/race, login issuance versus each of logout/reset/self-change/deactivation, refresh issuance versus each of those four revocations, concurrent global revocations for one User, concurrent unique monotonic per-User outbox aggregate-version allocation, Manager-target race protection, audit immutability, and full rollback after append. Final persisted state and credential usability are asserted; no SQLite/mock result counts as evidence.

## Validate the Definition of Done scenarios

Run the feature acceptance suite:

```bash
uv run --project backend pytest backend/tests/integration/api/identity backend/tests/integration/postgres/identity backend/tests/integration/postgres/audit
```

The suite must prove together:

1. Active login succeeds; unknown/wrong/inactive login returns identical INVALID_CREDENTIALS.
2. Refresh rotates, old refresh reuse is denied, and a same-token race has at most one winner.
3. Logout on one device revokes refresh on every device while an existing access credential follows the canonical 15-minute/account-state rule.
4. `is_active=false` is checked on the next request and returns ACCOUNT_INACTIVE.
5. A generated password can login repeatedly without TTL but every non-change protected endpoint returns PASSWORD_CHANGE_REQUIRED.
6. Self password change revokes old refresh first, then returns a new usable session.
7. Manager reset sets must_change_password, revokes all refresh, and never stores/logs/audits/events plaintext.
8. Existing Manager targets remain readable and reject profile/role/status/reset writes, including malformed and empty bodies.
9. Leader mutations and Helpdesk user administration are denied without side effects.
10. The complete direct/effective RBAC matrix and generic grant provenance match CHOT, with no implicit all-to-self grant beyond the five approved pairs and no Task/Attendance record-ownership behavior in Identity.

## Validate generated contracts

After explicitly regenerating artifacts as part of the implementation change:

```bash
uv run --project backend python scripts/generate_openapi.py --check
uv run --project backend python scripts/check_openapi.py --all
npm --prefix frontend run api:check
uv run --project backend python scripts/check_contract_drift.py
scripts/check_openapi_compatibility.sh
```

Expected:

- All identity paths/operation IDs match `contracts/api.md`.
- Generation is deterministic and committed OpenAPI/generated `schema.ts` are current; handwritten `client.ts` passes type/static verification.
- Role/capabilities are open strings.
- No JSON refresh, password response/create/reset/profile property, cookie value, credential example, or sensitive audit/event value appears; exact `password` is present only in the canonical login request schema.
- The additive v1 change passes merge-base compatibility.

## Validate frontend session and administration

```bash
npm --prefix frontend run format:check
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run test
npm --prefix frontend run build
```

Expected frontend tests prove:

- access/account state is memory-only;
- page bootstrap uses refresh then `/me/`;
- concurrent invalid-token responses share one refresh and replay at most once;
- inactive and forced-password-change outcomes do not loop;
- canonical capabilities gate navigation/actions without replacing backend security;
- generated password is cleared on dismissal/unmount/logout/account switch;
- all API calls cross the existing authenticatedFetch/openapi client path.

## Record non-CI usability and capacity evidence

After the feature is implemented, run the approved operator workflow and existing capacity tool. Record only reproducible, non-secret evidence in `evidence/usability.md` and `evidence/capacity.md`:

- a Manager completes create, search/filter, eligible profile/role/status change, and password reset within two minutes;
- the existing approved capacity tool runs with at least 50 test identities and concurrency 20 and records measured p95 results against the 500 ms target.

These measurements are evidence tasks, not CI gates, and must not be represented as production measurements.

## Run architecture and complete repository gates

```bash
uv run --project backend pytest backend/tests/architecture
uv run --project backend mypy backend/core backend/config backend/operations backend/identity backend/audit scripts
uv run --project backend python scripts/check_function_length.py backend/core backend/config backend/operations backend/identity backend/audit scripts frontend/src/shared/api/client.ts
./scripts/check_all.sh
```

Expected:

- approved local apps/persistence owners are exactly operations, identity, and audit;
- config/core remain non-apps;
- domain code has no framework imports;
- no cross-module models/domain/adapters imports occur;
- audit/outbox are not hidden in identity/core/operations;
- all quality, tests, contracts, migrations, isolation, generated artifacts, and frontend build checks pass.

## Security inspection

Run the automated sensitive-output suites and inspect only structural paths, never secret values:

```bash
uv run --project backend pytest backend/tests/contract/test_openapi_safety.py backend/tests/contract/identity backend/tests/integration/api/identity -q
npm --prefix frontend run test -- --run tests/unit/identity tests/contract/identity
```

Expected zero plaintext generated-password/token/cookie/JTI occurrences in logs, AuditLog, OutboxEvent, exceptions, generated examples, browser storage, or rendered post-dismissal UI. A failed payload filter names only the violating path and rolls back the whole use case.

## Final migration compatibility check

The PostgreSQL migration suite must explicitly start from the feature-001 migration graph and advance to feature 002. Verify:

- old feature-001 runtime has no dependency on new tables;
- new tables/constraints/triggers are additive;
- no stock auth user table was previously adopted;
- auth/token blacklist foreign keys resolve to identity.User;
- each local app has one leaf;
- no reverse/destructive migration is part of deployment;
- deployment order remains migrate first, then roll out new application processes.
