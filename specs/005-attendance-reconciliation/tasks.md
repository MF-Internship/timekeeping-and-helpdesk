---

description: "Implementation tasks for Attendance Sessions, Anomalies and Daily Reconciliation"
---

# Tasks: Attendance Sessions, Anomalies and Daily Reconciliation

**Input**: Design documents from `/specs/005-attendance-reconciliation/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/job-health-api.yaml`, `quickstart.md`

**Tests**: Tests are required by the feature specification, constitution, and user request. Test tasks precede the behavior they prove; PostgreSQL claims use real PostgreSQL.

**Organization**: Tasks are grouped by user story so each increment has a verifiable outcome. `[P]` is used only where tasks touch independent files and do not depend on unfinished tasks in the same phase.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel after its phase prerequisites are complete
- **[MANUAL]**: Requires a real environment or human acceptance; automation may prepare evidence but cannot self-approve it
- **[DEFERRED]**: Explicitly moved outside the automated Feature 005 closeout and does not count as implemented evidence
- **[Story]**: Maps to US1–US4 in `spec.md`
- Every task names its concrete owning files

---

## Phase 1: Setup (Shared Structure)

**Purpose**: Establish the approved attendance/operations layer locations without adding behavior or dependencies.

- [X] T001 Create the missing Python package scaffolding for attendance reconciliation and operations job health in `backend/attendance/management/__init__.py`, `backend/attendance/management/commands/__init__.py`, `backend/operations/domain/__init__.py`, `backend/operations/ports/__init__.py`, `backend/operations/adapters/api/__init__.py`, and `backend/operations/adapters/persistence/__init__.py`.
- [X] T002 Extend production module-boundary coverage to include `backend/operations/`, reject operations↔attendance internal imports outside `backend/config/`, and reject job-health role imports/comparisons outside Identity authorization in `backend/tests/architecture/test_module_boundaries.py`, `backend/tests/architecture/test_django_app_registry.py`, and `backend/tests/architecture/test_authorization_boundaries.py`.

**Checkpoint**: Approved layer paths exist and architecture tests recognize operations as a business module.

---

## Phase 2: Foundational — JobRun Evidence and Shared Ports

**Purpose**: Provide the schema, closed vocabulary, ports, and persistence needed by reconciliation and health.

**⚠️ CRITICAL**: Complete this phase before US3 or US4. US1 and US2 may use the existing attendance foundation independently.

### Tests first

- [X] T003 [P] Add failing tests for the exact JobRun job/status/error enums, terminal classification table, zero-work success, partial-versus-total failure, and compare-and-set transition rules in `backend/tests/unit/operations/test_job_run_domain.py`.
- [X] T004 [P] Add failing ORM contract tests for every JobRun field, DB default, closed-value check, finish/error shape, timestamp ordering, and `changed_count = anomaly_count <= scanned_count` constraint in `backend/tests/unit/operations/test_job_run_model.py`.
- [X] T005 [P] Add failing port contract tests for attendance candidate/lock/mutation access, consumer-owned JobRun recording, operations attendance-health evidence, Identity-owned typed job-health access scope, server clock, and read/write unit-of-work boundaries in `backend/tests/unit/attendance/test_reconciliation_ports.py`, `backend/tests/unit/operations/test_job_health_ports.py`, and `backend/tests/unit/identity/test_authorization_gateway.py`.
- [X] T006 [P] Add failing PostgreSQL migration compatibility tests proving additive JobRun creation, DB defaults, one operations migration leaf, no historical backfill, previous-version coexistence, and no mutation of existing attendance/reference data in `backend/tests/integration/postgres/operations/test_migration_compatibility.py`.

### Foundation implementation

