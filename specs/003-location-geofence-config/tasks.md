---

description: "Dependency-ordered implementation tasks for Feature 003"
---

# Tasks: Location, Geofence, Configuration and Reference Data

**Input**: Design documents from `/specs/003-location-geofence-config/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`,
`quickstart.md`

**Tests**: Required by the specification and Constitution. Test tasks precede the behavior
they constrain and must fail for the prohibited behavior before implementation begins.

**Organization**: Tasks are grouped by user story. Setup/Foundation establish only the
shared boundaries required for independently verifiable story increments.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: genuinely independent after prior-phase prerequisites; different primary files
- **[Story]**: maps to the matching story in `spec.md`
- Every task has one verifiable outcome and concrete paths

## Phase 1: Setup (Shared Structure)

**Purpose**: Register the new business module and test layout without implementing behavior.

- [X] T001 Create the `locations` Django app/package skeleton and register it in `backend/config/settings.py` and backend build/type paths in `backend/pyproject.toml`
- [X] T002 Create matching test package skeletons in `backend/tests/unit/locations/`, `backend/tests/integration/api/locations/`, `backend/tests/integration/postgres/locations/`, and `backend/tests/contract/locations/`
- [X] T003 Add empty typed container/dependency declarations for late composition in `backend/locations/application/container.py` and `backend/locations/application/dependencies.py`

**Checkpoint**: Django and pytest discover the empty `locations` module; no route/model exists.

---

## Phase 2: Foundational (Blocks Every User Story)

**Purpose**: Establish public cross-module ports, canonical errors, shared geometry, schema,
and controlled Config initialization needed by seed and all HTTP stories.

### Tests first

- [X] T004 [P] Add regression tests proving Audit records accept owner-defined closed enums while existing Identity events remain unchanged in `backend/tests/unit/audit/test_records.py`
- [X] T005 [P] Add authorization-gateway tests for action denial before forced-password gating, allowed action then forced-password denial, and permission provenance in `backend/tests/unit/identity/test_authorization_gateway.py`
- [X] T006 [P] Add canonical envelope tests for `LOCATION_VERSION_CONFLICT` and `NOT_FOUND`, including unsafe-details rejection, in `backend/tests/unit/core/test_location_errors.py`
- [X] T007 [P] Add pure Haversine/overlap tests for zero distance, symmetry, antimeridian, known distances, exact sum-of-radii overlap, and non-overlap in `backend/tests/unit/locations/test_geometry.py`
- [X] T008 [P] Add PostgreSQL Location constraint tests for exact decimals, code uniqueness/nonblank/immutability, name/address nonblank, kind/range/radius/version checks, `is_active` NOT NULL/DDL default, duplicate coordinates, parent protection, and indexes in `backend/tests/integration/postgres/locations/test_location_constraints.py`
- [X] T009 [P] Add PostgreSQL Config tests for singleton id=1, fixed timezone, direct-write rejection of `NaN`/positive and negative infinity for every meter-valued field, numeric/order/shift/grace checks, and second-row rejection in `backend/tests/integration/postgres/locations/test_config_constraints.py`
- [X] T010 [P] Add PostgreSQL Holiday tests for unique date, nonblank name, stable indexes, and absence of cross-module cascades in `backend/tests/integration/postgres/locations/test_holiday_constraints.py`
- [X] T011 Add migration compatibility tests proving additive `locations.0001_initial`, one migration leaf, N-1 coexistence, immutable-code trigger installation, and no edits to Feature 001/002 migration history in `backend/tests/integration/postgres/locations/test_migration_compatibility.py`
- [X] T012 Add public snapshot/DTO/port contract tests that reject Django models/raw JSON and assert exactly two LocationKind values, two warning values, two validation results, and seven Feature 003 event values in `backend/tests/unit/locations/test_port_contracts.py`
- [X] T013 Add controlled Config-initialization tests for complete values, approved defaults, non-finite meter-value rejection, inactive/non-Manager denial, invalid atomic failure, repeat rejection, and sanitized evidence in `backend/tests/unit/locations/test_config_initialization.py`
- [X] T014 Add PostgreSQL competing-initializer and rollback tests proving exactly one complete Config and one evidence pair in `backend/tests/integration/postgres/locations/test_config_initialization.py`

### Foundational implementation

