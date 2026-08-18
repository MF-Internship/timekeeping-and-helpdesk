# Tasks: Attendance Check-In and Check-Out Core

**Input**: Design documents from `/specs/004-attendance-core/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/attendance-api.yaml`, `quickstart.md`

**Tests**: Required by the feature specification and constitution. Write each
listed test before its paired behavior and confirm it fails for the prohibited or
missing behavior before implementation.

**Organization**: Tasks are grouped by user story. IDs are execution ordered;
`[P]` appears only where work uses distinct files and has no unmet dependency
inside the phase.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Genuinely independent after the phase prerequisite is satisfied
- **[Story]**: User story traceability label
- Every task names concrete files and one verifiable outcome

## Phase 1: Setup (Shared Structure)

**Purpose**: Establish importable attendance and test package structure without
adding behavior or dependencies.

- [X] T001 Scaffold `backend/attendance/{domain,application,ports,adapters/api,adapters/persistence,migrations}/` with package initializers and `backend/attendance/apps.py`, and add `attendance` to the mypy/build package lists in `backend/pyproject.toml` so the empty module imports and is statically discovered.
- [X] T002 Scaffold attendance test packages and reusable factories in `backend/tests/{unit,integration/api,integration/postgres,contract}/attendance/` and `backend/tests/integration/api/attendance/helpers.py` so later tests can create users, Config, canonical Location snapshots, and GPS payloads without copying fixtures.

---

## Phase 2: Foundational (Blocks Every User Story)

**Purpose**: Define the closed vocabulary, schema, ports, adapters, and module
wiring all five stories require.

**Critical**: No user-story implementation starts until this phase passes.

### Tests first

- [X] T003 [P] Add failing closed-vocabulary and state-shape tests for Attendance kind/result/resolution, seven attempt outcomes, five failure-rate members with `LOCATION_CHOICE_REQUIRED` excluded, four anomaly reasons, two punch AuditActions, and the canonical open-session predicate in `backend/tests/unit/attendance/test_domain_contract.py` and `backend/tests/unit/audit/test_records.py`.
- [X] T004 [P] Add failing ORM contract tests for fields, defaults, immutability expectations, accepted-attempt linkage, and absence of `(user, work_date, kind)` uniqueness in `backend/tests/unit/attendance/test_model_contract.py`.
- [X] T005 [P] Add failing port/DTO contract tests proving attendance dependencies expose authorization, clock, one locked Config-plus-all-76-Location reference snapshot, repositories, attempt writer, transactional audit append, and unit-of-work boundaries in `backend/tests/unit/attendance/test_port_contracts.py`.
- [X] T006 [P] Add failing migration compatibility tests for additive tables, database defaults, one attendance migration leaf, no seed mutation, and N-1 schema coexistence in `backend/tests/integration/postgres/attendance/test_migration_compatibility.py`.

### Foundation implementation