- [X] T007 [P] Implement canonical JobRun enums, immutable snapshots, counter deltas, and pure terminal-state classification in `backend/operations/domain/job_runs.py` until T003 passes.
- [X] T008 [P] Define typed reconciliation/job-health protocols and the Identity-owned `JobHealthAccessScope` authorization result in `backend/attendance/ports/reconciliation.py`, `backend/attendance/ports/job_runs.py`, `backend/operations/ports/job_runs.py`, `backend/operations/ports/attendance_health.py`, `backend/operations/ports/authorization.py`, `backend/operations/application/dependencies.py`, `backend/identity/ports/authorization.py`, and `backend/identity/application/authorization.py` until T005 passes without exposing `Role` to operations.
- [X] T009 Implement the JobRun ORM model with the exact fields, DB defaults, constraints, and latest-run/latest-success indexes in `backend/operations/models.py` until T004 passes.
- [X] T010 Create the expand-only JobRun migration with no data operation or heartbeat backfill in `backend/operations/migrations/0002_job_run.py` until T006 passes.
- [X] T011 Implement JobRun create, per-invocation counter update, locked compare-and-set finalization, and latest/latest-success/latest-terminal query operations in `backend/operations/adapters/persistence/job_runs.py` against the T008 ports and T009 model.
- [X] T012 Run `backend/tests/unit/operations/test_job_run_domain.py`, `backend/tests/unit/operations/test_job_run_model.py`, both port-contract suites, `backend/tests/integration/postgres/operations/test_migration_compatibility.py`, and `backend/tests/architecture/`, fixing only foundational ownership defects until all pass.

**Checkpoint**: Durable JobRun evidence can be written/read through ports, with constraints and migration compatibility proven before either use case consumes it.

---

## Phase 3: User Story 1 — Record Trustworthy Working Time (Priority: P1) 🎯 MVP

**Goal**: Preserve exact completed-session duration and expose a daily total equal to the sum of completed sessions, independent of geofence presence and boundary Location identity.

**Independent Test**: Complete two sessions on one work date, leave the first geofence between punches, Check Out at a different Location, and verify exact per-session durations plus their sum while an incomplete session contributes zero.

### Tests first

- [X] T013 [P] [US1] Add failing pure regression tests for exact server timestamp subtraction, repeating-decimal minute conversion, six-place `ROUND_HALF_UP`, negative-delta rejection, and canonical open/job-closed null duration in `backend/tests/unit/attendance/test_session_lifecycle.py`.
- [X] T014 [P] [US1] Add failing parameterized query-service tests for every completed-session count from 1 through 20, each mixed with open and job-closed incomplete rows, proving the total sums only completed durations and the displayed count is derived from `len(sessions)` rather than a stored/transported duplicate in `backend/tests/unit/attendance/test_today_query.py`.
- [X] T015 [P] [US1] Add failing API regressions for same-date sessions with different Check-In/Check-Out Locations, null incomplete duration, distinct boundary ids, exact `total_duration_minutes` serialization, and Task GPS/movement outside all attendance geofences causing no AttendanceSession mutation or auto-close in `backend/tests/integration/api/attendance/test_today.py` and `backend/tests/integration/api/attendance/test_multiple_sessions.py`.
- [X] T016 [P] [US1] Add failing PostgreSQL behavior tests proving multiple same-date sessions are permitted, incomplete/job-closed rows are excluded from `SUM`, and no `(user, work_date, kind)` uniqueness reappears in `backend/tests/integration/postgres/attendance/test_multiple_sessions.py`.
- [X] T017 [P] [US1] Add failing frontend tests for rendering every session, deriving the displayed count from the session array, separate boundary Locations, six-place daily total, a distinct missing-Checkout state without estimating time, and absence of continuous/background location polling while a session stays open in `frontend/tests/unit/attendance/attendance-panel.test.tsx` and `frontend/tests/unit/attendance/attendance-location-lifecycle.test.tsx`.

### Implementation