- [X] T015 [P] Generalize Audit action/event record typing without changing persistence behavior in `backend/audit/domain/records.py` and re-export the public contract from `backend/audit/ports/recording.py`
- [X] T016 [P] Expose canonical action/account authorization through `backend/identity/ports/authorization.py` and implement it in `backend/identity/application/authorization.py`
- [X] T017 [P] Register `LOCATION_VERSION_CONFLICT` and canonical-envelope `NOT_FOUND` in `backend/core/error_codes.py`, `backend/core/messages.py`, and `backend/core/errors.py`
- [X] T018 [P] Implement pure shared coordinates, Haversine, overlap detection, and warning values in `backend/locations/domain/locations.py` and `backend/locations/domain/geofence.py`
- [X] T019 Define framework-free Location/Config/Holiday snapshots, requests, results, and closed event enums in `backend/locations/domain/`, `backend/locations/application/dto.py`, and `backend/locations/domain/events.py`
- [X] T020 Implement repository, source-data, authorization, audit, and UoW protocols in `backend/locations/ports/repositories.py`, `backend/locations/ports/source_data.py`, and `backend/locations/ports/unit_of_work.py`
- [X] T021 Implement Location, Config, and Holiday models plus additive constraints/indexes/immutable-code trigger in `backend/locations/models.py` and `backend/locations/migrations/0001_initial.py`
- [X] T022 Implement the caller-owned Django UoW and initial repository adapters in `backend/locations/adapters/persistence/unit_of_work.py` and `backend/locations/adapters/persistence/repositories.py`
- [X] T023 Implement Config complete-candidate validation and controlled initialization service in `backend/locations/domain/config.py` and `backend/locations/application/config_admin.py`
- [X] T024 Implement the thin attributable initialization command in `backend/locations/management/commands/initialize_location_config.py`
- [X] T025 Add architecture tests proving `locations` imports Identity/Audit only through public ports and domain remains Django/DRF-free in `backend/tests/architecture/test_locations_boundaries.py`

**Checkpoint**: Shared ports, DB schema, lock-capable repositories, geometry, and one complete
Config can be verified without any Feature 003 HTTP route.

---

## Phase 3: User Story 1 — Establish Trusted Location Reference Data (Priority: P1) 🎯 MVP Part 1

**Goal**: Atomically establish and reconcile exactly 7 centers + 69 shops from two explicit
CSV mappings, with exact coordinates and warning-only overlaps.

**Independent Test**: Initialize Config, run seed twice, and prove 76/7/69, exact source
coordinates/hierarchy, zero second-run changes/evidence, duplicate-coordinate acceptance,
and atomic failure for every invalid input.

### Tests first

- [X] T026 [P] [US1] Add CSV adapter tests for separate header constants, BOM handling, ignored center `STT`, missing-header diagnostics, decimal parsing without float, and parent derivation in `backend/tests/unit/locations/test_csv_source.py`
- [X] T027 [P] [US1] Add seed preflight tests for exact 7/69 counts, cross-file duplicate code rejection, valid duplicate coordinates, invalid numeric/range values, and unmatched parent acceptance in `backend/tests/unit/locations/test_seed_preflight.py`
- [X] T028 [P] [US1] Add seed-service tests for immutable code identity, source/config drift reconciliation, unexpected database identity rejection, unchanged no-op, and sanitized per-row evidence in `backend/tests/unit/locations/test_seed_service.py`
- [X] T029 [P] [US1] Add PostgreSQL first-run verification for exact 76/7/69, all-active/default radius, `HCM020129→HCM020000`, `HCM000079→NULL`, seven parentless centers, the retained duplicate-coordinate pair, and exact 15-decimal coordinates in `backend/tests/integration/postgres/locations/test_seed_exact_data.py`
- [X] T030 [P] [US1] Add PostgreSQL idempotency tests for unchanged second run, drift restoration with one version/evidence increment per changed row, and no 77th identity in `backend/tests/integration/postgres/locations/test_seed_idempotency.py`
- [X] T031 [P] [US1] Add PostgreSQL rollback tests for header/count/code/config/constraint/audit/outbox failures leaving zero partial Location/evidence changes in `backend/tests/integration/postgres/locations/test_seed_atomicity.py`
- [X] T032 [P] [US1] Add PostgreSQL competing-seed tests using real threads/connections and a barrier to prove Config-lock serialization and no duplicate evidence in `backend/tests/integration/postgres/locations/test_seed_concurrency.py`
- [X] T033 [US1] Add management-command tests for active Manager authorization, deny paths, canonical default paths, safe diagnostics, and coordinate-free output in `backend/tests/integration/api/locations/test_seed_command.py`

### Implementation

- [X] T034 [P] [US1] Define immutable center/shop source records, required headers, and separate mappings in `backend/locations/ports/source_data.py`
- [X] T035 [US1] Implement BOM-safe two-file parsing and complete preflight in `backend/locations/adapters/source_data/csv_source.py`
- [X] T036 [P] [US1] Implement bulk lookup/ordered locking/insert/reconcile methods used only by seed in `backend/locations/adapters/persistence/repositories.py`
- [X] T037 [US1] Implement atomic `LocationSeedService` with Config-first locking, exact-count verification, parent linking, warnings, versions, and per-changed-row evidence in `backend/locations/application/seed.py`
- [X] T038 [US1] Implement the thin `seed_locations` command with Manager actor and safe summary output in `backend/locations/management/commands/seed_locations.py`
- [X] T039 [US1] Wire Config initialization and seed dependencies only after their adapters exist in `backend/config/composition.py`
- [X] T040 [US1] Run the US1 unit/command/PostgreSQL suites and record the exact verification commands/outcomes in `specs/003-location-geofence-config/verification/us1-seed.md`

