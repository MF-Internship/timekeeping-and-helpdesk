# Implementation Plan: Attendance Sessions, Anomalies and Daily Reconciliation

**Branch**: `005-attendance-reconciliation` | **Date**: 2026-08-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-attendance-reconciliation/spec.md`

## Summary

Complete the already-established attendance session and day-anomaly behavior, then add a retry-safe daily `MISSING_CHECK_OUT` reconciliation use case and an authorized operational health view. `attendance` continues to own session/anomaly transitions; `operations` owns the new `JobRun` evidence and derived health model; cross-module access is injected through ports in `config/`. Each eligible session is locked and revalidated in its own PostgreSQL transaction, while a durable `RUNNING` JobRun is created before scanning and finalized from committed counts. A thin Django management command is the scheduler entry point, so no new queue, worker, library, or infrastructure is introduced.

## Technical Context

**Language/Version**: Python `>=3.12,<3.14`; TypeScript 5.9.2; Node.js `>=22`

**Primary Dependencies**: Django 5.2.5, Django REST Framework 3.16.1, drf-spectacular 0.28; Next.js 16.3.1, React 19.1.1, openapi-fetch 0.14

**Storage**: PostgreSQL 17 in CI; existing ORM tables plus additive `operations_jobrun` and one partial attendance reconciliation index

**Testing**: pytest/pytest-django against real PostgreSQL for constraints, transactions, and races; Vitest/Testing Library for frontend; generated OpenAPI and TypeScript contract checks

**Target Platform**: Linux web deployment with the existing Django/Next.js runtime and an existing deployment scheduler bound from `deploy/scheduled-jobs.yaml` to invoke the command at 00:15 Asia/Ho_Chi_Minh every calendar day

**Project Type**: Web application with Django REST API and Next.js frontend

**Performance Goals**: Finish the daily run before the 01:00 Asia/Ho_Chi_Minh cutoff; health GET remains an aggregate indexed read suitable for the approved 60-second active-tab refresh pattern

**Constraints**: About 50 internal users; no overnight MVP sessions; no continuous GPS; no fabricated checkout/duration; one transaction per session; repeated/concurrent runs safe; private/no-store health response; no AuditLog/OutboxEvent for auto-close or health reads; no new dependencies or infrastructure

**Scale/Scope**: At most one canonical open session per user, therefore normally no more than about 50 eligible rows per day; existing 76 Location source rows and Holiday/working-weekday data are explicitly not reconciliation inputs

## Constitution Check

*GATE: Passed before Phase 0 and re-checked after Phase 1.*

| Principle | Plan evidence | Result |
|---|---|---|
| I. Source-of-Truth Governance | R-127–R-134 are synchronized through CHOT, QUY_TAC, PRD, RA_SOAT, and the current spec; no unresolved conflict remains. | PASS |
| II. Fixed Stack and Inward Architecture | Existing stack is reused. Attendance and operations expose domain/application/ports/adapters; only `config/` composes cross-module implementations. | PASS |
| III. Authorization Is Layered and Ordered | `operations.job_health.view` is a direct centralized action; DRF permission runs before request-shape validation; the read is explicitly global with no user object scope. | PASS |
| IV. Server Authority and Boundary Validation | Server clock owns work date, run timestamps, cutoff, counts, state, and refresh time. Health GET accepts no body, filters, user id, or client-owned state. | PASS |
| V. Database Invariants and Transactions | PostgreSQL row locks, partial index, anomaly uniqueness, JobRun checks, and per-session units of work protect the required races and count relations. | PASS |
| VI. Auditability and Safe Observability | JobRun/session/anomaly are canonical evidence; safe closed error codes replace raw exceptions; no AuditLog/outbox is created; health remains `unknown` without evidence. | PASS |
| VII. Stable Generated Contracts | DRF serializers and drf-spectacular generate `contracts/openapi.yaml`; the TypeScript schema is regenerated and compatibility/drift checks remain authoritative. | PASS |
| VIII. Safe Schema Evolution | Additive migrations, DB defaults for counters/status, no backfill or contraction, single migration leaf, migration-first rolling deployment. | PASS |
| IX. Security and Environment Isolation | No new secret or network dependency; aggregate response excludes GPS, user lists, raw exceptions, credentials, and unauthorized links. | PASS |
| X. Location/GPS Integrity | Reconciliation never reads Location, Config weekday, Holiday, or device position; existing distinct Check-In/Check-Out Location behavior remains unchanged. | PASS |
| XI. Testing at Correct Layer | Pure evaluators get unit tests; API/authorization/contracts get boundary tests; locks, rollback, constraints, and races use real PostgreSQL connections. | PASS |
| XII. Maintainable Code and Naming | Canonical enums/names are reused; thin views/command; cohesive DTOs and ports; existing Ruff/mypy/ESLint/AST limits remain gates. | PASS |

## Project Structure

### Documentation (this feature)

```text
specs/005-attendance-reconciliation/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── job-health-api.yaml
└── tasks.md                         # generated later by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── attendance/
│   ├── domain/{sessions.py,reconciliation.py}
│   ├── application/{anomalies.py,reconciliation.py}
│   ├── ports/{reconciliation.py,job_runs.py}
│   ├── adapters/persistence/reconciliation.py
│   ├── management/commands/reconcile_missing_checkouts.py
│   ├── migrations/0002_reconciliation_index.py
│   └── models.py
├── operations/
│   ├── domain/{job_runs.py,job_health.py}
│   ├── application/{dependencies.py,container.py,job_health.py}
│   ├── ports/{authorization.py,attendance_health.py,job_runs.py}
│   ├── adapters/api/{permissions.py,serializers.py,urls.py,views.py}
│   ├── adapters/persistence/job_runs.py
│   ├── migrations/0002_job_run.py
│   └── models.py
├── identity/
│   ├── domain/authorization.py
│   ├── application/authorization.py
│   └── ports/authorization.py
├── config/{composition.py,operations_adapters.py,urls.py}
└── tests/
    ├── unit/{attendance,operations,identity}/
    ├── integration/api/operations/
    ├── integration/postgres/{attendance,operations}/
    ├── contract/operations/
    └── architecture/

