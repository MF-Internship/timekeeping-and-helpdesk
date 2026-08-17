# Implementation Plan: Project Foundation and API Contract Baseline

**Branch**: `001-project-api-foundation` (feature context reported by the setup script; current Git branch is `feature/001-project-foundation`) | **Date**: 2026-08-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-project-api-foundation/spec.md`

## Summary

Establish the empty repository's first executable web-application baseline: a Django REST Framework backend backed only by PostgreSQL, a Next.js frontend whose API traffic crosses one `authenticatedFetch` boundary, a narrow non-app `backend/core/` technical kernel, the approved `operations` owner for operational command discovery and cache-table provisioning, deterministic OpenAPI and generated TypeScript artifacts, and automated quality, compatibility, environment, cache, and migration-safety gates. The design intentionally creates no authentication, location, attendance, task, reporting, notification, audit/outbox business model, or placeholder business application and never turns `config/` or `core/` into a Django app.

## Technical Context

**Language/Version**: Python 3.12; TypeScript 5.x; Node.js 22 LTS

**Primary Dependencies**: Django 5.2 LTS, Django REST Framework 3.16, psycopg 3, drf-spectacular; Next.js 16, React 19, openapi-fetch, openapi-typescript

**Storage**: PostgreSQL 17 for local/CI verification; no SQLite fallback; one R-109 Django DatabaseCache table provisioned by the approved `operations` migration, with no business table

**Testing**: pytest, pytest-django, real-PostgreSQL integration tests; Vitest, Testing Library, jsdom; schema/client drift and compatibility fixtures

**Target Platform**: Linux application/CI runtime; modern browsers supported by Next.js 16

**Project Type**: Web application with separate backend and frontend projects plus committed contract artifacts

**Performance Goals**: A clean-checkout validation and probe workflow in 15 minutes or less; 10,000 UUIDv4 request IDs with no collisions or context leakage; deterministic byte-identical artifact generation

**Constraints**: `/api/v1/` only; `snake_case` wire names; server-generated request IDs; PostgreSQL-only database evidence; fail-closed configuration; no protected values in schema or diagnostics; no business feature implementation

**Scale/Scope**: One backend composition root, one frontend application, one OpenAPI contract, one generated TypeScript schema, shared technical primitives, and repository/CI tooling required by all later modules

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle / gate | Pre-design | Post-design evidence |
| --- | --- | --- |
| I. Source-of-truth governance | PASS | CHOT controls all decisions. R-103/104/106/107/108/109 are used only as accepted-decision rationale. QUY_TAC and the PRD are synchronized before the blocking implementation gate; the plan uses canonical `backend/core/`, approved `operations` ownership, and exact 50/20/500 capacity semantics. |
| II. Fixed stack and inward architecture | PASS | Django/DRF, PostgreSQL, and Next.js are fixed. Future business modules use `domain/application/ports/adapters`; architecture tests enforce inward and cross-module imports. No empty business modules are created. |
| III-IV. Authorization and boundary ownership | PASS (not applicable to a business flow) | There is no auth, RBAC, scoped object, or business DTO. The frontend transport stores no token and makes no authorization decision. Test-only views exercise the HTTP boundary without becoming public business APIs. |
| V. Database invariants and transactions | PASS (no business mutation) | No business model, constraint, index, lock, or transaction is introduced. The only technical table is the R-109 DatabaseCache table owned by an `operations` migration and verified on real PostgreSQL; later modules own their business transactions. |
| VI. Auditability and safe observability | PASS | Correlation, logging enrichment, and recursive payload safety are technical primitives. Business `AuditLog`, `OutboxEvent`, append ports, retries, and delivery remain deferred. Diagnostic failures are contained. |
| VII. Stable generated contracts | PASS | The backend generates committed `contracts/openapi.yaml`; the frontend schema is generated from it. Determinism, drift, sensitive-content scanning, and merge-base compatibility are CI gates. |
| VIII. Safe schema evolution | PASS | The approved `operations` migration provisions only the canonical cache table and has one graph leaf. An AST-only checker and fixture corpus establish ownership, table-identity drift, single-leaf, required-field, and expand/contract enforcement without importing Django or connecting to a database; PostgreSQL proves actual provisioning. |
| IX. Security, secrets, environment isolation | PASS | Pre-Django typed validation, runtime/admin DB separation, canonical shared-cache selection, `.env.example`, a non-secret environment inventory, and isolation/readiness checks fail closed without exposing values. Process-local cache is rejected outside development regardless of debug. |
| X. Location integrity | PASS (out of scope) | Location CSVs, geometry, and location models are not read or changed. |
| XI-XII. Correct-layer tests and maintainability | PASS | Unit, HTTP, PostgreSQL, architecture, contract, frontend, and fixture tests own their respective claims; Ruff, mypy, ESLint, TypeScript, format, AST, and build checks are automated. |

No constitution violation needs a complexity exception. CHOT §9.4, R-104/R-106, QUY_TAC §3, and this plan now use the same `backend/core/` path.

## Project Structure

### Documentation (this feature)

```text
specs/001-project-api-foundation/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── README.md
│   ├── api.md
│   ├── frontend.md
│   ├── tooling.md
│   ├── recovery.md
│   └── cache.md
└── tasks.md                  # created later by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── manage.py
├── pyproject.toml
├── uv.lock
├── config/                   # sole composition root and URL/settings assembly
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── core/                     # narrow technical shared kernel
│   ├── correlation.py
│   ├── deployment.py
│   ├── errors.py
│   ├── error_codes.py
│   ├── event_payload.py
│   ├── cache.py
│   ├── logging.py
│   ├── messages.py
│   ├── middleware.py
│   ├── recovery.py
│   └── recovery_health.py   # pure value model/evaluator only
├── operations/               # approved operational integration owner
│   ├── application/recovery_health.py          # operational orchestration
│   ├── adapters/recovery_alerts.py             # contained alert/telemetry sink
│   ├── management/commands/verify_restore.py   # thin shim only
│   └── migrations/<next>_throttle_cache_table.py
└── tests/
    ├── unit/core/
    ├── integration/api/
    ├── integration/postgres/
    ├── architecture/
    ├── contract/
    └── migration_fixtures/