**Checkpoint**: The database contains exactly the canonical 76 Locations and a second run is
a state/evidence no-op.

---

## Phase 4: User Story 2 — View and Safely Maintain Locations (Priority: P1) 🎯 MVP Part 2

**Goal**: All canonical roles list/filter the fixed directory; only Manager performs atomic,
versioned updates with warnings and attributable evidence.

**Independent Test**: Exercise list/update as every role, malformed and server-owned inputs,
duplicate coordinates, overlaps, stale races, rollbacks, and route absence for create/delete.

### Tests first

- [X] T041 [P] [US2] Add query/update service tests for stable ordering/filters/global scope plus immutable fields, warnings, current-version same-value no-op, stale-before-no-op, reason retention, and evidence/version counts in `backend/tests/unit/locations/test_location_services.py`
- [X] T042 [P] [US2] Add API tests for all-role list, Manager mutation/no-op, non-Manager malformed denial, forced-password precedence, malformed/nonpositive/nonexistent id equivalence after gates, server-owned fields, stale-before-no-op, and absent POST/DELETE routes in `backend/tests/integration/api/locations/test_location_api.py`
- [X] T043 [P] [US2] Add API tests proving duplicate coordinates and overlap/radius warnings return 200 while invalid coordinates/radius return 400 with no evidence in `backend/tests/integration/api/locations/test_location_warnings.py`
- [X] T044 [P] [US2] Add PostgreSQL same-version competing-update tests with real workers proving one success, one 409, one version increment, and one evidence pair in `backend/tests/integration/postgres/locations/test_location_update_concurrency.py`
- [X] T045 [P] [US2] Add real-worker PostgreSQL races for different-Location updates, update-vs-seed, update-vs-Config, and same-value-vs-mutation proving Config→Location serialization, independent versions, valid caps, 76 rows, and exact evidence counts in `backend/tests/integration/postgres/locations/test_location_cross_operation_races.py`
- [X] T046 [P] [US2] Add PostgreSQL audit/outbox failure tests proving Location state/version/warnings roll back and precise coordinates never persist in evidence in `backend/tests/integration/postgres/locations/test_location_update_atomicity.py`
- [X] T047 [P] [US2] Add frontend tests for all-role directory, Manager-only controls, warning notices, filters, and stale draft/reason preservation in `frontend/src/features/locations/ui/LocationDirectory.test.tsx`

### Implementation

- [X] T048 [P] [US2] Implement stable Location filters/query and locked optimistic update repository methods in `backend/locations/adapters/persistence/repositories.py`
- [X] T049 [P] [US2] Implement strict Location filter/update serializers and structured warning serializers in `backend/locations/adapters/api/serializers.py`
- [X] T050 [US2] Implement `LocationQueryService` and `LocationAdminService` with Config-first locks, version-before-no-op comparison, overlap recomputation, write-only-on-change audit/outbox, and no create/delete path in `backend/locations/application/queries.py` and `backend/locations/application/location_admin.py`
- [X] T051 [US2] Implement the injected canonical Location permission adapter and thin list/update views with R-116 path parsing only after action/account gates in `backend/locations/adapters/api/permissions.py` and `backend/locations/adapters/api/views.py`
- [X] T052 [US2] Register only GET `/locations/` and PATCH `/locations/{location_id}/` in `backend/locations/adapters/api/urls.py` and compose them under `/api/v1/` in `backend/config/urls.py` and `backend/config/composition.py`
- [X] T053 [US2] Add deterministic OpenAPI annotations for Location list/update/warnings/conflict with no precise coordinate examples in `backend/locations/adapters/api/views.py`
- [X] T054 [US2] Regenerate Location API artifacts in `contracts/openapi.yaml` and `frontend/src/shared/api/schema.ts`
- [X] T055 [US2] Add typed Location list/update calls in `frontend/src/features/locations/api/location-api.ts`
- [X] T056 [US2] Implement directory/filter/edit/conflict state and page UI in `frontend/src/features/locations/model/`, `frontend/src/features/locations/ui/LocationDirectory.tsx`, and `frontend/src/app/locations/page.tsx`
- [X] T057 [US2] Run US2 backend/frontend/contract tests and record success/deny/edge/race outcomes in `specs/003-location-geofence-config/verification/us2-location-api.md`