- [X] T018 [US1] Make the existing session lifecycle and ORM repository satisfy exact duration, canonical state shape, multiple-session pairing, different boundary Locations, and completed-only aggregation in `backend/attendance/domain/sessions.py` and `backend/attendance/adapters/persistence/repositories.py` until T013, T014, and T016 pass.
- [X] T019 [US1] Make the today query DTO and serializer expose ordered individual sessions, session count through the collection, null incomplete duration, and exact daily total without first-to-last calculation in `backend/attendance/application/queries.py`, `backend/attendance/application/dto.py`, and `backend/attendance/adapters/api/serializers.py` until T015 passes.
- [X] T020 [US1] Update the attendance timeline/panel to render completed and incomplete sessions without continuous-presence assumptions or invented checkout time in `frontend/src/features/attendance/ui/TodayTimeline.tsx` and `frontend/src/features/attendance/ui/AttendancePanel.tsx` until T017 passes.

**Checkpoint**: US1 independently proves the feature's duration, multiple-session sum, distinct Location boundaries, and incomplete-session exclusion DoD items.

---

## Phase 4: User Story 2 — Reconcile Day-Level Attendance Anomalies (Priority: P1)

**Goal**: Only the first IN determines lateness and only the current final OUT determines early/late departure, with atomic replacement when a later OUT becomes final.

**Independent Test**: Record multiple alternating punches around every strict grace boundary and prove only the first IN/current final OUT carry anomalies; adding a normal final OUT removes the earlier departure anomaly.

### Tests first

- [X] T021 [P] [US2] Add failing pure boundary tests for first-IN lateness, later-IN exclusion, exact late-grace equality, final-OUT early/late strict inequalities, exact departure-boundary equality, and mutual exclusion in `backend/tests/unit/attendance/test_anomaly_reconciliation.py`.
- [X] T022 [P] [US2] Add failing multi-session API tests proving a later accepted OUT removes the previous final-OUT anomaly, evaluates the new OUT, preserves first-IN anomaly state, and creates no anomaly on middle punches in `backend/tests/integration/api/attendance/test_multiple_sessions.py`.
- [X] T023 [P] [US2] Add a failing PostgreSQL rollback test that injects failure after removing the prior final-OUT anomaly and proves the new OUT, session close, anomaly deletion/replacement, AuditLog, and related punch transaction all roll back together in `backend/tests/integration/postgres/attendance/test_anomaly_atomicity.py`.
- [X] T024 [P] [US2] Extend the closed-domain regression to assert exactly four anomaly reasons, absence of `MISSING_CHECK_IN`/`OFF_ASSIGNMENT`, and uniqueness of one reason per Attendance in `backend/tests/unit/attendance/test_domain_contract.py` and `backend/tests/unit/attendance/test_model_contract.py`.

### Implementation

- [X] T025 [US2] Refine first-IN/latest-OUT selection and strict grace-boundary evaluation using server timestamps and Config timezone/thresholds in `backend/attendance/application/anomalies.py` until T021 passes.
- [X] T026 [US2] Make departure-anomaly replacement group-scoped and execute it with the accepted OUT/session/AuditLog transaction in `backend/attendance/ports/repositories.py`, `backend/attendance/adapters/persistence/repositories.py`, and `backend/attendance/application/commands.py` until T022–T023 pass without deleting unrelated `MISSING_CHECK_OUT` evidence.
- [X] T027 [US2] Run `backend/tests/unit/attendance/test_anomaly_reconciliation.py`, `backend/tests/unit/attendance/test_domain_contract.py`, `backend/tests/unit/attendance/test_model_contract.py`, `backend/tests/integration/api/attendance/test_multiple_sessions.py`, and `backend/tests/integration/postgres/attendance/test_anomaly_atomicity.py`, resolving only US2 defects until all first-IN/final-OUT success and boundary cases pass.

**Checkpoint**: US2 independently proves first-IN lateness, last-OUT early/late, exact-boundary behavior, and transactional replacement of the previous final-OUT anomaly.

---

## Phase 5: User Story 3 — Close Stale Sessions Without Inventing Time (Priority: P1)

**Goal**: Run idempotent reconciliation every calendar day, atomically closing each stale canonical-open session with exactly one `MISSING_CHECK_OUT` while retaining null checkout/duration and durable JobRun progress.