- [X] T007 Implement the closed enums, immutable snapshots, report-neutral failure-rate classification, approximate-nearest derivation, and canonical open-session/state-shape helpers in `backend/attendance/domain/attendance.py`, `backend/attendance/domain/attempts.py`, `backend/attendance/domain/sessions.py`, and the two approved actions in `backend/audit/domain/records.py` until T003 passes.
- [X] T008 Define typed command/query DTOs and dependency protocols in `backend/attendance/application/dto.py`, `backend/attendance/application/dependencies.py`, and `backend/attendance/ports/{authorization,reference_data,repositories,attempts,clock,unit_of_work}.py` until T005 passes.
- [X] T009 Implement `Attendance`, `AttendanceSession`, `AttendanceAttempt`, and `AttendanceAnomaly` with the approved fields, enum checks, state checks, one-to-one edges, `PROTECT` history, and exact indexes—including attempt `(work_date,outcome)` and `(nearest_location,outcome)`—in `backend/attendance/models.py` until T004 passes.
- [X] T010 Create the additive initial migration with DB defaults, all named indexes, and named constraints—including `uniq_open_session_per_user` and no daily-kind uniqueness—in `backend/attendance/migrations/0001_initial.py` until T006 passes.
- [X] T011 [P] Add the approved attendance API error constants and Vietnamese canonical messages for `WEAK_GPS`, `OUTSIDE_RADIUS`, `LOCATION_CHOICE_REQUIRED`, `INVALID_LOCATION_CHOICE`, `NO_OPEN_SESSION`, and `SESSION_ALREADY_OPEN` in `backend/core/error_codes.py` and `backend/tests/unit/core/test_attendance_errors.py`.
- [X] T012 Implement the server clock plus ORM snapshot mapping, immutable Attendance writes, canonical open-session queries, Check Out row locking, attempt insertion, and Django unit-of-work adapters in `backend/attendance/adapters/clock.py` and `backend/attendance/adapters/persistence/{repositories,attempts,unit_of_work}.py` so every framework adapter required by T004–T005 exists.
- [X] T013 Implement the Identity authorization and locked Config-plus-76-Location/geofence bridge adapters exclusively in the exempt composition-root file `backend/config/attendance_adapters.py`, exposing one reference snapshot whose active rows are filtered in memory.
- [X] T014 Wire the attendance application container, app registration, and URL factory in `backend/attendance/application/container.py`, `backend/config/composition.py`, `backend/config/settings.py`, and `backend/config/urls.py`, injecting the T012–T013 adapters and existing transactional audit port without adding an OutboxEvent type.
- [X] T015 Extend `backend/tests/contract/test_deployment_runbook.py` and `docs/TRIEN_KHAI.md` so Attendance route/UI enablement occurs only after the existing `verify_location_reference_ready` command succeeds, relying on the established PostgreSQL readiness matrix to prove failure is nonzero and read-only without adding a runtime feature-flag dependency.
- [X] T016 [P] Extend module-boundary and maintainability tests in `backend/tests/architecture/test_module_boundaries.py`, `backend/tests/architecture/test_django_app_registry.py`, and `backend/tests/architecture/test_maintainability.py` to reject Django/DRF imports in attendance domain/application and every foreign business-module models/domain/adapters import below `backend/attendance/`, with `backend/config/` as the only bridge exception.
- [X] T017 Run `backend/tests/unit/attendance/`, `backend/tests/unit/audit/test_records.py`, `backend/tests/unit/core/test_attendance_errors.py`, `backend/tests/integration/postgres/attendance/test_migration_compatibility.py`, `backend/tests/contract/test_deployment_runbook.py`, and `backend/tests/architecture/`, resolving only owning foundation-file defects until all pass with no production workflow implemented.

**Checkpoint**: Schema, ports, adapters, and module wiring are ready; no endpoint
yet accepts a punch.

---

## Phase 3: User Story 1 — Start and Finish a Work Session (Priority: P1) MVP

**Goal**: A HELPDESK user can perform one valid Check In and Check Out; duplicate
Check In and no-session Check Out return canonical state errors, with one correct
attempt per post-boundary request.

**Independent Test**: With one active Location containing the sample, perform
Check In then Check Out and verify two Attendance rows, one closed session,
server-owned fields, and accepted attempts; verify duplicate/no-session and
MANAGER denial paths have exactly the specified side effects.

### Tests first

- [X] T018 [P] [US1] Add failing command-service tests for one-active-candidate Check In/Out with base attendance quality/radius gates, `AUTO_SINGLE`, `SESSION_ALREADY_OPEN`, `NO_OPEN_SESSION`, route-owned kind/user/time/work date, six-decimal duration, first-IN/latest-OUT anomaly behavior for one pair, command-result `punch_index`, one transactional route-specific AuditLog on each success, no OutboxEvent, one post-transaction attempt per expected business result, attempt-writer non-interference, and unexpected-infrastructure 5xx producing no attempt in `backend/tests/unit/attendance/test_commands.py`.
- [X] T019 [P] [US1] Add failing API precedence tests for unauthenticated, inactive, password-change-required, MANAGER/LEADER denied, malformed body, and client-owned `user_id`/`kind` cases—asserting zero Attendance and zero AttendanceAttempt before the boundary—in `backend/tests/integration/api/attendance/test_authorization_and_boundary.py`.
- [X] T020 [P] [US1] Add failing API success/state tests for first Check In, duplicate Check In, Check Out, and Check Out without session, including one-candidate `AUTO_SINGLE`, command `punch_index`, projected `resolved_address`, and `maps_url` derived from stored captured decimals without rounding or Location-coordinate substitution, plus canonical envelopes and exact Attendance/Session/Attempt/AuditLog/Outbox counts, in `backend/tests/integration/api/attendance/test_session_actions.py`.
- [X] T021 [P] [US1] Add failing PostgreSQL catalog and behavior tests for the exact `uniq_open_session_per_user` predicate, all three required AttendanceAttempt indexes, and `closed_by_job=True, check_out=NULL` not blocking a later session in `backend/tests/integration/postgres/attendance/test_open_session_constraint.py`.
- [X] T022 [P] [US1] Add failing real-PostgreSQL Check In race tests using two connections and a barrier: 100 trials must yield one accepted punch plus one `SESSION_ALREADY_OPEN`, exactly one open session, and one surviving correctly classified attempt per request in `backend/tests/integration/postgres/attendance/test_check_in_concurrency.py`.
- [X] T023 [P] [US1] Add failing real-PostgreSQL Check Out race tests using two connections and a barrier: one request must create the OUT and close the locked session while the other returns `NO_OPEN_SESSION`, with one surviving correctly classified attempt per request in `backend/tests/integration/postgres/attendance/test_check_out_concurrency.py`.