**Checkpoint**: The fixed Location directory is usable and every write is RBAC-ordered,
optimistic, atomic, warning-aware, and globally scoped.

---

## Phase 5: User Story 3 — Validate GPS and Classify Geofence Membership (Priority: P1)

**Goal**: Provide a pure reusable GPS/Haversine classifier with exactly inside/outside and no
Attendance/Task decision.

**Independent Test**: Validate numeric boundaries and known distances; prove exact radius is
inside, immediately outside is outside, and accuracy cannot change membership.

### Tests first

- [X] T058 [P] [US3] Add boundary/property tests for finite GPS, NaN/infinities, inclusive poles/antimeridian, out-of-range values, and negative/zero accuracy in `backend/tests/unit/locations/test_validated_position.py`
- [X] T059 [P] [US3] Add classifier tests for exact two-value enum, zero/inside/exact-radius/outside, canonical `d=40,r=50` inside and `d=60,r=50` outside regressions, and a signature without `accuracy_m` in `backend/tests/unit/locations/test_geofence_classification.py`
- [X] T060 [P] [US3] Add application-port tests proving `d=40,a=20,r=50,t=25` stays inside, changing accuracy never changes membership, and no candidate/workflow decision is exposed in `backend/tests/unit/locations/test_geofence_service.py`

### Implementation

- [X] T061 [US3] Implement `ValidatedPosition`, exact two-value `LocationValidationResult`, and radius-only classification in `backend/locations/domain/geofence.py`
- [X] T062 [US3] Expose the reusable framework-free geofence application port/service in `backend/locations/ports/geofence.py` and `backend/locations/application/geofence.py`
- [X] T063 [US3] Add architecture regression tests forbidding `UNCERTAIN`, Attendance/Task workflow helpers, candidate selection, and framework imports in `backend/tests/architecture/test_locations_scope_exclusions.py`
- [X] T064 [US3] Run the pure geofence and architecture suites and record boundary outcomes in `specs/003-location-geofence-config/verification/us3-geofence.md`

**Checkpoint**: Future owners can consume a tested pure port; Feature 003 has no geofence HTTP
workflow and no Attendance/Task behavior.

---

## Phase 6: User Story 4 — Manage Shared Operating Configuration (Priority: P2)

**Goal**: All roles read the singleton; only Manager atomically updates complete valid policy
and receives nonblocking radius/accuracy warnings.

**Independent Test**: Exercise every field/invariant, deny precedence, singleton atomicity,
warning-only saves, concurrent updates, and proof that Location radii are never rewritten.

### Tests first

- [X] T065 [P] [US4] Add pure complete-Config candidate tests for defaults, `NaN`/positive and negative infinity rejection on every meter-valued field before comparisons, weekdays, radius/threshold ordering, shifts/graces, and warning-only states without querying Location persistence in `backend/tests/unit/locations/test_config_validation.py`
- [X] T066 [P] [US4] Add Config service tests for partial overlay, singleton/global read, same-value no-op, maximum-cap rejection against both active and inactive Locations, cap equality acceptance, warning production, no Location rewrite, and exact sanitized evidence/version counts in `backend/tests/unit/locations/test_config_services.py`
- [X] T067 [P] [US4] Add API tests for all-role read, Manager mutation/no-op, non-Manager malformed denial, forced-password precedence, server-owned fields, `NaN`/positive and negative infinity rejection for every meter-valued field, safe cap-violation details, other invalid candidates, and absence of create/version conflict in `backend/tests/integration/api/locations/test_config_api.py`
- [X] T068 [P] [US4] Add real-worker PostgreSQL Config-update, Config-vs-Location, and same-value-vs-mutation races proving lock serialization, cap equality acceptance and below-boundary rejection for both active and inactive Locations, one singleton, no rewrite/partial state, and exact evidence versions in `backend/tests/integration/postgres/locations/test_config_update_concurrency.py`
- [X] T069 [P] [US4] Add PostgreSQL failure injection proving Config, audit, and outbox roll back together while Location versions/radii remain unchanged in `backend/tests/integration/postgres/locations/test_config_update_atomicity.py`
- [X] T070 [P] [US4] Add frontend tests for all-role read, Manager-only editor, independent thresholds, field errors, and warning-success presentation in `frontend/src/features/locations/ui/ConfigEditor.test.tsx`

### Implementation