**Independent Test**: Reconcile weekday, Sunday, and Holiday sessions repeatedly; inject one per-session failure and retry; race two jobs and a Check Out; verify exactly-once transitions, partial progress, honest counts, and no fabricated time/audit/event.

### Tests first

- [X] T028 [P] [US3] Add failing pure tests for Asia/Ho_Chi_Minh eligibility, current-date exclusion, canonical open predicate, deterministic candidate ordering, zero-work success, per-session-error classification, invocation abort, and absence of weekday/Holiday inputs in `backend/tests/unit/attendance/test_reconciliation.py`.
- [X] T029 [P] [US3] Add failing application-service tests for RUNNING-before-scan, one unit of work per candidate, lock/revalidation no-op counting, post-lock failure scan recovery, continue-after-error, retry-only-remaining behavior, terminal status/error selection, and finalization failure leaving RUNNING in `backend/tests/unit/attendance/test_reconciliation_service.py`.
- [X] T030 [P] [US3] Add failing management-command tests for server-owned invocation time, zero-work exit zero, PARTIAL_FAILED/FAILED nonzero exit, safe output without ids/raw exceptions/GPS, and no command date/repair arguments in `backend/tests/integration/api/test_management_command_discovery.py` and `backend/tests/unit/attendance/test_reconciliation_command.py`.
- [X] T031 [P] [US3] Add failing PostgreSQL catalog tests for `attendance_reconcile_idx` on `(work_date, id)` with exactly `check_out_id IS NULL AND closed_by_job = FALSE`, while retaining the existing partial unique predicate, in `backend/tests/integration/postgres/attendance/test_reconciliation_index.py`.
- [X] T032 [P] [US3] Add failing PostgreSQL success/idempotence tests covering stale weekday, Sunday, configured Holiday, current-date exclusion, at least three repeated zero-work runs over unchanged data, next-day Check In, null checkout/duration, no invented Attendance, and no AuditLog/OutboxEvent/AttendanceAttempt in `backend/tests/integration/postgres/attendance/test_daily_reconciliation.py`.
- [X] T033 [P] [US3] Add failing PostgreSQL per-session rollback/retry tests that separately force anomaly insertion and the JobRun changed/anomaly counter writer to fail after session/anomaly writes; prove the affected flag, anomaly, and main-transaction deltas roll back together, the recovery transaction records only `scanned_count + 1`, prior/later valid sessions commit, and a later run closes only remaining eligible sessions in `backend/tests/integration/postgres/attendance/test_reconciliation_partial_failure.py`.
- [X] T034 [P] [US3] Add a failing two-connection barrier test repeated at least three times for concurrent reconciliation invocations where one changes the session and the loser records only an allowed scanned no-op, with one missing anomaly and valid independent JobRun counts in `backend/tests/integration/postgres/attendance/test_reconciliation_concurrency.py`.
- [X] T035 [P] [US3] Add a failing two-connection barrier test repeated at least three times for Check Out versus reconciliation where exactly one transition wins and the loser observes `NO_OPEN_SESSION` or an ineligible completed row without duplicate/fabricated evidence in `backend/tests/integration/postgres/attendance/test_checkout_reconciliation_race.py`.
- [X] T036 [P] [US3] Add failing PostgreSQL JobRun lifecycle tests proving RUNNING commits before scan, committed counters survive process interruption, terminal compare-and-set is single-use, failure codes contain no raw error, and DB constraints reject every invalid status/count/error shape in `backend/tests/integration/postgres/operations/test_job_run_lifecycle.py`.
- [X] T037 [P] [US3] Add failing bidirectional invariant fixtures for job-closed-without-missing-anomaly and missing-anomaly-without-job-closed, plus the valid one-to-one case, in `backend/tests/integration/postgres/attendance/test_missing_checkout_invariant.py`.

### Implementation