### Implementation

- [X] T024 [US1] Implement `AttendanceCommandService.check_in()` and `.check_out()` through server timestamp/work-date capture, canonical session-state evaluation, base attendance quality/radius decisions, one-active-candidate `AUTO_SINGLE`, exact six-decimal session duration, one-pair anomaly reconciliation, accepted Attendance/session mutation, route-specific sanitized AuditLog append, and command-result punch-index projection in `backend/attendance/application/{commands,anomalies,projections}.py` and `backend/attendance/domain/{attendance,sessions}.py` until all T018 success/state cases pass.
- [X] T025 [US1] Translate only the named partial-unique `IntegrityError` after rollback, lock the open session for Check Out, and preserve atomic Attendance/Session writes in `backend/attendance/adapters/persistence/repositories.py` until the session-state/final-row assertions of T021–T023 pass; T026 owns their attempt assertions.
- [X] T026 [US1] Implement exactly-once attempt-draft finalization outside the business transaction on accepted and expected-business-rejection paths, skip attempt persistence for unexpected infrastructure exceptions, and preserve the original result on a writer failure while emitting sanitized telemetry and never retrying, in `backend/attendance/application/commands.py` and `backend/attendance/adapters/persistence/attempts.py` until T018 and T022–T023 pass.
- [X] T027 [US1] Implement strict command request, punch, Location, session, and command-result serializers with finite/range checks, explicit unknown/server-owned-field rejection, `resolved_address=Location.address`, and one shared Maps helper that URL-encodes the stored captured decimal strings exactly—without rounding, Location-coordinate substitution, client URL input, or network lookup—in `backend/attendance/adapters/api/serializers.py` and `backend/attendance/adapters/api/maps.py`.
- [X] T028 [US1] Implement thin route-specific permission classes that invoke the injected attendance authorization port's Check In/Check Out decisions—without importing Identity domain/models/adapters—and thin views with canonical error mapping in `backend/attendance/adapters/api/permissions.py` and `backend/attendance/adapters/api/views.py` until T019–T020 pass.
- [X] T029 [US1] Register `/api/v1/attendance/check-in` and `/api/v1/attendance/check-out` through `backend/attendance/adapters/api/urls.py`, `backend/config/urls.py`, and `backend/config/composition.py` so both routes resolve only through the configured attendance container.
- [X] T030 [US1] Add command-endpoint schema assertions and executable example validation for request ownership, success projections, disjoint 409/422 error variants, candidate-list cardinality, and absence of precise coordinate examples in `backend/tests/contract/attendance/test_command_contract.py`, then annotate the views in `backend/attendance/adapters/api/views.py` until every instance matches exactly one declared branch.
- [X] T031 [US1] Regenerate `contracts/openapi.yaml` and `frontend/src/shared/api/schema.ts`, then add typed `checkIn`/`checkOut` wrappers using only `apiClient` in `frontend/src/features/attendance/api/attendance-api.ts` and verify existing API-generation/transport contract tests remain green.

**Checkpoint**: US1 is deployable as a backend/API MVP and independently proves
the partial constraint, rollback semantics, double-tap race, deny paths, and one
complete session.

---

## Phase 4: User Story 2 — Work Multiple Sessions in One Date (Priority: P1)