- [X] T071 [P] [US4] Implement locked Config get/update methods plus all-Location cap-violation and affected-Location warning queries in `backend/locations/adapters/persistence/repositories.py`
- [X] T072 [P] [US4] Implement strict Config read/update serializers with complete-candidate field errors in `backend/locations/adapters/api/serializers.py`
- [X] T073 [US4] Complete `ConfigQueryService` and `ConfigAdminService` for partial overlay, cap rejection, same-value no-op, atomic validation, warnings, and write-only-on-change evidence in `backend/locations/application/queries.py` and `backend/locations/application/config_admin.py`
- [X] T074 [US4] Add thin method-specific Config GET/PATCH views and actions in `backend/locations/adapters/api/views.py` and `backend/locations/adapters/api/urls.py`
- [X] T075 [US4] Wire Config services/routes after adapters exist in `backend/config/composition.py` and `backend/config/urls.py`
- [X] T076 [US4] Regenerate Config API additions in `contracts/openapi.yaml` and `frontend/src/shared/api/schema.ts`
- [X] T077 [US4] Add typed Config API calls and singleton editor/read UI in `frontend/src/features/locations/api/location-api.ts`, `frontend/src/features/locations/ui/ConfigEditor.tsx`, and `frontend/src/app/config/page.tsx`
- [X] T078 [US4] Run US4 validation/API/PostgreSQL/frontend suites and record outcomes in `specs/003-location-geofence-config/verification/us4-config.md`

**Checkpoint**: Exactly one complete Config exists; every update is authorized, atomic, and
keeps Attendance/Task thresholds independent without implementing their workflows.

---

## Phase 7: User Story 5 — Maintain Holidays Under Canonical RBAC (Priority: P3)

**Goal**: Manager alone lists, creates, and deletes manually maintained unique-date Holidays.

**Independent Test**: Exercise success, duplicate date, missing delete target, malformed deny
precedence, concurrent create/delete, evidence rollback, and absence of automatic generation.

### Tests first

- [X] T079 [P] [US5] Add Holiday service tests for stable ordering, create/delete success, duplicate-date validation failure, missing-target `NOT_FOUND`, zero failure evidence, sanitized success evidence, and no automatic generation in `backend/tests/unit/locations/test_holiday_services.py`
- [X] T080 [P] [US5] Add API tests for Manager list/create/delete, Leader/Helpdesk malformed denial, inactive and forced-password gates, malformed/nonpositive/nonexistent id equivalence, invalid date/name, duplicate date, and no forbidden side effects in `backend/tests/integration/api/locations/test_holiday_api.py`
- [X] T081 [P] [US5] Add PostgreSQL competing same-date create and double-delete tests proving one winner/evidence pair and unique final state in `backend/tests/integration/postgres/locations/test_holiday_concurrency.py`
- [X] T082 [P] [US5] Add PostgreSQL audit/outbox failure tests proving Holiday create/delete rollback atomically in `backend/tests/integration/postgres/locations/test_holiday_atomicity.py`
- [X] T083 [P] [US5] Add frontend tests for Manager-only navigation, ordered list, duplicate-date feedback, delete confirmation, and missing-target refresh in `frontend/src/features/locations/ui/HolidayManager.test.tsx`

### Implementation

- [X] T084 [P] [US5] Implement ordered Holiday query, unique-date create, and locked delete repository methods in `backend/locations/adapters/persistence/repositories.py`
- [X] T085 [P] [US5] Implement strict Holiday create/read serializers in `backend/locations/adapters/api/serializers.py`
- [X] T086 [US5] Implement `HolidayService` with duplicate-date validation failure, missing-target `NOT_FOUND`, and atomic success evidence in `backend/locations/application/holidays.py`
- [X] T087 [US5] Add Manager-only Holiday GET/POST/DELETE views/routes with R-116 path parsing after action/account gates in `backend/locations/adapters/api/views.py` and `backend/locations/adapters/api/urls.py`
- [X] T088 [US5] Wire Holiday dependencies/routes after service completion in `backend/config/composition.py` and `backend/config/urls.py`
- [X] T089 [US5] Regenerate Holiday API additions in `contracts/openapi.yaml` and `frontend/src/shared/api/schema.ts`
- [X] T090 [US5] Add typed Holiday API calls and management page in `frontend/src/features/locations/api/location-api.ts`, `frontend/src/features/locations/ui/HolidayManager.tsx`, and `frontend/src/app/holidays/page.tsx`
- [X] T091 [US5] Run US5 service/API/PostgreSQL/frontend suites and record outcomes in `specs/003-location-geofence-config/verification/us5-holidays.md`

**Checkpoint**: Holiday reference data is manually and exclusively Manager-managed with
database uniqueness and atomic evidence.

---

## Phase 8: Reference-Data Readiness Gate

**Purpose**: Prevent the intentional post-migration empty-schema state from serving Feature
003 traffic.

