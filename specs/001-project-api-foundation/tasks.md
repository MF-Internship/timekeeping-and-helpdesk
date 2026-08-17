---

description: "Dependency-ordered implementation tasks for the project foundation and API contract baseline"
---

# Tasks: Project Foundation and API Contract Baseline

**Input**: Design documents from `/specs/001-project-api-foundation/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Mandatory. For each behavior slice, add the named failing test or contract first, then implement the canonical primitive, then its consumers, then run integration verification.

**Ordering invariant**: Governance → tests/contracts → canonical primitive implementation → consumers → integration verification. A task marked `[P]` is independent only after every prerequisite named in Dependencies is complete.

## Phase 1: Governance and Setup

**Purpose**: Establish authoritative, reproducible inputs before any runtime source, generated artifact, migration, or CI implementation begins.

- [X] T001 Execute the authority-order traceability review and record PASS/FAIL for canonical `backend/core/`, authorized API codes only, R-107/R-108/R-109 ownership, no `config`/`core` Django app, PRD 50/20/500 semantics, generated-code treatment, and centralized messages in `specs/001-project-api-foundation/checklists/requirements.md`; STOP all later tasks on any FAIL
- [X] T002 [P] Initialize the pinned Python 3.12/Django 5.2/DRF 3.16/psycopg 3/drf-spectacular/pytest/Ruff/mypy dependency graph in `backend/pyproject.toml` and `backend/uv.lock`; `uv sync --project backend --locked` must exit 0 without an unapproved runtime dependency
- [X] T003 [P] Initialize the pinned Node 22/Next.js 16/React 19/openapi-fetch/openapi-typescript/Vitest/Testing Library/ESLint/Prettier graph in `frontend/package.json` and `frontend/package-lock.json`; `npm --prefix frontend ci` must exit 0 from the lockfile
- [X] T004 [P] Define one PostgreSQL 17 development/CI service with distinct runtime and migration principals in `compose.yaml`; its healthcheck must become healthy and no SQLite service/configuration may exist
- [X] T005 Add only safe runtime/admin/origin/Redis/bucket/recovery/cache examples to `.env.example` and `deploy/migration.env.example`; a source scan must find no secret value, empty unresolved assignment, full provider DSN, or migration-admin key in the runtime example
- [X] T006 Configure pytest-django discovery, unit/integration/contract/architecture/PostgreSQL markers, and safe test defaults in `backend/pytest.ini` and `backend/tests/conftest.py`; collection must succeed without opening PostgreSQL for non-PostgreSQL tests
- [X] T007 Configure Vitest, jsdom, Testing Library cleanup, and test aliases in `frontend/vitest.config.ts` and `frontend/tests/setup.ts`; after T003, an empty-suite collection probe must exit 0

**Checkpoint**: T001 and T005 are complete, both lockfile installs are reproducible, and test runners collect. No runtime behavior has been implemented.

---

## Phase 2: Blocking Backend and Cache Foundations

**Purpose**: Establish the canonical sanitizer first, then pure configuration, approved app ownership, and R-109 persistence before user-story work.

**Critical**: User-story implementation cannot begin until T008–T024 pass.

- [X] T008 Add failing recursive-filter and bounded canonical-sanitizer tests in `backend/tests/unit/core/test_event_payload.py`; URL, token, password, cookie, object/image, coordinate, list, exact-key, allowed-substring, length, and no-value-diagnostic cases must be covered before any diagnostic consumer test or implementation
- [X] T009 Implement the recursive rejection filter and sole `sanitize_failure_reason` against T008 in `backend/core/event_payload.py`; all adversarial cases must pass and an architecture test must prove no upward Django/logging/operations/scripts import before any diagnostic consumer is implemented

- [X] T010 Add failing tests for typed environment parsing, closed environment names, empty/`UNRESOLVED` rejection, PostgreSQL-only DSNs, runtime/admin collision, encrypted Redis and environment-qualified names, forbidden result backend, source credential length, and key-only diagnostics in `backend/tests/unit/core/test_deployment.py`; each unsafe fixture must fail for its named rule without echoing its value
- [X] T011 Implement immutable pre-Django runtime parsing against T010 in `backend/core/deployment.py`; all T010 cases must pass and no application path may read `DATABASE_ADMIN_URL`
- [X] T012 Add failing canonical cache and consumer-boundary tests in `backend/tests/unit/core/test_cache.py` and `backend/tests/architecture/test_cache_consumers.py`; they must require `THROTTLE_CACHE_ALIAS`, `THROTTLE_CACHE_TABLE`, exact `locmem/database/redis` choices, process-local classification, zero Django imports, and canonical-alias imports from every present throttle consumer
- [X] T013 Implement the pure canonical cache definitions against T012 in `backend/core/cache.py`; T012 and a standalone pre-Django import probe must pass
- [X] T014 Add failing Django ownership tests in `backend/tests/architecture/test_django_app_registry.py`; they must reject registration of `config`/`core`, `config/apps.py`, `config/management/`, `config/migrations/`, unapproved local apps, and any local persistence owner other than `operations`
- [X] T015 Add test-only DRF probe views and URLs for success plus CHOT-authorized validation/CSRF denial in `backend/tests/integration/api/views.py` and `backend/tests/integration/api/urls.py`; URL inspection must find no business/auth route or invented 404/405/415/500 code
- [X] T016 Assemble the Django composition root and approved `operations` package against T014 in `backend/manage.py`, `backend/config/settings.py`, `backend/config/urls.py`, `backend/config/asgi.py`, `backend/config/wsgi.py`, and `backend/operations/__init__.py`; `manage.py check` and the local-app allowlist test must pass without `config/apps.py` or `core` registration
- [X] T017 Add failing cache-settings tests in `backend/tests/unit/config/test_cache_settings.py`; they must require exactly one canonical alias, canonical table identity, closed env parsing, shipped staging/production `database`, development/test `locmem` fallback, debug-independent process-local denial, Redis package guard, and fail-closed cache errors
- [X] T018 Configure the single Django cache alias against T017 in `backend/config/settings.py`; every cache-settings fixture must pass without copying alias, table, vocabulary, or process-local classification
- [X] T019 Add failing deployment-cache contract fixtures in `backend/tests/contract/fixtures/deployment/` and `backend/tests/contract/test_cache_deployment.py`; missing/unknown/process-local non-development choices must fail and all three valid inventories must use definitions imported from `core.cache`
- [X] T020 Add resolved non-secret `cache.backend` entries for all environments in `deploy/environments.yaml` and implement canonical cache validation against T019 in `scripts/deployment_check.py`; valid isolation must exit 0 and every unsafe fixture must exit nonzero with path-only output
- [X] T021 Add failing migration ownership/static tests in `backend/tests/contract/test_cache_migration.py`; they must require one `operations` leaf, the approved create-cache-table mechanism, import of `THROTTLE_CACHE_TABLE`, settings/provisioning identity equality, and absence of any config migration/app
- [X] T022 Reinspect the actual `operations` graph and add the current next valid cache-table migration against T021 at `backend/operations/migrations/0001_throttle_cache_table.py`; if prior migrations have appeared, rename this task target to the graph's next number before editing, and require the static tests to pass without a duplicated table literal
- [X] T023 Add and run a real-PostgreSQL migration test in `backend/tests/integration/postgres/test_cache_migration.py`; applying the graph must create exactly the canonical cache table and reversing/reapplying the test graph must leave one valid leaf
- [X] T024 Document `config`/`core` non-app rules, approved `operations` ownership, future business-module layers, inward dependencies, and closed exemptions in `docs/ARCHITECTURE.md`; the architecture document contract test must locate every rule exactly once

**Checkpoint**: `config/` is composition only, `core/` is pure/non-app, `operations` is the only approved local operational owner, and the canonical cache table is proven on PostgreSQL.

---

## Phase 3: User Story 1 — Build New Features on a Safe Foundation (Priority: P1)

**Goal**: Provide inspectable backend/frontend boundaries, PostgreSQL-only behavior, one transport, and shared UI/error foundations without business behavior.

**Independent Test**: Run the US1 architecture, PostgreSQL, transport, error, and UI suites; every prohibited import/transport/configuration/business route must fail and the minimal shell must pass.

### Tests and contracts

- [X] T025 [P] [US1] Add fixture-driven module-boundary tests for domain framework imports, inward violations, cross-module internals, undocumented exemptions, and oversized core ownership in `backend/tests/architecture/fixtures/` and `backend/tests/architecture/test_module_boundaries.py`; every unsafe fixture must fail with rule/path output
- [X] T026 [P] [US1] Add PostgreSQL vendor, transaction rollback, and migration-executor tests in `backend/tests/integration/postgres/test_database_foundation.py`; the suite must prove `connection.vendor == "postgresql"` and persisted state rollback
- [X] T027 [P] [US1] Add deny tests for SQLite configuration and unavailable PostgreSQL in `backend/tests/integration/postgres/test_no_database_fallback.py`; both cases must fail instead of falling back
- [X] T028 [P] [US1] Add scope-exclusion tests in `backend/tests/architecture/test_scope_exclusions.py`; runtime URLs/apps/models must contain no login/auth, locations, attendance, tasks, reporting, notifications, stock user model, `AuditLog`, or `OutboxEvent`
- [X] T029 [P] [US1] Add failing transport and edge tests in `frontend/tests/unit/transport/authenticated-fetch.test.ts` and `frontend/tests/architecture/origin-proxy-boundary.test.ts`; they must cover one same-origin `/api/v1/` fetch, no-store, absolute/off-prefix denial, source-header stripping, no public secret, and literal matcher/rewrite parity
- [X] T030 [P] [US1] Add failing API failure-parser and centralized-message tests in `frontend/tests/unit/errors/api-error.test.ts` and `frontend/tests/unit/messages.test.ts`; canonical/mirror mismatch, unexpected body, network failure, and safe request-ID fallback must be distinguishable
- [X] T031 [P] [US1] Add failing async-state tests in `frontend/tests/unit/ui/async-state.test.tsx`; loading, empty, canonical, unexpected, network, accessible roles, centralized strings, and optional retry must each have one observable state
- [X] T032 [P] [US1] Add a frontend architecture test in `frontend/tests/architecture/api-transport-boundary.test.ts`; direct `/api/v1/` fetches or alternate authenticated transports outside the one exemption must fail
- [X] T033 [P] [US1] Add a shell contract test in `frontend/tests/contract/foundation-shell.test.tsx`; the shell must render every shared async state without business data or routes

### Canonical primitives and consumers

- [X] T034 [US1] Implement the AST architecture checker against T025 in `scripts/check_architecture.py`; all safe fixtures pass and all unsafe fixtures fail with rule/path diagnostics
- [X] T035 [US1] Wire runtime PostgreSQL-only settings against T026–T028 in `backend/config/settings.py`; PostgreSQL tests pass and SQLite/business/auth exclusions remain enforced
- [X] T036 [US1] Create only the non-business Next.js shell in `frontend/src/app/layout.tsx`, `frontend/src/app/page.tsx`, and `frontend/src/app/globals.css`; T033 must progress to failing only on still-missing shared states, not edge behavior
- [X] T037 [US1] Implement centralized frontend messages and canonical/unexpected/network parsing against T030 in `frontend/src/shared/messages.ts` and `frontend/src/shared/errors/api-error.ts`; parser/message tests must pass with no duplicate display string
- [X] T038 [US1] Implement the single fetch-compatible `authenticatedFetch` against T029 in `frontend/src/shared/transport/authenticated-fetch.ts`; transport tests must pass without token storage, redirect, refresh, or automatic retry
- [X] T039 [US1] Implement the rewrite/matcher and source-header boundary against T029 in `frontend/next.config.ts` and `frontend/src/middleware.ts`; stripping, literal parity, no-store, and no-public-secret tests must pass
- [X] T040 [US1] Implement accessible shared async states against T031 in `frontend/src/shared/ui/async-state/AsyncState.tsx` and `frontend/src/shared/ui/async-state/index.ts`; every controlled state and optional-retry test must pass
- [X] T041 [US1] Implement the exact transport source scanner against T032 in `frontend/scripts/check-api-transport.mjs`; one approved file passes and every fixture containing a second transport exits nonzero with its path
- [X] T042 [US1] Connect the shell to shared async states against T033 in `frontend/src/app/page.tsx`; the shell contract must pass with no public business workflow
- [X] T043 [US1] Run the complete US1 suites under `backend/tests/architecture/`, `backend/tests/integration/postgres/`, `frontend/tests/unit/`, `frontend/tests/architecture/`, and `frontend/tests/contract/foundation-shell.test.tsx`; the checkpoint passes only when all required paths pass and all prohibited fixtures fail

---

## Phase 4: User Story 2 — Consume a Stable Versioned Contract (Priority: P1)

**Goal**: Provide one v1 API/error boundary, deterministic OpenAPI, and a generated frontend schema/client through `authenticatedFetch`.

**Independent Test**: Generate backend and frontend artifacts twice, exercise authorized errors and schema enabled/disabled states, and require byte identity plus observed header/body equality.

### Tests and contracts

- [X] T044 [P] [US2] Add correlation lifecycle tests in `backend/tests/unit/core/test_correlation.py`; empty/bind/reset/nested/exception behavior and UUIDv4 validation must be deterministic
- [X] T045 [P] [US2] Add error/message tests in `backend/tests/unit/core/test_errors.py` and `backend/tests/unit/core/test_messages.py`; only `VALIDATION_FAILED` and `PERMISSION_DENIED` are allowed and every canonical/mirror/collision/protected-value assertion must pass
- [X] T046 [P] [US2] Add request middleware tests in `backend/tests/integration/api/test_request_contract.py`; server UUIDv4, body/header equality, no-store, cleanup, and denial of valid/malformed/duplicate/oversized client IDs must be observed
- [X] T047 [P] [US2] Add API denial tests in `backend/tests/integration/api/test_error_responses.py` and `backend/tests/integration/api/test_origin_credential.py`; missing/wrong origin responses must be identical canonical 403 and no generic 404/405/415/500 code may exist
- [X] T048 [P] [US2] Add schema-route tests in `backend/tests/contract/test_schema_route.py`; enabled YAML, disabled 404 route absence, and no Swagger/ReDoc HTML must be proved
- [X] T049 [P] [US2] Add deterministic OpenAPI tests in `backend/tests/contract/test_openapi_generation.py`; version, v1 paths, unique operation IDs, snake_case, LF/stable order, and two-pass bytes must pass
- [X] T050 [P] [US2] Add protected-schema fixtures and tests in `backend/tests/contract/fixtures/openapi/` and `backend/tests/contract/test_openapi_safety.py`; every forbidden token/URL/object/image/coordinate fixture must fail with safe path-only output
- [X] T051 [P] [US2] Add frontend generation tests in `frontend/tests/contract/api-generation.test.ts`; only committed OpenAPI input and repeated byte identity may pass
- [X] T052 [P] [US2] Add typed-client and schema-probe tests in `frontend/tests/contract/api-client.test.ts` and `frontend/tests/contract/schema-probe.test.ts`; injected `authenticatedFetch`, snake_case, request ID, no-store, machine schema, and disabled denial must be observed

### Canonical primitives and consumers

- [X] T053 [US2] Implement context-local correlation primitives against T044 in `backend/core/correlation.py`; the lifecycle suite must pass before middleware consumption
- [X] T054 [US2] Implement authorized constants, centralized messages, and the single envelope builder against T045 in `backend/core/error_codes.py`, `backend/core/messages.py`, and `backend/core/errors.py`; the code-vocabulary scan must find no unauthorized code
- [X] T055 [US2] Implement request-ID/correlation/no-store and constant-time origin middleware against T046–T047 in `backend/core/middleware.py`; all request and indistinguishable-denial tests must pass
- [X] T056 [US2] Implement only authorized validation/CSRF/origin adapters against T047 in `backend/core/errors.py` and `backend/config/handlers.py`; the framework-code absence assertion must pass
- [X] T057 [US2] Configure DRF and drf-spectacular generation against T048–T049 in `backend/config/settings.py` and `backend/config/schema.py`; schema validation must be warning-free
- [X] T058 [US2] Register only the conditional machine schema under `/api/v1/` against T048 in `backend/config/urls.py`; enabled and disabled route tests must pass
- [X] T059 [US2] Implement deterministic generation and protected-content scanning against T049–T050 in `scripts/generate_openapi.py` and `scripts/check_openapi.py`; check mode must be non-mutating and two-pass output byte-identical
- [X] T060 [US2] Generate and commit the backend-authoritative artifact in `contracts/openapi.yaml`; regeneration check must exit 0 with no diff
- [X] T061 [US2] Implement deterministic frontend schema generation and commit `frontend/src/shared/api/schema.ts` through `frontend/scripts/generate-api.mjs` and `frontend/package.json`; T051 must pass with no handwritten edit
- [X] T062 [US2] Assemble the thin typed client against T052 in `frontend/src/shared/api/client.ts`; client and end-to-end schema-probe tests must pass through `authenticatedFetch`
- [X] T063 [US2] Run `backend/tests/unit/core/test_correlation.py`, `backend/tests/unit/core/test_errors.py`, `backend/tests/integration/api/`, `backend/tests/contract/test_openapi_*.py`, and `frontend/tests/contract/`; the checkpoint passes only with byte identity, authorized codes, v1 paths, matching mirrors, and one transport

---

## Phase 5: User Story 3 — Detect Unsafe Changes Before Merge (Priority: P2)

**Goal**: Make quality, architecture, migration, deployment, contract, PostgreSQL, frontend, and build regressions fail reproducibly.

**Independent Test**: Run every gate against a conforming tree and its controlled unsafe fixtures; each fixture must fail for exactly its intended rule without protected output.

### Tests and contracts

- [X] T064 [P] [US3] Add maintainability fixtures/tests in `backend/tests/architecture/fixtures/maintainability/` and `backend/tests/architecture/test_maintainability.py`; function, parameter, nesting, complexity, naming, exact generated exclusions, and thin-client violations must each fail
- [X] T065 [P] [US3] Add migration graphs for safe/duplicate/merge/nullable/required/default/contraction/mixed/owner/cache-drift cases in `backend/tests/migration_fixtures/`; each fixture must identify one expected outcome
- [X] T066 [US3] Add migration-check tests against T065 in `backend/tests/contract/test_migration_safety.py`; AST-only execution must reject every unsafe fixture, accept safe fixtures, and prove no Django import or database connection
- [X] T067 [US3] Add deployment/recovery consumer fixtures after T009 in `backend/tests/contract/fixtures/deployment/`, `backend/tests/contract/fixtures/recovery/`, and `backend/tests/contract/test_deployment_checks.py`; isolation/readiness/safe-diagnostic and canonical-sanitization outcomes must be exhaustive before the consumer implementation
- [X] T068 [P] [US3] Add drift fixtures/tests in `backend/tests/contract/fixtures/drift/` and `backend/tests/contract/test_contract_drift.py`; stale backend/client artifacts must fail while check mode leaves files unchanged
- [X] T069 [P] [US3] Add compatibility fixtures/tests in `backend/tests/contract/fixtures/compatibility/` and `backend/tests/contract/test_openapi_compatibility.py`; removal/type/response/new-required changes fail and additive optional change passes
- [X] T070 [US3] Add controlled-gate diagnostic consumer tests after T009 in `backend/tests/contract/test_gate_diagnostics.py`; every stdout/stderr-facing gate must route external failure text through the canonical sanitizer and return its rule ID and artifact path without matched protected values

### Gate implementations

- [X] T071 [P] [US3] Configure Ruff and strict mypy for authored backend/config/core/operations/scripts code in `backend/pyproject.toml`; format, lint, and type commands must exit 0 on the conforming tree
- [X] T072 [P] [US3] Configure strict TypeScript, ESLint, Prettier, tests, and production build in `frontend/tsconfig.json`, `frontend/eslint.config.mjs`, `frontend/.prettierrc.json`, and `frontend/package.json`; every declared check must exit 0
- [X] T073 [US3] Implement the AST maintainability checker against T064 in `scripts/check_function_length.py`; all safe/unsafe fixtures must produce their expected exit status
- [X] T074 [US3] Implement the no-import/no-database migration checker against T065–T066 in `scripts/migration_check.py`; exact `check` mode must include owner/cache-drift/R-108 rules and pass on the repository
- [X] T075 [US3] Commit credential-free resource, backup, cache, and unresolved evidence inventories against T067 in `deploy/environments.yaml` and `deploy/recovery-evidence.yaml`; source validation must pass while production/recovery readiness intentionally remains nonzero
- [X] T076 [US3] Complete `isolation`, intentionally non-green `production-ready`, `recovery-ready`, and status-only `smoke` against T067 after T009 in `scripts/deployment_check.py`; every fixture must match its expected exit code and every external diagnostic must use the canonical sanitizer
- [X] T077 [US3] Implement non-mutating backend/client drift checks against T068 in `scripts/check_contract_drift.py`; conforming artifacts pass and both stale fixtures fail by path
- [X] T078 [US3] Implement checksum-pinned merge-base compatibility comparison against T069 in `scripts/check_openapi_compatibility.sh`; first-baseline and all change fixtures must match their expected outcomes
- [X] T079 [US3] Configure lockfile, format/lint/type/unit/architecture, and frontend build jobs in `.github/workflows/quality.yml`; workflow static validation must find every required job once
- [X] T080 [US3] Configure PostgreSQL, HTTP integration, generation, drift, safety, compatibility, exact migration check, cache migration, and environment isolation in `.github/workflows/contract.yml`; a workflow contract test must confirm readiness/smoke/capacity are absent
- [X] T081 [US3] Mirror the approved fast static/check subset in `.pre-commit-config.yaml`; a config contract test must prove no mutating generator or operator readiness command is invoked
- [X] T082 [US3] Implement the non-interactive aggregate local gate against T070 after T009 in `scripts/check_all.sh`; a conforming tree exits 0 and each injected controlled violation exits nonzero with sanitized rule/path output
- [X] T083 [US3] Run `backend/tests/architecture/`, `backend/tests/contract/`, `scripts/check_all.sh`, and workflow contract validation; the checkpoint passes only when conforming gates pass and every controlled unsafe fixture fails for its expected rule

---

## Phase 6: User Story 4 — Diagnose Requests Across Shared Boundaries (Priority: P3)

**Goal**: Make server-issued correlation reliable and ensure every external diagnostic string uses the canonical sanitizer without changing observed work.

**Independent Test**: Run concurrent correlation probes and adversarial output tests across log, error, recovery, deployment, and capacity consumers; no protected value may appear and forced sink failure must not change HTTP outcomes.

### Correlation primitive

- [X] T084 [US4] Add correlation concurrency tests in `backend/tests/unit/core/test_correlation_concurrency.py`; 10,000 UUIDs, competing threads/tasks, nesting, exceptions, cleanup, and empty out-of-request state must show zero collision/leak
- [X] T085 [US4] Harden correlation primitives against T084 in `backend/core/correlation.py`; the complete concurrency suite must pass before logging consumers change

### Consumers and integration

- [X] T086 [US4] Add logging-consumer tests after T009 in `backend/tests/unit/core/test_logging.py`; bound/empty IDs, canonical sanitization, reserved-record-key safety, and sink-failure containment must fail until the consumer exists
- [X] T087 [US4] Implement log enrichment and safe emission against T086 in `backend/core/logging.py`; every external string must traverse `sanitize_failure_reason` and sink failure must be contained
- [X] T088 [US4] Register correlation-aware Django `dictConfig` against T086 in `backend/config/settings.py`; named formatter/filter/handler tests must pass with empty defaults outside requests
- [X] T089 [US4] Add concurrent HTTP and available-consumer integration tests in `backend/tests/integration/api/test_concurrent_correlation.py` and `backend/tests/contract/test_sanitized_outputs.py`; distinct IDs, cleanup, and zero protected strings across error, log, and deployment outputs must be observed
- [X] T090 [US4] Implement the independently executable readiness-baseline verification in `backend/tests/contract/test_readiness_baseline.py`; `pytest backend/tests/contract/test_readiness_baseline.py` must exit 0 only when `production-ready` and `recovery-ready` return nonzero for committed `UNRESOLVED` data, `smoke` is status-only, no evidence file changes, and no restore/capacity evidence is fabricated
- [X] T091 [US4] Complete middleware cleanup and diagnostic-failure containment against T089 in `backend/core/middleware.py`; concurrent success/error and forced-sink cases must preserve correct responses and leave empty context
- [X] T092 [US4] Run `backend/tests/unit/core/test_correlation_concurrency.py`, `backend/tests/unit/core/test_event_payload.py`, `backend/tests/unit/core/test_logging.py`, `backend/tests/integration/api/test_concurrent_correlation.py`, and `backend/tests/contract/test_sanitized_outputs.py`; require zero leaks, protected matches, or changed outcomes under sink failure

---

## Phase 7: Recovery, Capacity, Runbook, and Final Verification

**Purpose**: Implement only repository-side operational foundations after canonical primitives and consumers are tested.

- [X] T093 Add failing pure recovery/pre-connect/read-only tests after T009 in `backend/tests/integration/postgres/test_verify_restore.py`; identity collisions must prove zero connection attempts, missing relation, missing category, missing probe registration, partial/incomplete probe, incompatible schema, and probe execution failure must each return `incomplete/unverifiable` with no PASS/OK/readiness, and only a complete successful verification across every required category may pass while all SQL remains read-only
- [X] T094 Implement pure recovery orchestration against T093 in `backend/core/recovery.py`; the full fail-closed and successful PostgreSQL suite must pass using only `RECOVERY_DATABASE_URL`, without a recovery `DATABASES` alias, write SQL, alternate sanitizer, or evidence mutation
- [X] T095 Add failing command-discovery/thin-shim tests in `backend/tests/integration/api/test_management_command_discovery.py`; discovery must resolve `verify_restore` to `operations` and reject recovery policy/query logic in `Command.handle`
- [X] T096 Implement the thin command shim against T095 in `backend/operations/management/commands/verify_restore.py`; discovery, delegation, safe-summary, and exit-status tests must pass while app-registry tests remain green
- [X] T097 Add capacity consumer tests after T009 in `backend/tests/contract/test_capacity_check.py`; under-50 distinct real identities and concurrency under 20 must reject before network I/O, 50/20 with p95 exactly 500 ms may pass, p95 above 500 ms must fail with a remediation owner, every opened connection/resource must close on success and failure, and identities/passwords/tokens/Bearer values/credentialed URLs/secret values must be absent from stdout, stderr, and returned/result artifacts; fixtures and command output must not create evidence or readiness
- [X] T098 Implement capacity `measure` against T097 in `scripts/capacity_check.py` and add `*.identities` to `.gitignore`; every eligibility, boundary, success/failure cleanup, result-artifact, sensitive-output, and evidence-boundary test must pass without writing evidence
- [X] T099 Add pure restore-health evaluator and boundary tests in `backend/tests/unit/core/test_recovery_health.py` and `backend/tests/architecture/test_recovery_health_boundaries.py`; never-run must be `unknown`, stale/current evidence must evaluate deterministically, invalid `HEALTH_RESTORE_DRILL_SECONDS` must fail closed, and core must have no operations/Django/logging-adapter/alert-adapter/telemetry-adapter import
- [X] T100 Implement only the pure restore-health value model/evaluator against T099 in `backend/core/recovery_health.py`; every state and architecture-boundary test must pass with no orchestration or sink integration in core
- [X] T101 Add failing operations consumer tests after T100 and T009 in `backend/tests/unit/operations/test_recovery_health.py`; orchestration must consume the pure evaluator, unknown/stale states must request an alert, external text must use the canonical sanitizer, and forced alert/telemetry sink failure must be contained
- [X] T102 Implement recovery-health orchestration and contained alert/telemetry integration against T101 in `backend/operations/application/recovery_health.py` and `backend/operations/adapters/recovery_alerts.py`; operations tests must pass while the architecture suite proves the dependency direction `core` → operations application → operations adapter
- [X] T103 Add final aggregate cross-consumer sanitizer tests in `backend/tests/contract/test_sanitized_outputs.py`; after T076/T087/T094/T096/T098/T102, adversarial URL/token/password/cookie/object/image/coordinate strings must be absent from log, error, recovery, deployment, capacity, metric-test-adapter, and alert-test-adapter stdout/stderr/result outputs
- [X] T104 Add deployment-runbook contract tests in `backend/tests/contract/test_deployment_runbook.py`; ≥2 AZ, public load balancer, private instances, per-AZ egress, one scheduler, all egress, runtime/admin routing, rotation, migration-before-rollout, isolated restore, session revocation, stale-lease clearing, deferred IaC, APAC caveat, cache provisioning, and evidence boundaries must each be located
- [X] T105 Write the reproducible operator procedures against T104 in `docs/TRIEN_KHAI.md`; the contract test must pass while all unknown provider choices and operator measurements remain explicitly unresolved
- [X] T106 Document entry points, generated ownership, transport, approved Django ownership, cache/recovery commands, CI gates, intentionally non-green readiness, and exclusions in `README.md`; a documentation link check must resolve every referenced path
- [X] T107 Add approved dependency provenance and requirement rationale in `docs/ARCHITECTURE.md`; a dependency audit must find one rationale for every runtime/dev/CI dependency and no unapproved infrastructure package
- [X] T108 Execute every command in `specs/001-project-api-foundation/quickstart.md` from a clean checkout and record monotonic start/end/elapsed time in `specs/001-project-api-foundation/verification/clean-checkout.md`; pass only when success commands exit 0, documented readiness commands return their expected nonzero status without evidence changes, and total elapsed time is at most 15 minutes
- [X] T109 Run `scripts/check_all.sh`, all PostgreSQL integration tests, both production builds, deterministic generation/drift/compatibility, app/persistence ownership checks, T090, and `backend/tests/contract/test_sanitized_outputs.py`; completion requires all quality gates green while only migration/isolation—not production-ready/recovery-ready/smoke/capacity—appear in CI

---

## Dependencies and Resulting Execution Graph

### Blocking graph

```text
T001 governance
  ├─→ T002/T003/T004
  └─→ T005 → T006/T007
              ↓