**Goal**: Support strict `IN → OUT → IN → OUT` on one local date, with distinct
sessions, different boundary Locations, and duration equal to the sum of closed
intervals rather than first-to-last elapsed time.

**Independent Test**: Complete two same-day pairs and verify four Attendance
rows, two closed sessions, no daily-kind uniqueness failure, separate IN/OUT
Locations, and exact per-session durations.

### Tests first

- [X] T032 [P] [US2] Add failing pure transition/duration tests for strict alternation, `ROUND_HALF_UP` quantization to six decimal minutes including a microsecond delta not exactly representable in decimal minutes, session work date inherited from Check In, and different Check In/Out Locations in `backend/tests/unit/attendance/test_session_lifecycle.py`.
- [X] T033 [P] [US2] Add a failing PostgreSQL test that inserts/executes two same-user same-date IN/OUT pairs and schema-inspects the absence of every equivalent daily-kind unique constraint in `backend/tests/integration/postgres/attendance/test_multiple_sessions.py`.
- [X] T034 [P] [US2] Add a failing API journey for `IN → OUT → IN → OUT` with Location A/B boundaries, exact two-session pairing, and attempt counts in `backend/tests/integration/api/attendance/test_multiple_sessions.py`.
- [X] T035 [P] [US2] Add failing anomaly reconciliation tests for late Check In, early Check Out, and late Check Out equality/over-threshold boundaries, proving only the first daily IN and latest daily OUT carry governed anomalies, middle punches do not, and a new latest OUT removes the superseded OUT anomaly in `backend/tests/unit/attendance/test_anomaly_reconciliation.py`.

### Implementation

- [X] T036 [US2] Extend US1's session lifecycle/repository operations to create a new session after any user-closed or job-closed session and pair each OUT only with the current open session while reusing the already-tested six-place duration helper in `backend/attendance/domain/sessions.py` and `backend/attendance/adapters/persistence/repositories.py` until T032–T034 pass.
- [X] T037 [US2] Extend US1's one-pair anomaly reconciliation to first-IN/latest-OUT semantics across multiple same-day pairs, including removal of a superseded latest-OUT anomaly, inside the punch transaction in `backend/attendance/application/anomalies.py` and `backend/attendance/application/commands.py` until T035 passes without adding job scheduling or new anomaly values.
- [X] T038 [US2] Add regression assertions to `backend/tests/integration/api/attendance/test_multiple_sessions.py` that a second-pair outside/invalid punch does not mutate either completed session, then make the minimal command-service correction in `backend/attendance/application/commands.py` needed for those assertions.

**Checkpoint**: US2 independently proves multiple sessions and strict pairing on
one work date without restoring daily uniqueness.

---

## Phase 5: User Story 3 — Validate Fresh and Trustworthy GPS (Priority: P1)

**Goal**: Enforce fresh finite GPS, the attendance-specific accuracy threshold,
and independent radius membership for every punch.

**Independent Test**: Exercise malformed/stale samples, equality boundaries,
weak GPS, outside radius, and the two canonical `d/a/r/t` truth-table fixtures;
verify pre-boundary versus post-boundary attempt behavior.

### Tests first

- [X] T039 [P] [US3] Add failing serializer tests for non-finite/range violations, negative accuracy, optional captured time, exactly-60-second freshness, stale samples, and all server-owned fields in `backend/tests/unit/attendance/test_serializers.py`.
- [X] T040 [P] [US3] Extend pure rule tests beyond US1's one-candidate path for `accuracy_m <= threshold`, `distance_m <= radius_m`, equality acceptance, `d=40/a=20/r=50/t=25` acceptance, and `d=60/a=5/r=50` rejection in `backend/tests/unit/attendance/test_gps_policy.py`.
- [X] T041 [P] [US3] Add failing API tests for `WEAK_GPS`, `OUTSIDE_RADIUS`, candidate-count null versus zero, repeated second-pair GPS enforcement, and zero pre-boundary attempts for malformed/stale inputs in `backend/tests/integration/api/attendance/test_gps_gates.py`.
- [X] T042 [P] [US3] Add a failing PostgreSQL interleaving test proving Attendance evaluation and concurrent Config/Location mutation obey Config→Location ordering, load one 76-Location snapshot, and derive both nearest and active-only candidates from that same snapshot without mixed versions in `backend/tests/integration/postgres/attendance/test_reference_data_concurrency.py`.