- [X] T092 Add PostgreSQL command tests proving readiness passes only for one complete Config plus canonical 76/7/69 codes/hierarchy/source coordinates, fails for every missing/drifted state, emits safe diagnostics, and never mutates/evidences in `backend/tests/integration/postgres/locations/test_reference_readiness.py`
- [X] T093 Implement the read-only readiness service and nonzero-exit `verify_location_reference_ready` command without repair/evidence behavior in `backend/locations/application/readiness.py` and `backend/locations/management/commands/verify_location_reference_ready.py`
- [X] T094 Wire the readiness repository, canonical source, and application service through typed dependencies in `backend/config/composition.py`, and make `backend/locations/management/commands/verify_location_reference_ready.py` resolve only the composed use case without constructing concrete persistence
- [X] T095 Add a release-order contract test and synchronize the operator runbook so `migrate → initialize_location_config → seed_locations → verify_location_reference_ready → enable routes/UI` is mandatory and any nonzero readiness result blocks enablement in `backend/tests/contract/test_deployment_runbook.py` and `docs/TRIEN_KHAI.md`

**Checkpoint**: Deployment has an executable fail-closed gate after initialize+seed and
before Feature 003 routes/UI enablement.

---

## Phase 9: Polish and Cross-Cutting Verification

**Purpose**: Close generated-contract, migration, architecture, privacy, CI, and acceptance
evidence across all completed stories.

- [X] T096 [P] Add contract tests for every Feature 003 path/status/error/warning schema, malformed/nonexistent id equivalence, private/no-store plus request-id header equality, and route absence in `backend/tests/contract/locations/test_api_contract.py`
- [X] T097 [P] Add schema/privacy regressions proving no precise source coordinate appears in OpenAPI examples, AuditLog, OutboxEvent, command output, or logs in `backend/tests/contract/locations/test_coordinate_safety.py`
- [X] T098 [P] Extend architecture ownership scanning for the `locations` business module and prohibited Attendance/Task helpers in `scripts/check_architecture.py`, `backend/tests/architecture/test_module_boundaries.py`, and `backend/tests/architecture/test_locations_scope_exclusions.py`
- [X] T099 Extend strict typing/build/maintainability coverage for `backend/locations` in `backend/pyproject.toml`, `scripts/check_all.sh`, and `.github/workflows/quality.yml`
- [X] T100 Extend contract/PostgreSQL/migration/readiness verification for Feature 003 in `.github/workflows/contract.yml` and `backend/tests/contract/test_migration_safety.py`
- [X] T101 Run deterministic OpenAPI/client generation, safety, drift, and compatibility gates and record results in `specs/003-location-geofence-config/verification/contracts.md`
- [X] T102 Run Ruff, mypy, maintainability, architecture, migration checker, readiness, and backend unit/API/PostgreSQL suites and record results in `specs/003-location-geofence-config/verification/backend-quality.md`
- [X] T103 Run frontend format, lint, typecheck, tests, API drift, and build and record results in `specs/003-location-geofence-config/verification/frontend-quality.md`
- [X] T104 Execute every scenario in `specs/003-location-geofence-config/quickstart.md` and record actual pass/fail evidence in `specs/003-location-geofence-config/verification/quickstart.md`
- [X] T105 Conduct the non-CI Manager usability run for Location/Config/Holiday maintenance and record actual under-two-minute measurements without fabricating p95 in `specs/003-location-geofence-config/evidence/usability.md`
- [X] T106 Run existing operator capacity tooling with at least 50 identities and concurrency 20, require p95 <= 500 ms, and record non-CI pass/fail plus remediation owner in `specs/003-location-geofence-config/evidence/capacity.md`

---

## Dependencies and Execution Order

### Phase dependencies

- **Phase 1 Setup**: no dependency.
- **Phase 2 Foundation**: depends on Phase 1 and blocks all stories.
- **US1 (Phase 3)**: depends on Foundation; provides the canonical 76-row dataset.
- **US2 (Phase 4)**: depends on Foundation and US1 data/seed; reuses geometry Foundation.
- **US3 (Phase 5)**: depends only on Foundation and may run in parallel with US1/US2 after
  shared geometry exists.
- **US4 (Phase 6)**: depends on Foundation; API/UI work may run beside US1, but final
  Config-vs-Location races require US2.
- **US5 (Phase 7)**: depends only on Foundation and may run parallel with US1–US4.
- **Readiness (Phase 8)**: depends on Foundation, US1 seed, Config persistence, and completed
  readiness adapters/services before late composition; its command and release-order contract
  block route/UI enablement.
- **Polish (Phase 9)**: depends on all selected story phases and readiness.

### User-story graph

```text
Setup → Foundation ─┬→ US1 Seed → US2 Location ─────────┐
                    │      └──────────────┐              │
                    ├→ US3 Geofence       ├→ Readiness ──┤→ Polish
                    ├→ US4 Config ────────┘              │
                    └→ US5 Holiday ──────────────────────┘
```