- [X] T038 [P] [US3] Implement pure reconciliation eligibility and invocation outcome selection without Config/Holiday/Location dependencies in `backend/attendance/domain/reconciliation.py` until T028 passes.
- [X] T039 [US3] Implement candidate-id enumeration, per-id `SELECT FOR UPDATE` by primary key, full predicate/date revalidation, atomic job-close plus unique missing anomaly, no-op detection, and aggregate invariant reads in `backend/attendance/adapters/persistence/reconciliation.py` until T031–T037 persistence assertions pass.
- [X] T040 [US3] Implement the per-invocation orchestration, separate transaction per session, post-rollback scanned evidence, continue/abort policy, and terminal JobRun finalization in `backend/attendance/application/reconciliation.py` using the T008 ports and existing server clock until T029 and T033 pass.
- [X] T041 [US3] Declare `attendance_reconcile_idx` in `AttendanceSession.Meta.indexes` and create its additive exact-predicate migration without state rewrite or constraint replacement in `backend/attendance/models.py` and `backend/attendance/migrations/0002_reconciliation_index.py` until T031 and `makemigrations --check` pass.
- [X] T042 [US3] Bind the attendance reconciliation repository, operations JobRun recorder, shared Django unit of work, and service in the exempt composition root without cross-module production imports elsewhere in `backend/config/operations_adapters.py` and `backend/config/composition.py`.
- [X] T043 [US3] Implement the thin `reconcile_missing_checkouts` management adapter with success/failure exit semantics and sanitized summary output in `backend/attendance/management/commands/reconcile_missing_checkouts.py` until T030 passes.
- [X] T044 [US3] Run `backend/tests/unit/attendance/`, `backend/tests/integration/postgres/attendance/`, `backend/tests/integration/postgres/operations/test_job_run_lifecycle.py`, `backend/tests/integration/api/test_management_command_discovery.py`, and `backend/tests/architecture/`, resolving only reconciliation-owned defects until the US3 independent test passes repeatedly.

**Checkpoint**: US3 proves all reconciliation DoD items, including every-calendar-day behavior, idempotence, per-session atomicity, concurrency, missing anomaly creation, null incomplete time, and JobRun persistence.

---

## Phase 6: User Story 4 — Monitor Reconciliation Health (Priority: P2)

**Goal**: MANAGER and LEADER can read a coherent, private, Identity-access-scope-shaped `ok`/`alert`/`unknown` health projection; HELPDESK and unauthorized object detail remain denied.

**Independent Test**: Read health across never-run, timely success, late/missing success, current/stale RUNNING, partial/failed, overdue, count mismatch, and persisted invariant fixtures for all three roles, then verify frontend refresh and role-specific guidance.

### Tests first