### Implementation

- [X] T043 [US3] Complete boundary validation and server-age checking in `backend/attendance/adapters/api/serializers.py` using one injected/server receipt time so T039 and pre-boundary T041 cases pass without creating attempts.
- [X] T044 [US3] Extend US1's pure attendance quality and radius decisions to every rejection/equality fixture in `backend/attendance/domain/attendance.py`, reusing distance evaluation without passing accuracy into geofence classification, until T040 passes without regressing US1's success path.
- [X] T045 [US3] Complete locked Config-plus-all-76-Location snapshot loading through `backend/config/attendance_adapters.py` and `backend/attendance/application/commands.py`, deriving active-only candidates from that same snapshot so quality runs before candidate matching and T041–T042 pass with no foreign-module import below `backend/attendance/`.
- [X] T046 [US3] Persist `WEAK_GPS` with null `candidate_count` and `OUTSIDE_RADIUS` with zero `candidate_count`, never creating Attendance for either outcome, in `backend/attendance/application/commands.py` and `backend/attendance/adapters/persistence/attempts.py`.
- [X] T047 [P] [US3] Add failing browser lifecycle tests for user-gesture permission, `maximumAge: 0`, fresh submit samples, stop-on-hidden/unmount/cancel/timeout/submit, and no background submission in `frontend/tests/unit/attendance/use-foreground-position.test.tsx`.
- [X] T048 [US3] Implement the bounded foreground geolocation state machine in `frontend/src/features/attendance/model/use-foreground-position.ts` until T047 passes without persisting coordinate streams.

**Checkpoint**: US3 independently proves every freshness/quality/radius boundary
and preserves the exact attempt boundary.

---

## Phase 6: User Story 4 — Resolve Overlapping Location Candidates (Priority: P1)

**Goal**: Resolve zero/one/many active candidates deterministically, require a
choice for ambiguity, revalidate supplied choices against a fresh sample, and
keep all-76 nearest diagnostics separate from active candidates.

**Independent Test**: Exercise zero, one, and multiple candidates; confirm a
fresh valid selection succeeds, an invalid/moved selection returns latest
candidates, inactive nearest is diagnostic only, and coincident candidates stay
separate while R-119 selects diagnostic nearest by code.

### Tests first

- [X] T049 [P] [US4] Add failing pure tests for zero/one/many cardinality, `AUTO_SINGLE`, `USER_SELECTED`, invalid-choice revalidation, all-76 nearest, inactive nearest, `(distance_m, code)` diagnostic ties, and `nearest_is_approximate` being true exactly for `WEAK_GPS` in `backend/tests/unit/attendance/test_candidate_resolution.py`.
- [X] T050 [P] [US4] Add failing API tests for `LOCATION_CHOICE_REQUIRED` and `INVALID_LOCATION_CHOICE` status/envelopes, latest candidate lists, accepted user selection, no persisted candidate array, and authoritative precedence where a supplied id with zero recomputed candidates returns `OUTSIDE_RADIUS` without a candidate list in `backend/tests/integration/api/attendance/test_location_choice.py`.
- [X] T051 [P] [US4] Add failing PostgreSQL/source-data tests proving inactive nearest never enters candidates and the exact `HCM000079`/`HCM010005` tie stores nearest `HCM000079` while returning both active candidates in `backend/tests/integration/postgres/attendance/test_nearest_location.py`.
- [X] T052 [P] [US4] Add failing frontend tests for choice-required rendering, latest-candidate replacement, invalid-choice recovery, and a new GPS acquisition before selected-id resubmission in `frontend/tests/unit/attendance/location-choice.test.tsx`.

### Implementation

