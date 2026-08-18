# Implementation Plan: Attendance Check-In and Check-Out Core

**Branch**: `004-attendance-core` | **Date**: 2026-08-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-attendance-core/spec.md`

## Summary

Add a dedicated `attendance` module for HELPDESK self Check In, self Check Out,
and today's self read model. The module will preserve the repository's inward
architecture (`domain/`, `application/`, `ports/`, `adapters/`), reuse identity
authorization and Location/Config/geofence capabilities through ports, and add
PostgreSQL-backed `Attendance`, `AttendanceSession`, `AttendanceAttempt`, and the
already-governed anomaly relation needed by attendance transactions.

Each accepted punch and its session transition commit atomically. A conditional
unique constraint on the canonical open-session predicate is the final race
guard. `AttendanceAttempt` is deliberately appended only after the business
transaction exits so rejected attempts and double-tap losers survive rollback.
The frontend obtains a new foreground GPS sample per submission, handles
overlapping-location choice as a fresh resubmission, and refreshes the self read
model after acceptance.

## Technical Context

**Language/Version**: Python 3.12–3.13; TypeScript 5.9; React 19

**Primary Dependencies**: Django 5.2.5, Django REST Framework 3.16.1,
drf-spectacular 0.28.0, Next.js 16.3.1, openapi-fetch 0.14.0

**Storage**: PostgreSQL through Django ORM; no cache, queue, object-storage, or
new infrastructure requirement for this feature

**Testing**: pytest 8.4.1 + pytest-django against PostgreSQL; Vitest 3.2.7 +
Testing Library; existing OpenAPI generation and compatibility checks

**Target Platform**: Linux-hosted web service and modern mobile/desktop browsers
with the W3C Geolocation API

**Project Type**: Next.js web application backed by a Django REST JSON API

**Performance Goals**: at least 95 of 100 PostgreSQL command-plus-today-read
trials complete within 2 seconds with 50 users, 76 canonical Locations, and 20
same-day sessions for the actor; frontend tests separately prove no artificial
render delay after the read completes

**Constraints**: server UTC and Asia/Ho_Chi_Minh work dates; fresh GPS no older
than 60 seconds; active-only attendance candidates; all-76 nearest diagnostics;
no background tracking; one open session per user; no new dependencies

**Scale/Scope**: approximately 50 internal users, exactly 76 canonical Locations,
three attendance endpoints, one employee-facing page, and multiple sessions per
user/work date

## Constitution Check

*GATE: Passed before Phase 0 and re-checked after Phase 1.*

| Gate | Design response | Status |
|---|---|---|
| Source-of-truth governance | R-118 defines all-76 nearest versus active-only candidates; R-119 resolves equal-distance nearest diagnostics by canonical Location code without changing candidate ambiguity. | PASS |
| Inward architecture | New attendance code follows domain/application/ports/adapters; adapters alone import Django/DRF. | PASS |
| Cross-module ownership | Attendance consumes identity authorization and Location/Config/geofence behavior through application ports wired in `config/composition.py`; production code does not import foreign module models/adapters. | PASS |
| Authorization order | Authentication/account state and action RBAC run before strict DTO validation; self scope comes only from authenticated actor. | PASS |
| Server authority | Route owns `kind`; auth owns `user_id`; server owns UTC `recorded_at` and local `work_date`; strict serializers reject server-owned fields. | PASS |
| Database invariants | PostgreSQL partial uniqueness protects open sessions; state checks and row locks supplement rather than replace it. | PASS |
| Transaction semantics | Punch/session/anomaly and the required route-specific AuditLog share one transaction; observational attempts are appended afterward on success and expected rejection paths. | PASS |
| Safe observability | Attempts retain approved precise coordinates; AuditLog/outbox/telemetry never receive coordinates, maps URLs, device metadata, or request IP. | PASS |
| Stable contracts | DRF schema remains canonical; committed OpenAPI and TypeScript schema are regenerated, never hand-edited. | PASS |
| Safe migration | New tables are additive, fields needed by N-1 writers use database defaults where applicable, and no existing column or constraint is contracted. | PASS |
| PostgreSQL proof | Constraint, rollback, and double-tap claims receive real PostgreSQL transaction tests. | PASS |
| Dependency control | Existing stack and browser APIs are sufficient. | PASS |

## Project Structure

### Documentation (this feature)

```text
specs/004-attendance-core/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── attendance-api.yaml
└── tasks.md                    # created later by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── attendance/
│   ├── domain/
│   │   ├── attendance.py       # enums, snapshots, state/quality/candidate rules
│   │   ├── attempts.py         # closed outcome and observation records
│   │   └── sessions.py         # canonical open predicate and projections
│   ├── application/
│   │   ├── commands.py         # Check In/Out orchestration
│   │   ├── queries.py          # today self projection and punch_index
│   │   ├── anomalies.py        # governed first-IN/latest-OUT reconciliation
│   │   ├── projections.py      # shared command/today punch projections
│   │   ├── dto.py
│   │   ├── dependencies.py
│   │   └── container.py
│   ├── ports/
│   │   ├── authorization.py
│   │   ├── reference_data.py   # one locked Config + 76-Location snapshot
│   │   ├── repositories.py
│   │   ├── attempts.py
│   │   ├── clock.py
│   │   └── unit_of_work.py
│   ├── adapters/
│   │   ├── api/{views.py,serializers.py,permissions.py,urls.py,maps.py}
│   │   └── persistence/{repositories.py,attempts.py,unit_of_work.py}
│   ├── migrations/0001_initial.py
│   ├── apps.py
│   └── models.py
├── config/{attendance_adapters.py,composition.py,settings.py,urls.py}
├── core/error_codes.py
└── tests/
    ├── unit/attendance/
    ├── integration/api/attendance/
    ├── integration/postgres/attendance/
    ├── contract/attendance/
    └── architecture/