- [X] T045 [P] [US4] Add failing pure health truth-table tests proving success exactly at cutoff is late, current-day RUNNING is allowed only before cutoff, prior-local-day RUNNING alerts before cutoff, every unfinished RUNNING alerts at/after cutoff, never-run unknown, timely/late success, latest terminal partial/failed, overdue-only-before-cutoff, both mismatch classes, and `alert > unknown > ok` precedence in `backend/tests/unit/operations/test_job_health.py`.
- [X] T046 [P] [US4] Add failing authorization tests proving `operations.job_health.view` is a direct read grant for MANAGER/LEADER only, HELPDESK is denied before scope issuance, MANAGER maps to `INVESTIGATE`, LEADER maps to `ESCALATE_ONLY`, no implication exists, and the five-entry implication map is unchanged in `backend/tests/unit/identity/test_authorization.py`, `backend/tests/unit/identity/test_authorization_gateway.py`, and `backend/tests/integration/api/identity/test_authorization_matrix.py`.
- [X] T047 [P] [US4] Add failing API contract tests for the exact GET-only `/api/v1/operations/job-health` schema, lower-case state values, JobRun nullability/enums, reason flags, evidence counts, `changed_count` as the sole run-level “closed” count with no duplicate `closed_count`, access-scope-shaped nullable fields, and canonical errors in `backend/tests/contract/operations/test_job_health_contract.py`.
- [X] T048 [P] [US4] Add failing API authorization/order/object-scope tests for unauthenticated 401, inactive/password-change handling, HELPDESK malformed-input 403 before 400, MANAGER/LEADER 200, rejected query/body/user id, global aggregate equality, and absence of rerun/repair routes in `backend/tests/integration/api/operations/test_job_health_authorization.py`.
- [X] T049 [P] [US4] Add failing API privacy/access-scope tests for exact `Cache-Control: private, no-store`, `INVESTIGATE`-only `/api/v1/users/`, `ESCALATE_ONLY` guidance with no account/AuditLog link, and absence of users/session ids/GPS/URLs/raw exceptions/secrets plus zero AuditLog/OutboxEvent side effects in `backend/tests/integration/api/operations/test_job_health_response.py`.
- [X] T050 [P] [US4] Add a failing PostgreSQL two-connection test proving all health aggregates use one `REPEATABLE READ, READ ONLY` snapshot and cannot report a transient closed/anomaly mismatch while reconciliation commits in `backend/tests/integration/postgres/operations/test_job_health_snapshot.py`.
- [X] T051 [P] [US4] Add failing PostgreSQL query tests for latest run, latest success, latest terminal failure, any unfinished run, overdue canonical-open count, both anti-joins, and invariant/count flags in `backend/tests/integration/postgres/operations/test_job_health_queries.py`.
- [X] T052 [P] [US4] Add failing frontend API tests for generated JobHealth typing, canonical/network/unexpected failure mapping, and GET-only transport in `frontend/tests/unit/operations/job-health-api.test.ts`.
- [X] T053 [P] [US4] Add failing frontend component and route-boundary tests for loading/ready/refreshing/error states, last-good snapshot preservation, manual and 60-second visible-tab refresh, hidden-tab pause/unmount cleanup, scope-shaped link/guidance, absence of rerun controls, and the closed `/operations/job-health` → `operations.job_health.view` mapping in `frontend/tests/unit/operations/job-health-panel.test.tsx` and `frontend/tests/unit/identity/capabilities.test.tsx`.

### Implementation

- [X] T054 [P] [US4] Add `OPERATIONS_JOB_HEALTH_VIEW`, closed `JobHealthAccessScope`, and the sole MANAGER/LEADER-to-scope policy to `backend/identity/domain/authorization.py`, then expose it through `backend/identity/ports/authorization.py` and `backend/identity/application/authorization.py` without changing implications until T046 passes.
- [X] T055 [P] [US4] Implement immutable health evidence/reason DTOs, local cutoff calculation, stale-run rules, timely-success rule, invariant evaluation, and precedence as pure operations domain logic in `backend/operations/domain/job_health.py` until T045 passes.
- [X] T056 [US4] Implement one captured-time `REPEATABLE READ, READ ONLY` health unit of work, latest-run queries, attendance aggregate/anti-join bridge, and no-write projection assembly in `backend/operations/adapters/persistence/job_runs.py`, `backend/config/operations_adapters.py`, and `backend/operations/application/job_health.py` until T050–T051 pass.
- [X] T057 [US4] Implement operations authorization shaping by consuming only the typed Identity `JobHealthAccessScope`: `config` forwards the scope without role comparison, `INVESTIGATE` gets the independently authorized accounts link, and `ESCALATE_ONLY` gets fixed escalation in `backend/config/operations_adapters.py` and `backend/operations/application/job_health.py` until T002 and T048–T049 pass.
- [X] T058 [US4] Implement thin operations authentication/RBAC permission, strict no-input GET view, read-only serializers, private/no-store header, and drf-spectacular annotations in `backend/operations/adapters/api/permissions.py`, `backend/operations/adapters/api/serializers.py`, and `backend/operations/adapters/api/views.py` until T047–T049 pass.
- [X] T059 [US4] Wire the operations container and GET-only URL into the canonical namespace in `backend/operations/application/container.py`, `backend/operations/adapters/api/urls.py`, `backend/config/composition.py`, and `backend/config/urls.py`, with no rerun/repair route.
- [X] T060 [US4] Regenerate `contracts/openapi.yaml` and `frontend/src/shared/api/schema.ts`, then implement the generated-type GET wrapper in `frontend/src/features/operations/api/job-health-api.ts` until T047 and T052 pass without hand-authored duplicate response types.
- [X] T061 [US4] Extend the closed route/capability maps and implement the visibility-aware health state controller, scope-shaped panel, and capability-gated page in `frontend/src/features/identity/model/IdentityRouteBoundary.tsx`, `frontend/src/features/operations/model/job-health-state.ts`, `frontend/src/features/operations/ui/JobHealthPanel.tsx`, and `frontend/src/app/operations/job-health/page.tsx` until T053 passes.
- [X] T062 [US4] Run `backend/tests/unit/operations/`, `backend/tests/unit/identity/test_authorization.py`, `backend/tests/contract/operations/`, `backend/tests/integration/api/operations/`, `backend/tests/integration/postgres/operations/`, and `frontend/tests/unit/operations/`, resolving only health-owned defects until the US4 independent test passes for MANAGER, LEADER, and HELPDESK.