- [X] T053 [US4] Extend US1's single-candidate resolver with multiple-candidate choice and selection revalidation in `backend/attendance/domain/attendance.py` and `backend/attendance/application/commands.py`, preserving zero-candidate `OUTSIDE_RADIUS` precedence and forbidding nearest/history/name fallback, until T049–T050 pass.
- [X] T054 [US4] Implement all-76 nearest observation ordered by `(distance_m, code)` from T045's locked reference snapshot, derive the approximate marker in `backend/attendance/domain/attempts.py`, and persist nearest independently of candidate execution in `backend/attendance/adapters/persistence/attempts.py` until T049 and T051 pass.
- [X] T055 [US4] Add specialized canonical candidate-error serialization to `backend/attendance/adapters/api/serializers.py` and `backend/attendance/adapters/api/views.py` so both 409/422 responses expose only the current active candidate list required by the contract.
- [X] T056 [US4] Extend `frontend/src/features/attendance/api/attendance-api.ts` to preserve typed candidate error payloads and implement choice/submission states in `frontend/src/features/attendance/model/attendance-state.ts` without hand-written wire-case mapping.
- [X] T057 [US4] Implement `frontend/src/features/attendance/ui/LocationChoice.tsx` and connect it to a new-sample selected-id resubmission flow using `use-foreground-position.ts` until T052 passes.

**Checkpoint**: US4 independently proves all candidate paths, fresh revalidation,
inactive diagnostics, and the canonical equal-distance tie without silent choice.

---

## Phase 7: User Story 5 — Review Today's Own Attendance (Priority: P2)

**Goal**: Return and render the authenticated user's local-day sessions, unified
punch indexes, total closed duration, and canonical next-action state.

**Independent Test**: Seed two closed sessions and verify only the actor's local
date is returned, punches are indexed `1..4`, total excludes breaks/open/job-closed
sessions, and no client user id can alter object scope.

### Tests first

- [X] T058 [P] [US5] Add failing query-service tests for Asia/Ho_Chi_Minh today, actor-only filtering, `(recorded_at,id)` deterministic ordering, unified one-based `punch_index`, canonical open predicate, and closed-duration sum in `backend/tests/unit/attendance/test_today_query.py`.
- [X] T059 [P] [US5] Add failing API tests for HELPDESK self data, another user's punches and Maps URLs being excluded, rejected user-id query/body fields, open/job-closed projections, and permission/account-state precedence in `backend/tests/integration/api/attendance/test_today.py`.
- [X] T060 [P] [US5] Add failing contract tests for `/api/v1/attendance/today`, snake_case punch/session fields, nullable OUT/duration fields, actor-only input, and coordinate-schema safety in `backend/tests/contract/attendance/test_today_contract.py`.
- [X] T061 [P] [US5] Add failing frontend tests for loading/empty/error states, Check In versus Check Out control from `has_open_session`, unified timeline, separate boundary Locations, total duration, capability-based action hiding, post-command refresh, safe Maps links (`_blank` plus `noopener noreferrer`) with no iframe/SDK, and fake-timer proof that completed reads render without artificial delay in `frontend/tests/unit/attendance/attendance-panel.test.tsx`.

### Implementation

- [X] T062 [US5] Implement actor-scoped timeline/session repository reads and duration aggregation in `backend/attendance/adapters/persistence/repositories.py` with no persisted punch index.
- [X] T063 [US5] Implement `AttendanceQueryService.today()` and read-model DTOs in `backend/attendance/application/queries.py` and `backend/attendance/application/dto.py`, reusing the command-result ordering/index helper from `backend/attendance/application/projections.py`, until T058 passes.
- [X] T064 [US5] Implement today serializers/view and register `/api/v1/attendance/today` with `attendance.view.self` in `backend/attendance/adapters/api/{serializers,views,urls}.py` until T059–T060 pass.
- [X] T065 [US5] Regenerate `contracts/openapi.yaml` and `frontend/src/shared/api/schema.ts`, then add `getTodayAttendance()` to `frontend/src/features/attendance/api/attendance-api.ts` so generated types cover all three final endpoints.
- [X] T066 [US5] Implement `frontend/src/features/attendance/ui/{AttendancePanel,TodayTimeline}.tsx` and `frontend/src/app/attendance/page.tsx`, composing canonical today refresh, action state, Location choice, GPS readiness, capability presentation, and authorized safe Maps links without iframe/SDK until T061 passes.

**Checkpoint**: All five stories are independently verifiable and the employee
page reconciles mutations with the server-owned read model.

---

## Phase 8: Polish and Cross-Cutting Verification

**Purpose**: Prove privacy, contract, migration, concurrency, and static gates
across the completed feature without broadening scope.