US4's final cross-operation race proof waits for US2, although its pure/API work is otherwise
independent. Suggested deployable MVP is **Foundation + US1 + US2 + US3**: trusted data,
safe maintenance, and the reusable geofence rule.

### Within each story

1. Write and observe failing unit/contract/PostgreSQL/frontend tests.
2. Implement domain/ports/persistence before application services.
3. Implement serializers/permissions/views after services.
4. Wire concrete composition only after adapters/services exist.
5. Regenerate contracts before typed frontend integration.
6. Run the story checkpoint before starting dependent work.

## Parallel Opportunities

- Foundation audit, authorization, error, geometry, and per-entity test files can be
  authored in parallel after the module skeleton.
- US1 parser/preflight/service/PostgreSQL tests are independent test files; CSV parsing and
  persistence adapter work can proceed in parallel after those tests exist.
- US2 API, PostgreSQL race, atomicity, and frontend tests can be authored in parallel;
  repository and serializer implementations touch different files.
- US3 pure validation/classification/service tests are mutually independent and the story
  can run beside US1/US2.
- US4 validation/service/API/PostgreSQL/frontend tests are independent; repository and
  serializer work can run in parallel.
- US5 service/API/PostgreSQL/frontend tests are independent; repository and serializer work
  can run in parallel.
- Final contract/privacy/architecture tests can run in parallel before the sequential full
  verification commands.

## Parallel Examples

### US1

```text
T026 CSV mapping/header/BOM tests
T028 Seed-service reconciliation/evidence tests
T029 Exact-data PostgreSQL tests
T031 Atomic rollback PostgreSQL tests
```

### US2

```text
T042 RBAC/precedence/API tests
T044 Same-version PostgreSQL race tests
T046 Audit/outbox rollback tests
T047 Frontend directory/conflict tests
```

### US4 and US5 after Foundation

```text
US4 pure/API implementation may proceed independently of Holiday work.
US5 service/API/PostgreSQL/frontend work may proceed independently of Location UI.
```

## Implementation Strategy

### MVP first

1. Complete Setup and Foundation.
2. Deliver US1 exact/idempotent seed.
3. Deliver US2 authorized/versioned Location maintenance.
4. Deliver US3 pure GPS/geofence contract.
5. Stop and run the MVP checkpoints before Config/Holiday UI expansion.

### Incremental delivery

1. Add US4 singleton Config management and lock-race evidence.
2. Add US5 Holiday management and unique-date race evidence.
3. Complete cross-cutting generated contract, architecture, migration, static, frontend,
   quickstart, usability, and measured-capacity verification.

## Notes

- `[P]` never means “no prerequisites”; it means independent after the prior listed gate.
- PostgreSQL claims require real transactions, threads/connections, barriers, persisted-state
  assertions, and no SQLite/mock lock proof.
- Coordinates may appear in source/model/API behavior tests where required, but never in
  audit/outbox/log/schema examples or verification output.
- Do not create Location POST/DELETE, Config versioning, Attendance/Task models/workflows,
  geofence HTTP evaluation, map/reverse-geocoding, or new dependencies/infrastructure.

## Phase 10: Convergence

- [X] T107 Conduct and record timed Manager acceptance runs for Location, Config, and Holiday maintenance in `specs/003-location-geofence-config/evidence/usability.md`, marking PASS only when every workflow completes in under two minutes per SC-009 (partial)

## Phase 11: Convergence

- [X] T108 CRITICAL replace the noncanonical `OVERLAPPING_GEOFENCE` synonym with the closed `GEOFENCE_OVERLAP` value across `backend/locations/domain/locations.py`, Feature 003 services/tests, generated `contracts/openapi.yaml`, `frontend/src/shared/api/schema.ts`, and frontend warning presentation per Constitution XII and plan: closed warning vocabulary (contradicts)
- [X] T109 Implement the structured Feature 003 warning objects—including safe related Location ids/codes for overlaps and radius/threshold context for accuracy warnings—in application results, `backend/locations/adapters/api/serializers.py`, views, contract tests, generated API artifacts, typed frontend wrappers, and Location/Config UI tests per plan: API warning contract (partial)
- [X] T110 Compute duplicate-coordinate/geofence-overlap warnings during canonical seed reconciliation and return safe warning categories/codes from `backend/locations/application/seed.py` through `backend/locations/management/commands/seed_locations.py`, with unit, PostgreSQL, and command regressions proving warnings never block or merge records per FR-011 and US1/AC5 (missing)
- [X] T111 Align stale Location conflict details to canonical `current_version` and `submitted_reason` fields without coordinates, then update backend service/API/contract tests, generated artifacts, and frontend conflict handling regressions per US2/AC8 and plan: API/error contract (contradicts)
- [X] T112 Preserve the failing field from complete-candidate Config validation in canonical `VALIDATION_FAILED` details and add backend/frontend coverage for radius ordering, task threshold ordering, weekday, and shift-order errors in `backend/locations/application/config_admin.py`, Config API tests, and `frontend/src/features/locations/ui/ConfigEditor.test.tsx` per US4/AC4 (partial)
- [X] T113 Replace generic dictionary-key-derived Feature 003 outbox payloads with event-specific minimal payload builders and assert Location changed-field names, Config changed fields/warnings, and Holiday id/date/action metadata while preserving redaction and atomicity in `backend/locations/application/evidence.py`, mutation services, and audit/outbox tests per plan: Audit and Outbox (partial)