**Checkpoint**: US4 independently proves health semantics, consistent reads, authorization order, global scope, privacy, role shaping, generated API integration, and read-only frontend behavior.

---

## Phase 7: Polish and Cross-Cutting Verification

**Purpose**: Close migration, CI, deployment, static-analysis, and complete acceptance obligations across all stories.

- [X] T063 [P] Extend migration safety assertions for one leaf per affected app, expand-only operations, DB defaults, no backfill, exact index predicates, model/migration-state agreement through `makemigrations --check`, and N-1 coexistence in `backend/tests/contract/test_migration_safety.py` and `backend/tests/integration/postgres/attendance/test_migration_compatibility.py`.
- [X] T064 [P] Extend generated-contract safety/compatibility checks to reject forbidden health fields, unapproved operations mutations, and breaking response changes in `backend/tests/contract/test_openapi_safety.py`, `backend/tests/contract/test_openapi_compatibility.py`, and `scripts/check_openapi.py`.
- [X] T065 [P] Extend architecture/maintainability enforcement and CI type-check scope to all attendance and operations files in `scripts/check_all.sh`, `.github/workflows/quality.yml`, and `backend/tests/architecture/test_maintainability.py`.
- [X] T066 [P] Create the non-secret daily scheduler contract and executable readiness validation: declare one `missing-check-out-reconciliation` job with `working_directory: backend`, arguments `python manage.py reconcile_missing_checkouts`, `15 0 * * *`, `Asia/Ho_Chi_Minh`, `calendar: every_day`, `singleton_per_environment: true`, and exactly one enabled staging/production `scheduler_identity` binding in `deploy/scheduled-jobs.yaml` and `deploy/environments.yaml`; validate missing/duplicate/disabled/unresolved/drifted bindings with stable safe findings in `scripts/deployment_check.py` and `backend/tests/contract/test_deployment_runbook.py`; document migration-first rollout, strict `< 01:00` cutoff, failure exit, unknown-first-run, rollback, and monitoring in `docs/TRIEN_KHAI.md`.
- [ ] T067 [MANUAL] Execute every automated and manual scenario in `specs/005-attendance-reconciliation/quickstart.md` against local PostgreSQL, including at least three repeated/overlapping trials, and record only sanitized pass/fail evidence in `specs/005-attendance-reconciliation/evidence/acceptance.md`.
- [ ] T068 [MANUAL] [DEFERRED] Conduct pre-release job-health usability acceptance with at least 10 representative authorized MANAGER/LEADER users; require every participant to identify the state and one active reason when present in under 30 seconds, or correctly identify that an `ok` state has no alert reason, and record only aggregate role/count/timing/pass-fail evidence without usernames or GPS in `specs/005-attendance-reconciliation/evidence/job-health-usability.md`.
- [X] T069 Run `scripts/check_all.sh`, `uv run --project backend python scripts/generate_openapi.py --check`, `uv run --project backend python scripts/check_openapi.py --all`, `npm --prefix frontend run api:check`, `scripts/check_openapi_compatibility.sh`, `uv run --project backend python scripts/migration_check.py check`, and Django `makemigrations --check`, resolving only Feature 005 defects until every command passes.