frontend/
├── src/app/operations/job-health/page.tsx
├── src/features/identity/model/IdentityRouteBoundary.tsx
├── src/features/operations/
│   ├── api/job-health-api.ts
│   ├── model/job-health-state.ts
│   └── ui/JobHealthPanel.tsx
└── src/shared/api/schema.ts         # generated, never hand-edited

deploy/scheduled-jobs.yaml           # non-secret scheduler contract
scripts/deployment_check.py          # validates manifest/environment binding
```

**Structure Decision**: Extend the existing web application and its approved inward module pattern. Attendance owns the write use case because it owns sessions and anomalies. Operations owns durable run evidence and the read model. The composition root is the only production location allowed to bind operations-owned persistence to the attendance-owned `JobRun` port and attendance aggregates to the operations-owned health port.

## Phase 0 Research Decisions

The complete Decision/Rationale/Alternatives record is in [research.md](research.md). The implementation-driving results are:

1. Use the existing Django management-command deployment surface; `deploy/scheduled-jobs.yaml` binds the external scheduler to `15 0 * * *` in Asia/Ho_Chi_Minh with exactly one enabled identity per staging/production environment. No Celery dependency is added.
2. Create and commit one `RUNNING` JobRun before scanning. Candidate ids are enumerated deterministically, then every id is locked and revalidated in a separate transaction.
3. Commit the session transition, its one anomaly, and that run's scanned/changed/anomaly counter increments together. If processing fails after lock, roll back the business pair and record only the observed scan in a separate short transaction before continuing.
4. Use the existing PostgreSQL open predicate and add a matching partial `(work_date, id)` index. Checkout and competing jobs serialize on the same session row.
5. Store JobRun in `operations`; connect it through consumer-owned ports in `config/`. Do not introduce a parallel heartbeat model.
6. Derive health at read time with an explicit reason-flag object. Identity authorization maps role to the closed `INVESTIGATE|ESCALATE_ONLY` scope; operations shapes links/guidance from that scope without importing role. Only the existing independently authorized user-list endpoint may be linked for `INVESTIGATE`.

## Phase 1 Design

### Module and domain responsibilities

- `attendance.domain.sessions` remains the single definition of an open session and exact six-decimal duration. The already-implemented daily total query continues to sum completed non-job-closed sessions only.
- `attendance.application.anomalies` remains the one punch-time anomaly reconciler. It evaluates only the earliest IN/latest OUT and replaces earlier final-OUT anomalies inside the accepted punch transaction.
- `attendance.application.reconciliation` captures one server `started_at`, derives the Asia/Ho_Chi_Minh current date, creates the run, scans eligible ids, and delegates each atomic transition. It never reads Holiday, Location, `working_weekdays`, or shift Config.
- `operations.domain.job_runs` owns canonical job/status/error values and terminal classification. `operations.domain.job_health` is a pure evaluator over typed run and attendance evidence.
- `identity.application.authorization` authorizes the actor and returns a typed `JobHealthAccessScope`; `operations.application.job_health` consumes that scope, reads one consistent aggregate snapshot in a short PostgreSQL `REPEATABLE READ, READ ONLY` unit of work, applies scope shaping, and returns a DTO. The serializer only formats it.

### Reconciliation execution and transaction semantics

1. The management command resolves the configured reconciliation service and invokes it with no client-supplied date or timestamp.
2. In a short transaction, insert `JobRun(job_name=MISSING_CHECK_OUT, status=RUNNING, started_at=server_now, counts=0)` and commit before candidate enumeration.
3. Enumerate candidate session ids ordered by `(work_date, id)` using the canonical predicate and `work_date < local_current_date`. The list is a hint, not authorization to mutate.
4. For each id, open a new unit of work, lock the session with `SELECT FOR UPDATE`, and revalidate the full predicate and date.
5. Increment `scanned_count` for the invocation. If still eligible, set only `closed_by_job=True`, create the unique `MISSING_CHECK_OUT` on `check_in_id`, and increment `changed_count` and `anomaly_count`. Commit all of these together. Check Out and other reconciliation invocations use the same row lock, so only one transition wins.
6. If a session fails after its row was locked, its transaction rolls back. A separate short transaction increments only `scanned_count`, the service records a safe per-session failure flag in memory, and processing continues. If even this evidence update or candidate enumeration cannot continue, classify the invocation as aborted.
7. In a final short transaction, lock the run and transition it once from `RUNNING` to `SUCCEEDED`, `PARTIAL_FAILED`, or `FAILED`, set server `finished_at`, and assign only the approved safe error code. If the process dies or finalization cannot commit, the row deliberately remains `RUNNING` with the counts already committed.
8. A later invocation scans only rows that still satisfy the open predicate. Zero eligible rows is `SUCCEEDED(0,0,0)`.

No whole-run or batch business transaction, `skip_locked`, advisory/distributed lock, invented checkout Attendance, AuditLog, OutboxEvent, or automatic retry loop is introduced.

### Persistence constraints and indexes

- Retain `uniq_open_session_per_user`, `attendance_session_shape`, `attendance_duration_nonnegative`, `attendance_anomaly_unique`, and the four-reason check unchanged.
- Add `attendance_reconcile_idx` on `AttendanceSession(work_date, id)` with condition `check_out_id IS NULL AND closed_by_job = FALSE`; this exactly supports eligibility and remains compatible with the canonical open predicate.
- Declare `attendance_reconcile_idx` in `AttendanceSession.Meta.indexes` and generate the matching migration so model state and migration state cannot drift; `makemigrations --check` must remain clean.
- Add the JobRun checks specified in [data-model.md](data-model.md): closed enum values, status/finish/error shape, nonnegative counts, and `changed_count = anomaly_count <= scanned_count`.
- Add `(job_name, started_at, id)` for latest run and `(job_name, status, finished_at, id)` for latest successful/terminal reads. No uniqueness rule suppresses overlapping invocations because overlap is explicitly supported.
- Use `PROTECT` for existing attendance evidence relations; no hard-delete path is added.

### Health read model

- Capture `refreshed_at` once, then read all JobRun and attendance evidence inside one short PostgreSQL `REPEATABLE READ, READ ONLY` transaction. This prevents a per-session commit between aggregate queries from producing a false closed/anomaly mismatch; the health read takes no row locks and performs no writes.
- Read the latest run, latest successful run, aggregate job-closed count, aggregate `MISSING_CHECK_OUT` count, both anti-join mismatch counts, and overdue canonical-open count.
- The local cutoff is today's `01:00:00+07:00`. A success is timely for today only when its local finish date is today and `finished_at < cutoff`; equality is late and is evaluated by the at/after-cutoff branch.
- Before cutoff, overdue rows remain visible but do not alone alert; a current invocation may be `RUNNING`. A terminal failure, a `RUNNING` row started before the current local day, a count mismatch, or a persisted relationship violation alerts immediately.
- At or after cutoff, missing timely current-day success, any unfinished run, overdue rows, or the immediate-alert conditions produces `alert`. With no run evidence and no alert condition, state is `unknown`; otherwise healthy evidence is `ok`. Precedence is `alert > unknown > ok`.
- Return booleans for each reason rather than raw exceptions. `latest_run` and `latest_successful_run` retain their own safe counts/status/error code.

### API, DTO, authorization, and object scope

- Add `GET /api/v1/operations/job-health`; accept no query parameters or request body. Preserve the canonical 401/403/400 error envelope.
- Add `PermissionAction.OPERATIONS_JOB_HEALTH_VIEW = "operations.job_health.view"`, place it directly in MANAGER and LEADER grants, exclude HELPDESK, add it to the read-only action set, and leave the five-entry implication map unchanged.
- The DRF permission performs authentication and RBAC before request-shape validation. The application boundary repeats the gate through Identity; only `identity.domain.authorization` maps MANAGER to `JobHealthAccessScope.INVESTIGATE` and LEADER to `ESCALATE_ONLY`. Identity returns the typed scope through its authorization port, and `config/operations_adapters.py` forwards it without reading or comparing role.
- This is a global aggregate, so no `user_id` is accepted and no per-user object-scope filter exists. `INVESTIGATE` may receive `investigation_links.accounts = "/api/v1/users/"`, whose target independently checks `user.view`; no AuditLog link is emitted because no approved AuditLog read endpoint currently exists. `ESCALATE_ONLY` gets no links and receives a fixed escalation instruction.
- Use explicit read-only serializers for JobRun, reason flags, links, and the health response. Generate the canonical OpenAPI and frontend schema; do not hand-map snake/camel case.
- Add `Cache-Control: private, no-store` and existing private response protections. Exclude coordinates, users, raw exception text, secrets, object keys, and presigned/map URLs.

### Frontend state and API integration

- Extend the closed route/capability maps in `frontend/src/features/identity/model/IdentityRouteBoundary.tsx`, then add a capability-gated `/operations/job-health` page using `operations.job_health.view`; route visibility is presentation-only and backend enforcement remains authoritative.
- The API wrapper uses the generated `JobHealth` schema and shared `apiClient.GET`/canonical error parser.
- Model `loading`, `ready`, `refreshing`, `canonical_error`, `network_error`, and `unexpected_response`. Preserve the last successful snapshot while a manual or 60-second active-tab refresh is in flight; stop polling while hidden and clean up on unmount.
- Render state, cutoff/timezone, latest/latest-successful runs, three run counters, overdue count, invariant status, reason flags, and `refreshed_at`. Render the account link only when the server's `INVESTIGATE` projection includes it; render `ESCALATE_ONLY` guidance without constructing hidden links client-side.
- Provide refresh control only. Do not add rerun/repair controls, user lists, GPS detail, or AuditLog UI.

### Error, failure, audit, and event semantics

- Per-session unexpected failures never become attendance business error codes. They are reduced to `SESSION_PROCESSING_FAILED` on the run; invocation-level failures use `RUN_ABORTED`. Raw messages are sanitized operational telemetry only and never persisted in JobRun or exposed by the API.
- The management command exits nonzero for `PARTIAL_FAILED`/`FAILED` so the deployment scheduler can alert, while committed progress and the terminal JobRun remain intact. `SUCCEEDED`, including zero work, exits zero.
- Auto-close and health reads create no `AttendanceAttempt`, AuditLog, OutboxEvent, user actor, or per-session external message. This is an explicit governed exception because the three canonical tables are sufficient evidence.

### Deployment scheduler contract

- `deploy/scheduled-jobs.yaml` contains one `missing-check-out-reconciliation` entry with `working_directory: backend`, command arguments `python manage.py reconcile_missing_checkouts`, cron `15 0 * * *`, timezone `Asia/Ho_Chi_Minh`, `calendar: every_day`, and `singleton_per_environment: true`.
- Its bindings contain exactly `staging` and `production`, both enabled. `deploy/environments.yaml` adds one non-secret `scheduler_identity` inventory value per environment; the manifest refers to those inventory keys rather than embedding credentials or provider URLs.
- `scripts/deployment_check.py` accepts both documents and reports stable safe finding codes for missing/duplicate job ids, command/cron/timezone/calendar drift, disabled/missing staging or production binding, unresolved production scheduler identity, or multiple bindings in one environment.
- The contract configures an existing external scheduler only. The management command remains safe when invoked manually, late, repeatedly, or concurrently; singleton is a deployment ownership requirement, not a business correctness lock.

## Migration Strategy

1. Add `operations.JobRun` in `operations/migrations/0002_job_run.py` with all fields, DB defaults, checks, and indexes. Create no historical rows and no second heartbeat table.
2. Add the conditional attendance reconciliation index in `attendance/migrations/0002_reconciliation_index.py`. Do not rewrite session/anomaly rows or change the existing partial unique constraint.
3. Both migrations are expand-only and safe for the immediately previous application: old code ignores the new table/index; new code is enabled only after migrations apply. Migration DDL precedes application/frontend rollout.
4. Prove one leaf per app, old-version startup after migration, new-version clear failure before migration, PostgreSQL catalog shapes, and no changes to identity, audit, Config, Holiday, Location, or source CSV rows.
5. Add the non-secret `deploy/scheduled-jobs.yaml` contract for the canonical command, timezone, `15 0 * * *` schedule, daily calendar semantics, and singleton binding identity. Extend `scripts/deployment_check.py` to fail readiness when a staging/production binding is missing, duplicated, disabled, or drifts from the contract. Enable the external schedule only after the application is deployed and the command is discoverable. Health is intentionally `unknown` until the first real run; do not backfill a synthetic success.

## Verification Strategy

### Unit tests

- Existing duration tests retain exact microsecond delta, `ROUND_HALF_UP`, null incomplete duration, parameterized totals for every completed-session count from 1 through 20 with open/job-closed rows excluded, different boundary Locations, and no continuous-presence behavior. Add an explicit regression proving Task GPS/movement outside the geofence creates no attendance side effect or background tracking.
- Existing anomaly tests cover first-IN only, strict equality boundaries, final-OUT early/late mutual exclusion, and atomic replacement when a later OUT becomes final.
- New attendance tests cover local-date eligibility, canonical predicate, no Config/Holiday dependency, per-session continuation, retry outcome classification, zero-work success, and safe abort classification.
- New operations tests exhaust the JobRun transition table and health truth table, including the exact cutoff equality, before/after cutoff, never-run unknown, current/prior-day RUNNING, timely/late success, partial/failed latest run, overdue-only-before-cutoff, mismatch precedence, and access-scope shaping.
- Identity tests assert the exact direct grants, HELPDESK denial before scope issuance, MANAGER/LEADER typed scope mapping, read-only classification, and unchanged five-entry implication map. Architecture tests reject role imports/comparisons for job-health outside Identity authorization.

### API and contract tests

- MANAGER/LEADER 200, HELPDESK 403, unauthenticated 401, malformed query/body authorization precedence, no user object scope, and no rerun route.
- Exact lower-case health states, JobRun enums, nullability, reason flags, `INVESTIGATE` account link, `ESCALATE_ONLY` guidance, `private, no-store`, and absence of forbidden GPS/user/raw-error/secret fields.
- Deterministic OpenAPI generation, safety scan, generated TypeScript drift, and additive compatibility comparison.
- Frontend API unwrap, capability route behavior, async/refresh states, visibility-aware polling cleanup, last-good-data preservation, role-specific guidance, and no mutation control.

### PostgreSQL integration tests

- Catalog checks for JobRun constraints/defaults/indexes and the exact attendance partial-index predicate.
- One transaction per session: force anomaly failure and prove both session/anomaly roll back while previously completed sessions remain committed; retry closes only the remaining row.
- Force the JobRun changed/anomaly counter write to fail after the session/anomaly writes inside an eligible-session unit of work; prove the session flag, anomaly, and all main-transaction deltas roll back together, then prove the separate recovery transaction records only `scanned_count + 1` and no changed/anomaly delta.
- Two reconciliation workers released on a barrier against one session: one changed/anomaly, the other scanned/no-op, no duplicates, honest per-run counts.
- Check Out versus reconciliation on two real connections: exactly one state transition wins and the loser observes canonical state.
- JobRun creation commits before scanning; forced crash leaves `RUNNING`; successful/partial/failed finalization preserves checks and committed counts.
- Weekend, Sunday, configured Holiday, current-date exclusion, no fabricated Attendance/check-out/duration, and a job-closed row permitting the next Check In.
- Anti-join fixtures detect both job-closed-without-anomaly and anomaly-without-job-closed relationships.

### CI verification

- Extend strict mypy/function-length/architecture scope to new attendance and operations files.
- Run existing `scripts/check_all.sh`, Ruff, Django checks, unit/API/contract/architecture tests, real-PostgreSQL marker suite, frontend format/lint/typecheck/Vitest/build, generated OpenAPI/client checks, compatibility check, and migration safety/leaf checks.
- Validate `deploy/scheduled-jobs.yaml` and environment bindings through the deployment-check contract suite, and keep `makemigrations --check` clean for both model/migration states.
- Do not use wall-clock timing as a flaky CI assertion. Record a pre-release run proving completion under the approved 50-user scale strictly before 01:00 local time. Separately record sanitized usability evidence for at least 10 representative MANAGER/LEADER users, all identifying the state and one active reason when present in under 30 seconds, or correctly identifying that an `ok` state has no alert reason.

## Post-Design Constitution Re-check

Phase 1 preserves every pre-design gate. The data model introduces only additive evidence and an index; the API is generated and additive; all cross-module access goes through ports composed in `config`; transaction and race guarantees are assigned to PostgreSQL tests; authorization order, global object scope, privacy, no-audit/no-outbox behavior, and migration compatibility are explicit. No exception requires a Complexity Tracking entry.

## Complexity Tracking

No constitution violation or approved deviation is required.