T008 sanitizer tests → T009 canonical sanitizer
              ↓
T010 tests → T011 deployment primitive
T012 tests → T013 cache primitive
T014 ownership tests → T016 composition/operations registration
T017 settings tests → T018 settings consumer
T019 deployment-cache tests → T020 inventory/check consumer
T021 migration tests → T022 operations migration → T023 PostgreSQL proof
              ↓
          T024 foundation checkpoint
              ↓
US1 tests T025–T033 → primitives/consumers T034–T042 → T043
              ↓
US2 tests T044–T052 → primitives/consumers T053–T062 → T063
              ↓
US3 consumer/gate tests T064–T070 → gates/consumers T071–T082 → T083
              ↓
T084 tests → T085 correlation
T086 consumer tests → T087/T088 consumers → T089 integration → T091 → T092
T075/T076 readiness modes ───────────────→ T090 standalone baseline
              ↓
T093 tests → T094 recovery primitive → T095 discovery tests → T096 command shim
T097 tests → T098 capacity consumer
T099 tests → T100 pure health evaluator → T101 operations tests → T102 operations health consumer
T103 final cross-consumer sanitizer verification
T104 tests → T105 runbook
              ↓
T106/T107 → T108 clean checkout → T109 complete verification
```

### Parallel opportunities

- After T001, T002–T004 are mutually independent; T005 is deliberately serialized because all configuration work depends on its approved vocabulary/examples.
- After Phase 2, test-only tasks marked `[P]` within a story own disjoint fixtures/files and may run concurrently. Their implementations are not parallel with the unfinished tests or primitives they consume.
- T008–T009 establish the canonical sanitizer immediately after governance/setup and before any diagnostic consumer test or implementation; no dependent task is marked `[P]`. US3 may not start before US2 artifacts exist.
- T090 depends only on the committed unresolved inventories and completed readiness/smoke modes from T075–T076; it is independently runnable and does not depend on HTTP correlation or middleware tasks T089/T091.
- Recovery and capacity implementations begin only after T009 and their named consumer tests. Pure health tests precede the core evaluator, operations consumer tests then precede operations orchestration/adapter implementation; aggregate sanitizer verification remains serialized after all consumers.

### Explicit non-applicable behavior

- No authentication/RBAC/object-scope business endpoint exists, so no business authorization or object-scope behavior is invented. Scope-exclusion and origin-denial tests prove the boundary.
- No audit/outbox business model, mutation, idempotency policy, or business transaction is introduced. Recovery reads future-category tables only from an operator-supplied restored database.
- No business database race exists. Real PostgreSQL evidence covers connection/rollback and the approved cache-table migration; future business owners add their own constraints and concurrency tests.
- No restore drill, capacity run, provider resource, production readiness, or resolved infrastructure choice is fabricated by tests or CI.

## Implementation Strategy

1. Complete T001 and all Phase 1 prerequisites; stop on governance mismatch.
2. Establish the tested canonical sanitizer, then pure deployment/cache primitives and prove app/migration ownership on PostgreSQL.
3. Complete US1 and US2 as the MVP foundation with tests before each consumer.
4. Add merge gates, then correlation/sanitization consumers.
5. Add recovery/capacity/runbook primitives without generating evidence.
6. Finish only when T090, final cross-consumer sanitizer verification, clean-checkout validation, and T109 all satisfy their explicit exit criteria.

---

## Phase 8: Convergence

**Purpose**: Close implementation and evidence gaps found by cross-checking the completed task set against the feature specification, plan, and constitution.

- [X] T110 [US3] Make the PostgreSQL contract CI environment executable end to end by aligning the service database/principals and runtime DSN consumed by `backend/tests/integration/postgres/test_database_foundation.py` and `backend/tests/integration/postgres/test_cache_migration.py` with `.github/workflows/contract.yml`; strengthen `backend/tests/contract/test_workflow_contract.py` to reject mismatched PostgreSQL wiring and prove the workflow runs the real PostgreSQL integration and cache-migration gates.
- [X] T111 [P] [US3] Replace fake restore evidence with real PostgreSQL-backed read-only verification in `backend/tests/integration/postgres/test_verify_restore.py` and correct `backend/core/recovery.py` to execute concrete registered probes, consume psycopg cursor rows, and fail closed for missing relations/categories, incomplete results, incompatible schema, and execution failures; mark the suite as PostgreSQL integration evidence and prove the recovery transaction cannot write.
- [X] T112 [P] [US3] Implement the plan's checksum-pinned merge-base `oasdiff` gate in `scripts/check_openapi_compatibility.sh`, remove the custom checker as the source of compatibility truth, and extend `backend/tests/contract/fixtures/compatibility/` plus `backend/tests/contract/test_openapi_compatibility.py` so newly required request-body properties and referenced schemas fail while optional additive changes pass.
- [X] T113 [P] [US3] Replace the synthetic `--sample-ms` capacity path with a real operator-supplied request/resource adapter in `scripts/capacity_check.py`; extend `backend/tests/contract/test_capacity_check.py` to prove eligible 50-identity/concurrency-20 runs perform actual I/O, measure observed latency, close every resource, keep credentials and identities out of all outputs, and never mutate readiness evidence.
- [X] T114 [US1] After T110–T113, execute the documented workflow from an actual clean checkout, correct the direct-origin versus frontend-proxy probe instructions in `specs/001-project-api-foundation/quickstart.md`, and replace `specs/001-project-api-foundation/verification/clean-checkout.md` with evidence that all expected-success commands pass, expected non-green readiness commands remain nonzero without evidence mutation, CI-equivalent PostgreSQL/compatibility gates run, the browser-facing probe succeeds, and total elapsed time remains at most 15 minutes.

---

## Phase 9: Convergence

- [X] T115 Parse each secret `*.identities` entry as a structured record with a stable account identity separate from its Bearer credential, deduplicate and require at least 50 account identities before network activity, update the operator format in `docs/TRIEN_KHAI.md`, and add regression coverage proving 50 different tokens for one account cannot pass in `backend/tests/contract/test_capacity_check.py` per FR-046 and SC-014 (partial)
- [X] T116 Make the pinned `oasdiff` release and checksum non-bypassable by removing or strictly validating `OASDIFF_BIN`, revalidating every cached executable against trusted pinned material before use, and adding contract tests for a tampered cache and arbitrary executable override in `scripts/install_oasdiff.sh`, `scripts/check_openapi_compatibility.sh`, and `backend/tests/contract/test_openapi_compatibility.py` per plan: pinned merge-base oasdiff and T112 (partial)
- [X] T117 Move identity-file reading, decoding, parsing, and capacity target setup inside the canonical sanitized CLI error boundary, and add missing-file, malformed-record, and invalid-encoding tests proving traceback text, paths, identity data, credentials, and offending bytes never reach stdout, stderr, or result artifacts in `scripts/capacity_check.py` and `backend/tests/contract/test_capacity_check.py` per FR-034 and FR-046 (partial)