---

## Dependencies and Execution Order

### Phase dependencies

```text
Phase 1 Setup
├── Phase 2 Foundation ───────────────┬── Phase 5 US3 Reconciliation
│                                    └── Phase 6 US4 Health (also needs US3 evidence)
├── Phase 3 US1 Duration/Total
└── Phase 4 US2 Anomalies

Phase 3 + Phase 4 + Phase 5 + Phase 6
└── Phase 7 Cross-Cutting Verification
```

- **Phase 1** starts immediately.
- **Phase 2** depends on Phase 1 and blocks US3/US4.
- **US1** and **US2** depend on Phase 1 and the existing Feature 004 attendance foundation; they do not require the new JobRun foundation.
- **US3** depends on Phase 2.
- **US4** depends on Phase 2 and the US3 attendance evidence/reconciliation adapters; its pure domain and authorization test tasks may be prepared earlier, but the story checkpoint requires US3.
- **Phase 7** depends on every story selected for delivery.

### Within each story

- Write the listed tests first and confirm they fail for the intended missing behavior.
- Implement pure domain behavior before persistence/application orchestration.
- Implement persistence constraints/transactions before API or command adapters.
- Generate OpenAPI before consuming the generated frontend schema.
- Reach the story checkpoint before claiming that story complete.

### Parallel opportunities

- T003–T006 can run together after Phase 1; T007 and T008 can then run together.
- US1 test tasks T013–T017 are independent and can run together.
- US2 test tasks T021–T024 are independent and can run together.
- US3 test tasks T028–T037 can be distributed by unit/command/PostgreSQL file; T038 can proceed independently of persistence implementation after its test exists.
- US4 test tasks T045–T053 can be distributed across domain, authorization, API, PostgreSQL, and frontend; T054 and T055 can run together.
- T063–T066 are independent cross-cutting tracks after story completion; T067–T069 execute sequentially after those artifacts exist.

---

## Parallel Execution Examples

### User Story 1

```text
T013: session lifecycle duration/null-state unit tests
T014: daily total query tests
T015: today/multiple-session API tests
T016: PostgreSQL aggregation/schema tests
T017: attendance frontend rendering tests
```

### User Story 2

```text
T021: anomaly boundary unit tests
T022: multi-session anomaly API tests
T023: PostgreSQL anomaly rollback test
T024: closed enum/model tests
```

### User Story 3

```text
T028–T030: domain, service, and command tests
T031–T037: separate PostgreSQL index, success, failure, race, lifecycle, and invariant tests
```

### User Story 4

```text
T045–T046: health and authorization unit tests
T047–T049: contract and API boundary/privacy tests
T050–T051: PostgreSQL snapshot and query tests
T052–T053: frontend API and panel tests
```

---

## Implementation Strategy

### MVP first

1. Complete Phase 1.
2. Complete US1 (T013–T020) using the existing Feature 004 attendance foundation.
3. Stop and validate exact durations, multiple-session total, distinct boundary Locations, and incomplete-session exclusion.

US1 is the smallest independently demonstrable payroll-value increment. Production readiness for the full Feature 005 scope still requires Foundation, US2, US3, US4, and Phase 7.

### Incremental delivery

1. Setup → structure/import guards ready.
2. US1 → trustworthy worked-time read model.
3. US2 → trustworthy day-level anomaly evidence.
4. Foundation + US3 → safe daily reconciliation and durable JobRun evidence.
5. US4 → authorized operational health visibility.
6. Phase 7 → migration, contract, deployment, and full CI acceptance.

### Execution discipline

- `[P]` never means shared-file edits should be merged concurrently without coordination.
- Do not add Celery, brokers, WebSocket/SSE, distributed locks, audit/outbox events, rerun APIs, fabricated checkout values, or historical JobRun backfill.
- Preserve unrelated working-tree changes and commit by task or coherent dependency group.