frontend/
├── src/app/attendance/page.tsx
├── src/features/attendance/
│   ├── api/attendance-api.ts
│   ├── model/{attendance-state.ts,use-foreground-position.ts}
│   └── ui/{AttendancePanel.tsx,LocationChoice.tsx,TodayTimeline.tsx}
└── tests/unit/attendance/

contracts/
└── openapi.yaml                # generated implementation artifact

scripts/
└── attendance_interaction_check.py # pre-release SC-008 harness; not CI

specs/004-attendance-core/evidence/
├── latency-acceptance.md
└── usability-acceptance.md
```

**Structure Decision**: Extend the existing web application with one cohesive
attendance Django app and one frontend feature slice. Shared geometry remains in
the established Location domain; attendance-specific gate order, thresholds,
session state, attempt semantics, and read projections remain owned by attendance.

## Implementation Design

### Module and dependency ownership

- `attendance.domain` contains closed enums and pure decisions for GPS quality,
  session transitions, candidate cardinality, and resolution method. It may use
  narrow technical primitives but imports no Django, DRF, or frontend policy.
- `attendance.application.commands.AttendanceCommandService` owns the ordered
  Check In/Out workflow and captures an attempt draft once the request crosses
  the post-validation boundary.
- `attendance.application.queries.AttendanceQueryService` derives today's local
  work date from the injected clock, loads only the authenticated user, orders
  punches by `(recorded_at, id)`, and assigns one-based `punch_index` values.
- `attendance.ports.reference_data` exposes one locked reference snapshot with
  Config and all 76 canonical Locations. Nearest reads the full snapshot and
  candidates filter active rows from that same in-memory snapshot. The
  composition root adapts Feature 003's repositories and pure geofence service;
  the attendance module never imports `locations.models`.
- The attendance authorization port exposes operation-specific Check In, Check
  Out, and self-view decisions. Composition-root bridges translate those calls to
  Identity's three already-defined permission actions, so attendance code imports
  neither Identity enums nor implementation types. No role checks are added.
- The persistence adapter owns ORM models, constraint-name translation, row
  locking, and transaction implementation. Views and serializers remain thin.

### Ordered command workflow

1. Existing authentication and account-state enforcement identify the actor.
2. Route-specific action RBAC runs (`check_in.self` or `check_out.self`).
3. A strict serializer rejects unknown/server-owned fields, validates finite
   coordinate/range values, non-negative accuracy, and optional captured-time
   freshness. Rejections through this step create no attempt.
4. The service captures one server UTC timestamp and derives the local work date
   and route-owned kind. This is the AttendanceAttempt boundary.
5. Enter the business transaction, take the approved Config-first lock, load one
   snapshot of all 76 canonical Locations, and calculate nearest by
   `(distance_m, code)`, using `code` only for exact-distance diagnostic ties.
   This observation is never a candidate selector or business gate.
6. Evaluate canonical session state before GPS quality and candidates.
7. Compare accuracy only with `max_attendance_accuracy_m`. If it passes, classify
   every active Location independently using `distance_m <= radius_m`.
8. Resolve zero/one/many candidates; recompute and validate every supplied
   `selected_location_id` against this request's active candidate set. An empty
   recomputed set returns `OUTSIDE_RADIUS` before selected-id validation; only a
   non-empty set can return `INVALID_LOCATION_CHOICE`.
9. For acceptance, atomically create the immutable Attendance, open/close the
   session, reconcile the already-approved anomaly state, and append exactly one
   sanitized AuditLog using `attendance.check_in.created` or
   `attendance.check_out.created`. Rejections create no AuditLog, and routine
   punches create no OutboxEvent.
10. Exit the transaction. Append exactly one AttendanceAttempt with the captured
    result on accepted and expected-business-rejection paths. Return the original
    business result even if observational persistence itself fails after commit,
    while emitting sanitized telemetry without GPS/request-IP data.
11. Let unexpected infrastructure exceptions retain canonical 5xx handling; do
    not append or relabel an attempt, and emit only sanitized operational telemetry.

### Transactions and concurrency

- Check In pre-checks the canonical open predicate, but the conditional unique
  constraint is authoritative. A losing `IntegrityError` identified by
  `uniq_open_session_per_user` is translated to `SESSION_ALREADY_OPEN` only after
  the aborted transaction exits; the attempt is then appended separately.
- Check Out obtains `SELECT FOR UPDATE` on the canonical open session before
  creating `OUT` and closing it. No open row produces `NO_OPEN_SESSION`.
- Config is locked before the single 76-Location snapshot is loaded, matching
  Feature 003's Config→Location write order. Nearest and active-only candidates
  are both derived from that snapshot, so a concurrent reference edit cannot
  split one request across versions without adding locks or infrastructure.
- The accepted unit of work covers Attendance, AttendanceSession, approved anomaly
  reconciliation, and the required invariant-bound punch AuditLog append. Attempt writes
  never occur inside that unit of work and never use `transaction.on_commit()`.
- There is no Attendance idempotency key. Sequential or concurrent duplicate taps
  are state transitions: a repeated Check In returns `SESSION_ALREADY_OPEN`; a
  repeated Check Out returns `NO_OPEN_SESSION`. After a lost response the client
  reads `/attendance/today` to reconcile canonical state.
- Unexpected infrastructure errors are not mislabeled with one of the seven
  business outcomes. They follow the existing canonical 5xx handling, create no
  AttendanceAttempt, and emit sanitized telemetry; no new outcome or retry queue
  is introduced.

### Persistence, constraints, and indexes

- Create additive tables described in [data-model.md](data-model.md); never add
  `UNIQUE(user_id, work_date, kind)`.
- Add `UniqueConstraint(fields=["user"], condition=Q(check_out__isnull=True,
  closed_by_job=False), name="uniq_open_session_per_user")`.
- Add closed-enum checks, accepted-attempt/attendance consistency, non-negative
  distances and counts, session shape checks, and one-to-one punch/session edges.
- Index Attendance timeline `(user, work_date, recorded_at, id)`, Session lookup
  `(user, work_date, id)`, Attempt timeline `(user, work_date, recorded_at, id)`,
  and Attempt reporting `(work_date, outcome)` plus `(nearest_location, outcome)`.
- Store `duration_minutes` at six decimal places, derived once from the exact
  timestamp delta with `ROUND_HALF_UP`; no minute-level payroll rounding occurs.
- Use deterministic `(recorded_at, id)` ordering only as a technical tie-break for
  equal server timestamps; `recorded_at` remains the governing punch order.

### API and error semantics

- Add `POST /api/v1/attendance/check-in`, `POST
  /api/v1/attendance/check-out`, and `GET /api/v1/attendance/today`.
- Both commands accept only latitude, longitude, accuracy, optional captured time,
  and optional selected Location. They never accept user, kind, recorded time, or
  work date.
- Specialized 409/422 responses retain the canonical error envelope and expose
  `location_candidates` where CHOT requires the client to choose or recover.
- Successful commands return Attendance, Location/validation/resolution,
  session projection, derived punch index, `resolved_address` projected from
  `Location.address`, and a Maps URL derived locally from accepted coordinates.
- Today returns only the actor's local date, ordered punches and sessions, total
  of user-closed session durations, and `has_open_session`; it accepts no user id.
- Extend `core/error_codes.py` only with already-approved closed codes. Generate
  `contracts/openapi.yaml`, then regenerate `frontend/src/shared/api/schema.ts`.

### Frontend state and integration

- Route access uses authenticated capabilities for presentation; the backend is
  authoritative. MANAGER/LEADER see no attendance action controls.
- Model explicit states: idle, permission-needed, acquiring, ready/weak,
  submitting, choice-required, accepted, canonical-error, and browser-GPS error.
- A user gesture starts foreground geolocation. Stop watching on hidden tab,
  unmount, cancel, timeout, or submit. Never persist a stream of fixes or send
  location in the background.
- Each Check In/Out submission obtains a sample with `maximumAge: 0`; selecting a
  candidate triggers a new sample and resubmission rather than reusing the first
  ambiguous payload. The backend's recomputed candidates always win.
- Disable the action while one request is in flight, but do not treat this UI
  control as concurrency protection. On success or an ambiguous lost response,
  refresh today's read model and render its canonical next action.
- Render weak GPS guidance, outside-radius feedback, current candidate choices,
  separate Check In/Out Locations, a unified punch timeline, and total closed
  duration. Render authorized Maps links from each punch's captured coordinates
  with `target="_blank"` and `rel="noopener noreferrer"`; never embed an iframe or
  map SDK. Do not expose nearest diagnostic metadata in the employee action UI.

### Audit, privacy, and events

- AttendanceAttempt is the approved attendance request history, not AuditLog and
  not access logging. It stores precise request evidence only in its protected
  table and is never emitted to generic logs or outbox payloads.
- Successful self Check In/Out appends the newly governed AuditAction
  `attendance.check_in.created` or `attendance.check_out.created` in the business
  transaction. Rejections append no AuditLog; no Attendance OutboxEvent is
  approved. Each log targets the new Attendance, uses `before = {}`, and has
  exactly `attendance_id`, `kind`, `work_date`, `location_id`, and `session_id`
  in `after`; the shared sanitizer excludes coordinates, accuracy, maps URLs,
  request IP, and device metadata.
- API coordinate responses inherit private/no-store transport behavior. No reverse
  geocoder, third-party map call, or background telemetry is added.

## Migration Strategy

1. Add the `attendance` app and its four additive core/history tables in one
   initial migration, including constraints and indexes. Register the app only
   after the migration is deployable.
2. Use `db_default` for newly non-null booleans/JSON defaults (`closed_by_job`,
   metadata objects) so N-1 processes and direct inserts remain compatible.
3. Do not seed attendance rows, rewrite Location data, or add destructive/rename
   operations. Location foreign keys use `PROTECT` so historical evidence remains.
4. Prove migration from the immediately previous schema and inspect PostgreSQL
   catalog predicates/index names. Keep one migration leaf per app.
5. Deploy migration before application/UI enablement. Run the established
   reference-readiness check and enable routes/UI only after it proves one complete
   Config and exactly 76 canonical Locations; a failed check is read-only.

## Verification Strategy

### Unit tests

- Boundary/range/freshness validation and independent quality/radius truth table.
- Haversine boundary, all-76 nearest versus active-only candidates, canonical-code
  nearest tie-break, zero/one/many resolution, selected-location revalidation,
  and approximate weak-GPS metadata.
- Session state transitions, kind/work-date ownership, six-decimal duration
  quantization, unified punch-index derivation, approximate-nearest projection,
  and report-neutral failure-rate classification.
- Attempt draft/outcome mapping and the rule that candidate count is null until
  candidate matching actually executes.
- A parameterized seven-outcome attempt matrix covering attendance-link shape,
  candidate-count null/zero/positive semantics, nearest metadata, and exact one
  writer call; plus no attempt and sanitized telemetry for unexpected 5xx.

### API and contract tests

- HELPDESK allow paths; MANAGER/LEADER denial; malformed-body authorization
  precedence; server-owned-field rejection; actor-only object scope.
- Every success and canonical error status/body, including candidate lists and
  absence of attempt side effects before the boundary.
- Exact Maps URL derivation from stored captured decimals through one URL-encoding
  helper, actor authorization, no rounding/Location-coordinate substitution, and
  safe external-link rendering without iframe/SDK.
- OpenAPI path/schema generation, safety scanning, generated TypeScript client
  drift, and backward-compatibility checks.
- Frontend API wrappers, GPS lifecycle cleanup, choice resubmission with a fresh
  sample, loading/error states, and canonical today-state reconciliation.

### PostgreSQL integration tests

- Catalog and behavior proof for `uniq_open_session_per_user`, including a
  `closed_by_job=True, check_out=NULL` row not blocking a later Check In.
- Proof that same-user/same-date multiple `IN` and `OUT` rows are allowed.
- First Check In, double Check In, Check Out, no-session Check Out, and
  `IN→OUT→IN→OUT` with exact session/duration/attempt counts.
- Forced business rollback with the expected AttendanceAttempt still present.
- Two real connections/workers released by a barrier for double-tap Check In;
  repeat 100 trials and assert one accepted winner, one mapped loser, one open
  session, and one attempt per request.
- Two concurrent Check Out requests proving one accepted close and one
  `NO_OPEN_SESSION`, plus Config/Location update interleavings; no SQLite or mock
  result is cited for transaction/constraint guarantees.

### CI verification

- Run the existing `scripts/check_all.sh`, Ruff, strict mypy (including the new
  module), Django checks, pytest marker suites, frontend format/lint/typecheck/
  Vitest, architecture/import guards, migration safety, schema regeneration,
  TypeScript client regeneration, and OpenAPI compatibility comparison. CI uses
  deterministic tests and does not assert wall-clock latency.

### Pre-release acceptance

- Run the specified 100-trial PostgreSQL latency harness and record the measured
  p95 in `specs/004-attendance-core/evidence/latency-acceptance.md`; this is a
  signed feature acceptance budget, not a CI gate or production capacity claim.
- Record the SC-007 pre-release exercise with at least 20 representative
  HELPDESK participants and no coordinate evidence; 19 or more must complete
  both required journeys without assistance.

## Post-Design Constitution Re-check

All pre-design gates remain satisfied. The design adds no dependency, direct
cross-module model import, server-owned client field, unapproved outbox event type,
background GPS behavior, or service-only concurrency invariant. No complexity
exception is required.

## Complexity Tracking

No constitution violations require justification.