- [X] T067 [P] Add a parameterized seven-outcome AttendanceAttempt contract matrix covering exact fields, accepted-only Attendance linkage, nearest metadata, null/zero/positive `candidate_count`, absence of candidate arrays, and exactly one writer invocation; also prove pre-boundary and unexpected-infrastructure 5xx paths invoke the writer zero times and that writer failure is not retried or relabeled, in `backend/tests/unit/attendance/test_attempt_matrix.py` and `backend/tests/integration/api/attendance/test_attempt_outcomes.py`.
- [X] T068 [P] Add regression tests proving each successful Check In/Out creates exactly one AuditLog with the exact action, `target_type=Attendance`, new Attendance `target_id`, `before={}`, and only `attendance_id/kind/work_date/location_id/session_id` in `after`; force business rollback on PostgreSQL to prove Attendance/Session/anomaly/AuditLog atomicity; prove rejected punches create no AuditLog, routine punches create no OutboxEvent, and all audit/attempt-writer/infrastructure telemetry excludes coordinates, accuracy, device metadata, request IP, and maps URLs, in `backend/tests/integration/api/attendance/test_observability.py`, `backend/tests/integration/postgres/attendance/test_audit_atomicity.py`, and `backend/tests/unit/attendance/test_telemetry_safety.py`.
- [X] T069 [P] Extend generated-contract safety and compatibility coverage for all attendance schemas/errors, including executable validation that each 409/422 example matches exactly one disjoint error branch, in `backend/tests/contract/test_openapi_safety.py`, `backend/tests/contract/test_openapi_compatibility.py`, and `frontend/tests/contract/api-generation.test.ts`.
- [X] T070 Run the repository migration checker plus the attendance migration/PostgreSQL catalog suites, and record any required implementation correction only in `backend/attendance/migrations/0001_initial.py` and its owning tests until additive/N-1/single-leaf/constraint checks pass.
- [X] T071 Run all `postgres` attendance tests—including 100-trial Check In double tap, concurrent Check Out winner/loser, rollback survival, audit atomicity, row locking, exact attempt indexes, multiple sessions, and same-snapshot reference-data interleavings—and correct only the owning attendance persistence/application/config-composition files until the suite is green on real PostgreSQL.
- [X] T072 Run backend Ruff formatting/lint, strict mypy, Django checks, unit/API/contract/architecture suites, and update only the owning `backend/attendance/`, `backend/config/`, `backend/core/`, or backend test files until every static and behavioral backend gate passes.
- [X] T073 Run frontend Prettier check, ESLint, TypeScript, Vitest, API transport boundaries, and generated-client drift checks, updating only `frontend/src/features/attendance/`, `frontend/src/app/attendance/`, generated schema, or owning tests until every frontend gate passes.
- [X] T074 Execute `scripts/check_all.sh` with the approved PostgreSQL environment and verify the single full CI-equivalent command passes without a wall-clock latency assertion and without adding dependencies, infrastructure, secrets, precise coordinate examples, or generated-artifact hand edits.
- [X] T075 Create and run the pre-release-only `scripts/attendance_interaction_check.py` harness for 100 PostgreSQL-backed command-plus-today-read trials with 50 users, exactly 76 canonical Locations, and 20 same-day sessions for the actor; pass only when at least 95 trials finish within 2 seconds and record run metadata plus p95—but no GPS or secrets—in `specs/004-attendance-core/evidence/latency-acceptance.md` without wiring the harness into CI.
- [ ] T076 **DEFERRED — human acceptance will be scheduled later.** Conduct the documented usability acceptance with at least 20 representative HELPDESK participants and record participant/scenario/success/blocker counts—but no GPS coordinates—in `specs/004-attendance-core/evidence/usability-acceptance.md`; pass only when at least 19 complete both the unambiguous punch and multiple-Location choice without assistance.
- [ ] T077 **DEFERRED — blocked only by T076.** After T076 is executed, finish the remaining quickstart acceptance, map the final Definition of Done checkbox in `specs/004-attendance-core/spec.md` to the passing SC-007 and existing SC-008 evidence, and update only those two documentation files if command names or test paths differ from the verified implementation.

### Deferred acceptance record

- Deferred on: 2026-08-18 at the user's direction; usability testing will be
  conducted later.
- Completed scope: implementation, automated tests, PostgreSQL concurrency and
  migration checks, full CI-equivalent verification, and SC-008 latency evidence.