## Phase 12: Convergence

- [X] T114 CRITICAL make the generated Location PATCH contract require `version`, document every Feature 003 success/error/conflict response and canonical error schema, constrain filter/warning enums, regenerate `contracts/openapi.yaml` and `frontend/src/shared/api/schema.ts`, and strengthen drift/contract assertions in `backend/locations/adapters/api/views.py` and `backend/tests/contract/locations/test_api_contract.py` per Constitution VII and FR-016 (contradicts)
- [X] T115 CRITICAL validate the complete locked Config before any seed reconciliation write, reject invalid weekday or other domain-only Config state atomically, and add unit/PostgreSQL rollback regressions in `backend/locations/application/seed.py` and seed tests per FR-009 and US1/AC1 (missing)
- [X] T116 CRITICAL complete Config API and `ConfigEditor` owning-boundary regressions for successful mutation plus non-finite/non-positive meters, radius ordering, task-threshold ordering, invalid/duplicate weekdays, negative grace values, equal/reversed shifts, field-specific details, preserved drafts, and zero failure evidence per Constitution XI, T112, and US4/AC4 (partial)
- [X] T117 CRITICAL reject unknown Location query parameters and complete Location/Holiday API regressions for invalid filters, server-owned fields, inactive/forced-password precedence, malformed/nonpositive/nonexistent targets, invalid date/name, deny paths, canonical headers, and absence of forbidden side effects in `backend/locations/adapters/api/views.py`, `backend/tests/integration/api/locations/test_location_api.py`, and `backend/tests/integration/api/locations/test_holiday_api.py` per Constitution XI, T042, T080, and the API contract (partial)
- [X] T118 CRITICAL add real PostgreSQL regressions for audit-recorder and outbox-recorder failure rollback, Holiday double-delete concurrency, Location/Config race evidence counts, and consecutive aggregate versions without SQLite/mock claims in `backend/tests/integration/postgres/locations/` per Constitution XI and plan: PostgreSQL race/atomicity strategy (partial)
- [X] T119 strengthen seed postconditions and read-only readiness so active state, singleton default radius, hierarchy, kind, codes, counts, and exact source coordinates are all verified with safe drift diagnostics and PostgreSQL tests in `backend/locations/application/seed.py`, `backend/locations/application/readiness.py`, and `backend/tests/integration/postgres/locations/test_reference_readiness.py` per plan: seed step 7/readiness and SC-013 (partial)
- [X] T120 carry deterministic safe warning codes through Location/Config audit snapshots and seed Location audit/outbox evidence, restructuring seed evidence timing as needed while preserving coordinate redaction, atomicity, and one evidence pair per changed row in `backend/locations/application/evidence.py`, mutation services, and evidence tests per plan: Audit and Outbox and T113 (partial)
- [X] T121 display structured accuracy warnings with both affected Location codes and radius/threshold context in Config/Location notices, with accessible UI regressions in `frontend/src/features/locations/model/location-editor.ts`, `frontend/src/features/locations/ui/ConfigEditor.test.tsx`, and `frontend/src/features/locations/ui/LocationDirectory.test.tsx` per T109 and SC-009 (partial)
- [X] T122 rerun the full deterministic backend, PostgreSQL, contract, frontend, build, quickstart, and non-CI acceptance gates after T114–T121 and update the Feature 003 verification/evidence records with current commands and counts per T101–T103 and plan: CI and Verification (partial)

## Phase 13: Convergence

- [X] T123 Add exhaustive Config domain/API boundary matrices for negative values across all five meter fields, `NaN`/positive and negative infinity/non-positive values across every meter API field, and negative values across all three grace fields, asserting owning-field `VALIDATION_FAILED` details, unchanged singleton state, and zero AuditLog/OutboxEvent evidence per FR-028, FR-039, SC-006, T065, T067, and T116 (partial)
- [X] T124 Complete the PostgreSQL reference-readiness command drift matrix for invalid Config plus missing/extra codes, count, kind, parent hierarchy, coordinates, active state, and default radius, asserting nonzero fail-closed exit, safe diagnostics, no repair, and unchanged AuditLog/OutboxEvent counts per FR-044, SC-013, T092, and T119 (partial)
