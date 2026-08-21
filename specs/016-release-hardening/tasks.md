# Tasks: Code Quality, Build, CI/CD and Production Release Hardening

**Input**: Design documents from `specs/016-release-hardening/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/release-gate.md

**Tests**: Every defect fix has targeted verification before the full release gate.

## Phase 1: Setup and Inventory

**Purpose**: Establish the full repository and automation baseline.

- [X] T001 Record package managers, locks, runtime versions, build/test/format/lint/type commands, environment owners, deployment scripts, contracts, and migration gates in `specs/016-release-hardening/research.md` (Group A)
- [X] T002 [P] Inventory `quality.yml` jobs, triggers, services, dependencies, configuration, commands, security boundary, and problems in `specs/016-release-hardening/contracts/workflow-inventory.md` (Group Q)
- [X] T003 [P] Inventory `contract.yml` jobs, triggers, services, dependencies, configuration, commands, security boundary, and problems in `specs/016-release-hardening/contracts/workflow-inventory.md` (Group Q)
- [X] T004 Record every observed local/CI failure with symptom, root cause, fix, and verification in `specs/016-release-hardening/plan.md` (Group R)

---

## Phase 2: Foundational Tooling Consistency

**Purpose**: Make format, runtime, package, and environment ownership deterministic before behavior checks.

- [X] T005 Add repository line-ending and authored-file normalization rules in `.gitattributes` without rewriting binary/generated/vendor artifacts (Groups B, C)
- [X] T006 Exclude Playwright results and all existing generated/build/vendor artifacts from frontend formatting in `frontend/.prettierignore` (Group B)
- [X] T007 Add explicit formatter check/write command documentation to `specs/016-release-hardening/quickstart.md` and keep CI check-only (Group B)
- [X] T008 Audit `frontend/package.json`, `frontend/package-lock.json`, workflows, and runtime declarations; encode npm/Node 22 consistency in `frontend/package.json` and workflow configuration if drift exists (Group O)
- [X] T009 Audit `backend/pyproject.toml`, `backend/uv.lock`, workflows, and runtime declarations; encode uv/Python 3.12 consistency without a major upgrade (Group O)
- [X] T010 Audit every variable used by frontend build, backend checks/tests, CI, and deployment; correct categories and non-secret examples in `.env.example` and `deploy/migration.env.example` (Group P)

**Checkpoint**: Deterministic tool ownership and configuration are established.

---

## Phase 3: User Story 1 - Trust One Reproducible Quality Gate (Priority: P1) 🎯 MVP

**Goal**: One non-mutating local release gate exercises the same required categories as CI.

**Independent Test**: Run `scripts/check_all.sh` with declared prerequisites and confirm every release category executes through a canonical command and any failure exits non-zero.

- [X] T011 [P] [US1] Format all applicable frontend authored files with existing Prettier and verify `npm --prefix frontend run format:check` (Group C)
- [X] T012 [P] [US1] Format all applicable backend/script authored files with Ruff and verify `uv run --project backend ruff format --check backend scripts` (Group C)
- [X] T013 [P] [US1] Fix Ruff import ordering in `backend/config/composition.py` and verify backend lint (Group E)
- [X] T014 [P] [US1] Fix the redundant cast in `backend/identity/adapters/api/serializers.py` and verify strict mypy (Group E)
- [X] T015 [P] [US1] Add precise QuerySet model parameters in `backend/config/reporting_adapters.py` and verify strict mypy (Group E)
- [X] T016 [US1] Audit frontend ESLint warnings and fix meaningful authored-code diagnostics without blanket suppression in `frontend/src/` and `frontend/eslint.config.mjs` (Group D)
- [X] T017 [US1] Run strict TypeScript checking and correct any real nullability, prop, boundary, environment, chart/map, or generated-type defects in owning files under `frontend/src/` (Group F)
- [X] T018 [US1] Make `scripts/check_all.sh` the complete check-only release gate covering all required categories without duplicated implementation or bypasses (Groups S, T)
- [X] T019 [US1] Update `.pre-commit-config.yaml`, `README.md`, and `specs/016-release-hardening/quickstart.md` so fast pre-commit and full release commands point to the same owners (Group T)

**Checkpoint**: Static and formatting gates are deterministic and the release entry point is complete.

---

## Phase 4: User Story 2 - Reproduce Builds and Tests on Clean Machines (Priority: P1)

**Goal**: Clean installs, tests, backend checks, and production build work without caches or developer-only state.

**Independent Test**: Remove only disposable caches, perform locked installs, and run frontend/backend gates with scoped test configuration.

- [X] T020 [P] [US2] Add a canonical Vitest launcher that keeps jsdom-owned storage globals isolated from experimental Node process globals in `frontend/scripts/run-vitest.mjs` (Group G)
- [X] T021 [US2] Use the canonical launcher from `frontend/package.json`; rerun affected storage test files and the complete frontend suite (Group G)
- [X] T022 [P] [US2] Run backend unit tests from repository root with the canonical project invocation; fix actual regressions only after authority comparison in `backend/tests/unit/` (Group H)
- [X] T023 [P] [US2] Run backend architecture and contract tests from repository root; correct stale path/command assumptions only in owning files under `backend/tests/architecture/` and `backend/tests/contract/` (Groups E, H)
- [X] T024 [US2] Run API integration tests with the declared PostgreSQL test identity and correct actual regressions under `backend/tests/integration/api/` (Group H)
- [X] T025 [US2] Run all PostgreSQL integration tests, including attendance, outbox, task evidence, rollback, deduplication, and migration behavior, without SQLite substitution in `backend/tests/integration/postgres/` (Group I)
- [X] T026 [US2] Inspect concurrency tests for sleeps, leaked transactions, wall-clock dependence, and timing races; replace nondeterministic waits with barriers/events in affected `backend/tests/integration/postgres/` files (Group I)
- [X] T027 [P] [US2] Run a cache-clean frontend production build and fix real server/client, browser API, static rendering, module, CSS, asset, chart/map, or environment failures under `frontend/` (Group J)
- [X] T028 [P] [US2] Add a canonical scoped development environment for Django system checks and run system/deployment checks without weakening `backend/core/deployment.py` (Group K)

**Checkpoint**: Frontend and backend gates reproduce on a clean machine with explicit prerequisites.

---

## Phase 5: User Story 3 - Diagnose Automation Failures at Their Root Cause (Priority: P2)

**Goal**: Every workflow job is secure, reproducible, validation-only, and mapped to canonical local commands.

**Independent Test**: Validate workflow contract tests and execute each workflow's underlying commands locally with matching services/environment.

- [X] T029 [P] [US3] Refactor `backend-quality` in `.github/workflows/quality.yml` to use locked dependencies, canonical backend commands, PostgreSQL 17, scoped non-secret values, and no bypass (Groups Q, R)
- [X] T030 [P] [US3] Refactor `frontend-quality` in `.github/workflows/quality.yml` to use npm immutable install, Node 22, canonical frontend commands, and no build/type/lint bypass (Groups Q, R)
- [X] T031 [US3] Refactor `contract-integration` in `.github/workflows/contract.yml` to remove conflicting duplication while preserving API, PostgreSQL, migration, compatibility, and isolation evidence (Groups Q, R)
- [X] T032 [US3] Verify validation/deployment separation, branch triggers, action versions, cache keys, secret exposure, artifact paths, and permissions across `.github/workflows/quality.yml` and `.github/workflows/contract.yml` (Group Q)
- [X] T033 [US3] Update workflow contract assertions in `backend/tests/contract/test_workflow_contract.py` to encode the hardened mandatory job contract and reject bypasses (Group R)
- [X] T034 [US3] Execute CI-equivalent workflow commands locally and update each entry's final cause/fix/verification status in `specs/016-release-hardening/contracts/workflow-inventory.md` (Group R)

**Checkpoint**: Each workflow/job is concrete, locally reproducible, secure, and validation-only.

---

## Phase 6: User Story 4 - Preserve Contract and Migration Safety (Priority: P2)

**Goal**: Generated API contracts, migrations, and PostgreSQL-specific evidence remain synchronized and mandatory.

**Independent Test**: Regenerate/check both contract artifacts, inspect migration graph/model drift/policy, and execute PostgreSQL contract and concurrency suites.

- [X] T035 [P] [US4] Run canonical backend OpenAPI generation twice and verify byte stability, schema safety, unique explicit operation IDs, and committed drift in `contracts/openapi.yaml` (Group L)
- [X] T036 [P] [US4] Run canonical frontend schema generation/check and verify `frontend/src/shared/api/schema.ts` is derived and synchronized without hand edits (Group M)
- [X] T037 [US4] Run compatibility comparison against merge base and correct only authoritative contract defects in `scripts/check_openapi_compatibility.sh` or owning API schema sources (Groups L, M)
- [X] T038 [P] [US4] Run model/migration drift, graph, leaf, and `makemigrations --check` validation across backend apps (Group N)
- [X] T039 [US4] Run `scripts/migration_check.py check` and migration compatibility tests; correct unsafe expand/contract defects without squashing or casual historical edits (Group N)
- [X] T040 [US4] Verify runtime/admin database identity isolation and Feature 014 readiness gates remain fail closed in `scripts/deployment_check.py`, `deploy/environments.yaml`, and `deploy/recovery-evidence.yaml` (Groups K, N)

**Checkpoint**: Contracts and migrations are synchronized and cannot be bypassed.

---

## Phase 7: Clean Release and Deferred Operations

**Purpose**: Prove the repository gate from clean disposable state and document real-environment prerequisites honestly.

- [X] T041 Remove only `.next`, coverage, test-results, Playwright report, Python bytecode, and tool caches; reinstall with locked npm/uv commands and record clean-run evidence in `specs/016-release-hardening/quickstart.md` (Group S)
- [X] T042 Run the full `scripts/check_all.sh` release gate with isolated PostgreSQL and verify format, lint, type, architecture, migrations, contracts, backend/API/PostgreSQL/concurrency/frontend tests, production build, backend checks, and isolation (Groups S, T)
- [X] T043 [P] Audit existing deferred work and append Feature 016 PENDING records for real deployment, staging smoke/device/Web Push, backup/restore, recovery, capacity, DNS/TLS, hosting/network, and production secrets in `docs/DEFERRED_WORK.md` (Group U)
- [X] T044 Verify `production-ready` and `recovery-ready` still fail for unresolved evidence and document expected non-green status in `specs/016-release-hardening/quickstart.md` (Group U)
- [X] T045 Re-run `speckit-analyze` consistency checks and resolve all machine-fixable CRITICAL/HIGH findings across `specs/016-release-hardening/` and repository gates

---

## Phase 8: Git and Remote Verification

**Purpose**: Complete the authorized feature/develop workflow without touching main.

- [ ] T046 Review `git diff`, verify no secrets/generated manual edits/business drift, commit Feature 016, and push `feature/016-release-hardening`
- [ ] T047 Inspect required GitHub Actions jobs for the feature branch; for each failure add its root cause and targeted fix to `specs/016-release-hardening/contracts/workflow-inventory.md`, rerun locally, commit, and push until green or report NOT VERIFIED if access is unavailable
- [ ] T048 Merge `feature/016-release-hardening` into updated `develop` with `--no-ff` only after every observable required gate passes
- [ ] T049 Run the complete clean release gate on merged `develop`; push `develop` only after it passes and leave `main` untouched

## Dependencies & Execution Order

- Phase 1 precedes Phase 2; Phase 2 blocks all story phases.
- US1 establishes canonical gates and precedes the full US2 clean reproduction.
- US2 and US4 can proceed independently after US1 static foundations; US3 consumes their canonical commands.
- Phase 7 requires US1-US4 complete. Phase 8 requires the final local gate complete.

## Parallel Opportunities

- T002/T003, T008/T009/T010, T011-T015, T020/T022/T023/T027/T028, T029/T030, T035/T036/T038, and T043 can operate on independent files or verification groups.
- PostgreSQL suites must not run concurrently against the same test database unless each process owns an isolated database.

## Implementation Strategy

Deliver US1 first as the minimum viable release gate, then establish clean reproducibility (US2), workflow parity (US3), and contract/migration proof (US4). Run targeted checks after each logical group and the full gate only at the clean-release checkpoint.

## Format Validation

All 49 tasks use the required checkbox, sequential ID, optional parallel marker, story label for story phases, concrete action, and file path or exact repository artifact.