- Remaining scope: T076's real-user SC-007 exercise, followed by the documentary
  close-out in T077. Deferral is not a pass, waiver, or change to the acceptance
  threshold.
- Resume condition: a scheduled test environment and at least 20 representative
  HELPDESK participants are available.
- Completion condition: at least 19 participants complete both governed scenarios
  without assistance, aggregate evidence is recorded without GPS or identities,
  and the final combined DoD checkbox is then checked.

---

## Dependencies and Execution Order

### Phase dependencies

- Phase 1 has no dependency.
- Phase 2 depends on Phase 1 and blocks every user story.
- US1 depends on Phase 2 and establishes the command/API/transaction backbone.
- US2 depends on US1 because it extends the same session command and repository.
- US3 depends on US1 because it completes the GPS rejection branches of the
  established command; it does not depend on US2 behavior.
- US4 depends on US3 because candidate resolution occurs only after the quality
  gate and uses the same reference-data path.
- US5 depends on US1 persistence/API foundations; after US1 it can proceed in
  parallel with US2/US3 when file ownership is separated.
- Phase 8 depends on every story selected for delivery; the full Feature 004 DoD
  requires all five, T075's pre-release latency evidence, and T076's documented
  usability evidence before T077 performs the final DoD mapping.

### User-story graph

```text
Setup → Foundation → US1 ─┬→ US2 ─────────────┐
                          ├→ US3 → US4 ───────┼→ Cross-cutting verification
                          └→ US5 ─────────────┘
```

### Within-story order

- Author all listed failing tests first.
- Implement pure domain rules before application orchestration.
- Implement application orchestration before API delivery and frontend wiring.
- Regenerate OpenAPI before writing/adjusting generated-client consumers.
- Run each story's independent test checkpoint before starting its dependent
  story.

## Genuine Parallel Opportunities

### US1

After Phase 2, T018–T023 can be authored concurrently because they occupy distinct
test files. Implementation T024–T031 is sequential because it converges on
`commands.py`, persistence adapters, views, URLs, and generated contracts.

### US2

T032–T035 can be authored concurrently in distinct test files. T036–T038 are
sequential because session lifecycle and anomaly reconciliation meet in the same
command transaction.

### US3

T039–T042 and T047 can be authored concurrently. T043–T046 are sequential on the
backend command path; T048 can proceed independently after T047.

### US4

T049–T052 can be authored concurrently. Backend T053–T055 is sequential; frontend
T056–T057 follows the generated API types and GPS hook.

### US5

T058–T061 can be authored concurrently. Backend T062–T064 is sequential;
T065 precedes frontend T066.

## Parallel Examples

```text
US1: T018 command tests | T019 authorization tests | T020 API state tests |
     T021 constraint tests | T022 Check In race | T023 Check Out race

US3: T039 serializer boundaries | T040 pure GPS truth table |
     T041 API GPS outcomes | T042 PostgreSQL interleaving |
     T047 browser geolocation lifecycle

US5: T058 query projection | T059 API object scope | T060 contract schema |
     T061 frontend read/action states
```

## Implementation Strategy

### MVP first

1. Complete Setup and Foundation.
2. Complete US1 through T031.
3. Stop and run the US1 independent checkpoint, including the real PostgreSQL
   partial-index, rollback, and 100-trial double-tap proofs.
4. Demo one Check In/Out pair only if all deny and side-effect assertions pass.

### Incremental completion

1. Add US2 for multiple same-day sessions.
2. Add US3 for complete freshness/quality/radius behavior.
3. Add US4 for overlap choice, R-118, and R-119.
4. Add US5 for the actor-scoped today read model and employee UI.
5. Complete Phase 8 and the full Definition of Done.

## Notes

- Tasks intentionally add no dependency, queue, cache, reverse geocoder, tracking
  service, or OutboxEvent. They add only the two AuditActions now approved in
  CHOT for successful punches.
- `[P]` never means “safe to edit the same file concurrently.”
- PostgreSQL-specific claims are complete only when the `postgres`-marked tests
  run against real competing connections.
- Generated `contracts/openapi.yaml` and `frontend/src/shared/api/schema.ts` are
  regenerated, never hand-edited.
- No task authorizes MANAGER/LEADER Check In/Out, client-owned user/kind/time, a
  persisted `punch_index`, daily-kind uniqueness, or accuracy-adjusted radius.