frontend/
├── package.json
├── package-lock.json
├── next.config.ts
├── tsconfig.json
├── eslint.config.mjs
├── vitest.config.ts
├── src/
│   ├── app/                  # minimal application shell; no business screen
│   ├── middleware.ts         # source-credential edge boundary
│   └── shared/
│       ├── messages.ts
│       ├── api/
│       │   ├── schema.ts     # generated, committed, never hand-edited
│       │   └── client.ts     # thin handwritten typed client assembly
│       ├── errors/
│       ├── transport/
│       │   └── authenticated-fetch.ts
│       └── ui/async-state/
└── tests/
    ├── unit/
    ├── contract/
    └── architecture/

contracts/
└── openapi.yaml              # generated from backend and committed

deploy/
├── environments.yaml         # non-secret identities and UNRESOLVED markers
├── recovery-evidence.yaml    # targets plus unresolved/operator evidence
└── migration.env.example     # admin-process keys, never application runtime input

scripts/
├── check_architecture.py
├── check_function_length.py
├── migration_check.py
├── check_openapi.py
├── deployment_check.py
├── capacity_check.py
└── generate_openapi.py

.github/workflows/
├── quality.yml
└── contract.yml

compose.yaml                  # local PostgreSQL only
.env.example                  # application-runtime keys only; no real credentials
.pre-commit-config.yaml
docs/TRIEN_KHAI.md
```

**Structure Decision**: Use separate root-level backend and frontend projects because the approved stack has independent Python and Node toolchains. `backend/config/` is the only composition root and is never an installed app; it has no `apps.py`, management commands, migrations, models, or persistence. `backend/core/` owns pure technical cross-cutting behavior and is not an installed app. The already-approved `backend/operations/` module is the sole operational integration owner for the thin restore command and R-109 cache-table migration; this does not authorize another infrastructure app or business persistence. Do not create `identity`, `locations`, `attendance`, `tasks`, `reporting`, or `notifications` directories until a feature owns them. When created, every business module must have `domain/`, `application/`, `ports/`, and `adapters/`; the architecture checker validates that convention and the inward/cross-module rules without requiring placeholder packages now.

## Design and Ownership

### Backend assembly and boundaries

- `core.deployment` is pure Python and reads/validates application-runtime environment before Django settings are assembled. It exposes typed runtime settings and safe validation errors; it neither reads nor defines the migration-admin key and never logs values.
- `core.cache` is pure Python and is the sole owner of `THROTTLE_CACHE_ALIAS`, `THROTTLE_CACHE_TABLE`, `CACHE_BACKEND_CHOICES`, and process-local backend classification. It imports no Django so pre-framework deployment checks can consume it.
- `config.settings` translates validated settings into Django/DRF/drf-spectacular configuration and exactly one cache alias using the canonical cache definitions. Runtime code receives only the normal PostgreSQL DSN. A separate repository-side deployment module and process own migration-admin input and safe identity comparison; application imports cannot reach that module. `config` composes the approved `operations` app but never becomes an app itself.
- `config.urls` owns the `/api/v1/` prefix once. It conditionally registers the non-interactive machine schema route when `API_DOCS_ENABLED` is true. API error wrapping and request-ID middleware apply to the entire namespace.
- `core.correlation` uses execution-context-local storage with bind/read/reset operations. Middleware always creates UUIDv4 `request_id` and defaults `correlation_id` to it; any client `X-Request-Id` is ignored.
- `core.errors` is the single canonical envelope builder and DRF/Django adapter point. It accepts only codes already authorized by CHOT; this feature exercises `VALIDATION_FAILED` and `PERMISSION_DENIED` and assigns no generic 404/405/415/500 vocabulary. Canonical fields win; colliding detail keys remain only under `details` and are not top-level mirrors.
- `core.messages` centralizes backend display text; `frontend/src/shared/messages.ts` owns the corresponding foundation UI strings.
- `core.logging` enriches records with ambient identifiers or empty strings and contains enrichment/sink failures so diagnostics cannot change request outcomes. Every external failure string passes through `core.event_payload.sanitize_failure_reason` before reaching any log, metric, or alert sink.
- `core.event_payload` owns both the exact-key/value rejection filter and the distinct R-105/R-106 `sanitize_failure_reason`; no alternate sanitizer is introduced. Audit/outbox port integration remains deferred.
- `core.recovery_health` contains only the pure health value model/evaluator. `operations.application.recovery_health` orchestrates operational evidence and delegates emission to `operations.adapters.recovery_alerts`; core imports no operations, Django, logging adapter, alert adapter, or telemetry adapter.
- Test-only URLs and views exercise success, authorized validation/CSRF denial, and correlation behavior. They are never registered in runtime `config.urls` and therefore do not establish a public business contract or invent codes for ungoverned framework statuses.

There is no domain layer, business application service, business port, or business adapter to implement for this technical feature. The `operations` command is a thin framework adapter over pure `core.recovery` orchestration; it does not create business policy. The convention and import checks are established now; concrete modules will supply those layers when their business specifications exist.

### Persistence, transactions, and concurrency

- The feature owns no Django model, business table, business constraint, or business index. Its only migration is the R-109 technical DatabaseCache provisioning migration owned by `operations`; it consumes `core.cache.THROTTLE_CACHE_TABLE`, uses the approved create-cache-table mechanism, and remains the single `operations` leaf. In the currently empty graph its valid path is `operations/migrations/0001_throttle_cache_table.py`; implementation MUST recalculate the next number if the graph changes before that task. It does not enable a stock Django user model or create `AuditLog` or `OutboxEvent` tables.
- PostgreSQL integration tests connect through Django, assert `connection.vendor == "postgresql"`, execute a real transaction and rollback check, and fail when the service or DSN is unavailable. SQLite is not configured in any environment.
- There is no business unit of work, locking, compare-and-set, idempotency, retry, or outbox transaction to define. Concurrency evidence is limited to request/correlation isolation across competing threads and async tasks.
- `scripts/migration_check.py check` parses migration source with Python AST only. Fixtures reject unapproved migration owners, a config migration/app, canonical cache-table drift, multiple leaves, every new `NOT NULL` field lacking `db_default`, destructive operations without `RELEASE_PHASE = "contract"`, and contract files mixed with expansion. The `operations` cache migration is also applied on PostgreSQL and its table identity is compared with settings. Migration precedes rollout, remains compatible with N-1, and destructive contraction is delayed to a later release. A later business schema owner still adds its own PostgreSQL migration tests.

### API contract and error semantics

- OpenAPI 3.0.3 is generated by drf-spectacular with fixed `info.version: 1.0.0`, normalized line endings, stable ordering, explicit operation IDs, and no timestamps or machine paths.
- All registered application paths must begin `/api/v1/`. The schema route is machine-readable only and exists only under the enabled deployment flag; no Swagger UI or ReDoc dependency is installed.
- The foundation does not create an error vocabulary. It reuses only CHOT-authorized `VALIDATION_FAILED` and `PERMISSION_DENIED`; other framework statuses receive no new code/status mapping in this feature and require governance before any later public adapter is added.
- All `/api/v1/` responses set `X-Request-Id` and `Cache-Control: private, no-store`. JSON failures include the matching request ID and the canonical/mirrored v1 shape.
- Generation writes a temporary candidate, validates with warnings-as-errors, runs the sensitive-content scanner, generates twice and compares bytes, then replaces the committed artifact only in explicit update mode. Check mode never mutates committed files.
- Compatibility compares the candidate with `contracts/openapi.yaml` from the Git merge base using a pinned oasdiff release. The first introduction may have no baseline and is accepted only if the candidate exists and passes all other checks; after the baseline is present, missing either side is a failure. Optional additive changes are allowed, while removals, incompatible changes, and newly required request fields fail.

### Frontend integration and state

- `authenticatedFetch` is a fetch-compatible function that accepts relative same-origin `/api/v1/` requests, sets `credentials: "include"`, `cache: "no-store"`, a JSON accept header, and preserves caller cancellation. It contains no token store, login redirect, refresh, authorization policy, or automatic mutation retry.
- `openapi-typescript` generates only `schema.ts` from committed `contracts/openapi.yaml`. `openapi-fetch` is assembled in the thin handwritten `client.ts` with `authenticatedFetch` supplied as the custom fetch implementation.
- Architecture checks reject direct `fetch`/Axios-like authenticated transports outside the approved transport file and test fixtures. In exact accordance with QUY_TAC, ESLint globally ignores `src/shared/api/**`; `schema.ts` is generated while handwritten `client.ts` stays thin and is enforced by `tsc --noEmit`, architecture checks, and review.
- Shared errors defensively parse the canonical envelope and preserve `error_code`, `message`, `details`, mirrors, and `request_id`; invalid HTTP bodies become an unexpected-response state, and transport exceptions become a network state.
- Shared UI state covers loading, empty, canonical error, unexpected response, and network failure. Retry is an explicit callback supplied by the owning operation; the foundation does not infer that a mutation is safe to retry.

### Environment and security foundation

- The environment vocabulary is exactly `development`, `staging`, and `production`. Missing, empty, unknown, or `UNRESOLVED` runtime-critical values fail before framework settings load, naming only the key.
- `.env.example` documents only application-runtime keys and safe local placeholders; production-critical secrets remain visibly unset/commented and never receive weak defaults. `deploy/migration.env.example` documents the separate admin process without making that key visible to Django runtime.
- `deploy/environments.yaml` contains resource identifiers only—never credentials or full connection strings—and keeps undecided production values as `UNRESOLVED`. Isolation checks reject reuse of protected database, storage, cache/queue namespace, signing-key identity, or credential identity across environments.
- `deployment_check.py production-ready` intentionally exits nonzero and lists unresolved field paths until governance/provider decisions are made. That command is not a normal quality gate; `deployment_check.py isolation` is.
- Runtime/admin database identity comparison parses safe identities without echoing DSNs. Repository and generated-artifact checks likewise report only rule names and paths, never matched protected content.
- `frontend/src/middleware.ts` statically matches the same `/api/v1/*` source as the Next rewrite, removes any client-supplied source header first, then attaches the server-only credential. The value is at least 32 characters, never `NEXT_PUBLIC_`, logged, bundled, or echoed. `OriginCredentialMiddleware` uses `secrets.compare_digest` and returns the authorized canonical `PERMISSION_DENIED` 403 for missing/wrong credentials without identifying the cause.
- Outside development, typed startup validation requires `rediss://` with a password, environment-qualified `REDIS_KEY_PREFIX` and `R2_BUCKET`, rejects `REDIS_RESULT_BACKEND_URL`, and preserves separation of runtime/admin database identities.
- Cache backend choice is read once through the typed closed vocabulary `locmem`/`database`/`redis`. Development/test may use the approved `locmem` fallback; the shipped staging/production inventory resolves to `database`. Outside development, process-local `LocMemCache`, `DummyCache`, or `FileBasedCache` stops startup even when `DJANGO_DEBUG=true`. Redis selection remains guarded by package availability and adds no dependency.
- `deploy/environments.yaml` contains a resolved `cache.backend` for every environment. `scripts/deployment_check.py` imports canonical cache definitions and rejects missing, unknown, or non-development process-local choices without copying the vocabulary.

### Recovery-readiness foundation

- `deploy/environments.yaml` includes credential-free backup identities for all three environments. Provider selections remain `UNRESOLVED`; `production-ready` must therefore remain nonzero.
- `deploy/recovery-evidence.yaml` separates fixed targets (RPO 24 hours, RTO 4 hours, retention 30 days, p95 500 ms) from operator-recorded drill and capacity evidence. Empty evidence is represented as `UNRESOLVED`, never as a passed drill.
- `scripts/deployment_check.py recovery-ready` rejects unresolved, stale, failed, failed-without-remediation-owner, or target-exceeding evidence. It is an operator readiness command, not a CI gate.
- Django discovers `manage.py verify_restore` from the approved `operations` app. The command is a thin shim over `core.recovery`; it reads only `RECOVERY_DATABASE_URL`, compares safe DSN identities with runtime/admin before opening a socket, starts a read-only transaction, and verifies the CHOT-listed user/audit/token/outbox/schema categories without any write or Django database alias. Missing required relations/categories/registrations, incomplete probes, incompatible schemas, and probe execution failures deterministically produce `incomplete/unverifiable`, exit nonzero, and never produce PASS, OK, or readiness. Command and recovery failures use the canonical sanitizer.
- `scripts/capacity_check.py measure` rejects fewer than 50 distinct real identities or concurrency below 20 before network activity. Every opened connection/resource closes on success and failure. Identities, passwords, tokens, Bearer values, credentialed URLs, and secret values never appear in stdout, stderr, or returned/result artifacts. A p95 of exactly 500 ms may pass; a result above 500 ms is `failed` with a remediation owner. `*.identities` is ignored; controlled tests are never operator evidence, and command output cannot itself make production/recovery readiness true.
- The pure health evaluator represents a never-run restore drill as `unknown` and a stale drill as `alert`; operations application code owns evidence orchestration and the operations adapter owns contained alert/telemetry emission. `docs/TRIEN_KHAI.md` owns the reproducible topology, egress, credential rotation, migration-before-rollout, isolated restore, session revocation, stale-lease clearing, deferred-IaC, and APAC-not-residency procedures.

## Verification Strategy

| Layer | Evidence |
| --- | --- |
| Pure unit | Environment parsing/fail-closed behavior, UUID/context lifecycle, envelope collision rules, centralized messages, canonical sanitization, logging fallback, recursive payload filter, error parsing, frontend state mapping. |
| HTTP integration | Test-only DRF/Django routes prove request headers, body/header equality, framework errors, CSRF wrapping, namespace rules, and no-store headers. |
| Concurrency | Competing threads and async tasks prove unique request IDs, isolated context, reset after completion, and empty out-of-request values; 10,000 UUIDs satisfy SC-004. |
| PostgreSQL integration | Live service/vendor assertion, connection failure behavior, transactional rollback, and Django migration executor baseline. No SQLite setting or fallback is permitted. |
| Contract | Two-pass OpenAPI/client byte equality, explicit operation IDs, snake_case/path scans, validation, sensitive fixtures, source/artifact drift, and merge-base oasdiff. |
| Architecture | AST/import checks for domain purity, module convention, cross-module internals, composition-root exemptions, `config`/`core` non-app status, approved local-app ownership, function/component limits, generated-file ownership, and frontend transport uniqueness. |
| Migration safety | `migration_check.py check` AST-only fixtures for approved ownership, absence of config migrations/apps, canonical cache-table identity, leaves, `db_default`, release phase, and expand/contract separation; no import or database access. PostgreSQL separately verifies the approved cache table. |
| Deployment/origin | Manifest isolation, intentionally failing production readiness, proxy header stripping, static matcher/rewrite parity, constant-time origin denial, and status-only smoke output. |
| Recovery readiness | Command discovery through `operations`, evidence schema/readiness fixtures, pre-connect DSN denial, missing relation/category/registration, incomplete probe, incompatible-schema and probe-failure rejection, complete read-only success, pure-core health evaluation plus operations-owned orchestration/alerts, exact 50/20/500 capacity semantics, success/failure cleanup, and stdout/stderr/result-artifact secret tests. Operational drill/measurement execution is not claimed. |
| CI | Pinned Python/Node/PostgreSQL jobs run lockfile, format, lint, typing, unit, integration, build, contract, security, architecture, environment-isolation, and migration checks with actionable artifact paths. |

## Delivery Phases

1. Establish root toolchain files, locked dependency manifests, PostgreSQL compose/service configuration, and fail-closed environment parsing.
2. Assemble the non-app Django composition root, pure core correlation/error/cache/recovery/logging/payload primitives, the approved operations integration owner, test-only boundary probes, and backend unit/integration infrastructure.
3. Add deterministic OpenAPI generation, validation, safe-content scanning, drift/compatibility checks, and the initial committed contract.
4. Establish the Next.js shell, generated schema, typed client assembly, `authenticatedFetch`, shared error/state handling, and frontend tests/build checks.
5. Add architecture, complexity, exact migration, deployment/origin, recovery-readiness, and capacity fixture suites; wire only the CHOT-approved CI gates; run the full clean-checkout quickstart.

Each phase must remain green before the next begins. Contract generation precedes client generation. PostgreSQL-backed checks precede any claim of database readiness. No phase adds a business endpoint or model.

## Risks and Controls

- **Initial empty contract**: the schema may have no business paths. Control: test the pipeline with test-only routes and validate the conditionally exposed schema route separately; do not invent a public health/business API solely to populate OpenAPI.
- **Generated-code exclusions swallowing handwritten logic**: retain the exact QUY_TAC directory exclusion, keep `client.ts` thin, and enforce it with TypeScript, architecture checks, and review rather than a competing ESLint exception.
- **Compatibility baseline absent on the first contract PR**: control with a one-time, explicit initial-baseline branch in the check; missing a previously existing merge-base contract remains fatal.
- **Configuration check leaks a DSN or matched schema secret**: control with path/key-only diagnostics and adversarial tests asserting supplied values never appear.
- **Static migration analysis overclaims safety**: control by applying the approved cache-table migration on PostgreSQL and documenting that static analysis remains an early gate; each future business schema owner still supplies its own PostgreSQL migration and rolling-compatibility tests.
- **Django command discovery invites a new app**: control with an approved-local-app allowlist and tests that `verify_restore` resolves to `operations` while rejecting `config/apps.py`, `config/management/`, `config/migrations/`, registration of `core`, and any extra local app.
- **Canonical cache values drift**: control by making settings, deployment checks, throttle consumers, and migration import `core.cache` definitions and by statically/runtime comparing the resolved alias/table identity.
- **Readiness overclaim**: committed recovery fields begin `UNRESOLVED`; tests require readiness commands to remain nonzero until real signed evidence exists, and CI does not manufacture or certify that evidence.

## Complexity Tracking

No constitution violations or justified exceptions.
