# Phase 0 Research: Attendance Check-In and Check-Out Core

## Repository baseline

The repository already supplies Django 5.2/DRF, PostgreSQL, strict serializers,
canonical errors, centralized `PermissionAction` RBAC, transaction-oriented
application services, audit/outbox ports, pure haversine/geofence functions,
Location and Config repositories, OpenAPI generation, a generated openapi-fetch
client, and real-PostgreSQL concurrency test patterns. There is no attendance
module yet. The source CSVs contain 69 shops and 7 business centers, matching the
closed 76-Location Feature 003 readiness invariant.

## R-119 equal-distance nearest tie

**Decision**: When multiple canonical Locations share the minimum distance,
persist the Location with the lexicographically smallest canonical `code`.

**Rationale**: `AttendanceAttempt` has one nearest FK, and canonical code remains
stable across database reseeding and environments. This tie-break is strictly
observational and does not remove or auto-select equal geofence candidates.

**Alternatives considered**:

- Smallest database id: rejected because ids are persistence identities and may
  differ between environments or rebuilds.
- Null on a tie: rejected because it creates avoidable diagnostic coverage gaps.
- Persist all tied Locations: rejected because it expands the approved singular
  model and reporting contract without a demonstrated need.

## R-118 nearest population

**Decision**: Compute `AttendanceAttempt.nearest_location` over all 76 canonical
Locations, including inactive records. Compute candidates, auto-selection, and
selected-location validation over active Locations only. Order nearest results
by `(distance_m, code)` so R-119 resolves exact-distance ties deterministically.

**Rationale**: Nearest is diagnostic grouping metadata. Deactivation must not
erase the geographic grouping of future failed attempts, but an inactive record
must never authorize attendance. The existing Location repository already
supports both `is_active=None` and `is_active=True`, so separate port operations
express this distinction without new infrastructure.

**Alternatives considered**:

- Active-only nearest: rejected by stakeholder decision A/R-118 because it can
  remove the most geographically relevant diagnostic group.
- Nearest active candidate: rejected because nearest observation is not a
  geofence-membership or candidate decision.

## Attendance module ownership

**Decision**: Introduce a first-class `backend/attendance` app with
domain/application/ports/adapters and a matching frontend feature slice.

**Rationale**: Attendance owns state transitions, attempt semantics, session
invariants, and projections. Putting them in `locations` would collapse two
business policies into geometry infrastructure; putting them in views/models
would violate the constitution and existing repository pattern.

**Alternatives considered**:

- Extend `locations`: rejected because Locations own reference data and generic
  geometry, not attendance sessions or payroll-relevant transitions.
- Put orchestration in DRF views: rejected because it would duplicate gate order
  and transaction rules at the delivery boundary.

## Cross-module integration

**Decision**: Define attendance-owned ports for authorization and reference-data
snapshots, and adapt existing identity/locations services in the composition root.
Reuse the pure distance/classification behavior behind a port; do not import
foreign models or adapters from attendance production code.

**Rationale**: This complies with the repository's explicit module-boundary tests
and preserves single ownership of Config and Location persistence.

**Alternatives considered**:

- Direct ORM imports from `locations.models` and `identity.models`: rejected by
  Constitution Principle II.
- Duplicate Location/Config tables or geometry code: rejected as a competing
  source of truth.

## Business transaction boundary

**Decision**: Use one transaction for the accepted punch, session transition,
approved anomaly reconciliation, and any invariant-bound audit append. Begin
with the established Config-first lock order and use row locking for an existing
open session on Check Out.

**Rationale**: Acceptance cannot leave an unpaired punch or half-closed session.
Config-first ordering matches Feature 003 Location/Config writers, preventing
reference-data changes from splitting one evaluation while avoiding a new lock.

**Alternatives considered**:

- Independent saves: rejected because rollback could leave payroll state split.
- External distributed lock: rejected because PostgreSQL already provides the
  required mechanism and no new infrastructure is approved.

## Double-tap concurrency

**Decision**: Keep a service pre-check for clear errors but make PostgreSQL's
partial unique constraint on `(user)` where `check_out IS NULL AND
closed_by_job = FALSE` authoritative. Translate only the named constraint's
`IntegrityError` to `SESSION_ALREADY_OPEN` after transaction rollback.

**Rationale**: A first Check In has no existing session row to lock, so a
pre-check cannot prevent two concurrent inserts. The partial uniqueness rule is
the approved invariant and also permits job-closed rows with no fabricated OUT.

**Alternatives considered**:

- Pre-check only: rejected because both requests can see no row.
- Daily uniqueness on Attendance: rejected because it breaks multiple sessions.
- Advisory/distributed locks: rejected as unnecessary infrastructure and a less
  direct expression of the invariant.

## AttendanceAttempt transaction semantics

**Decision**: Build an attempt draft after the boundary, run the business unit of
work, let it commit or roll back, and then insert exactly one attempt on accepted
and expected-business-rejection paths. Unexpected database/network/process/
framework failures retain canonical 5xx handling and create no attempt; they are
never relabeled as one of the seven closed outcomes. Never create attempts in
middleware, inside the business `atomic()` block, or through `on_commit()`.

**Rationale**: Race-loser and rejected attempts must survive business rollback.
Middleware cannot map the closed business outcomes and would log pre-boundary
requests. `on_commit()` does not execute for rollback paths.

**Alternatives considered**:

- Same transaction: rejected by CHOT/R-74 because rejected attempts disappear.
- Separate database/queue: rejected because no new infrastructure is needed and
  the accepted process-crash gap is explicit.

## Attempt persistence failure

**Decision**: A failure to append observational attempt data after the business
transaction does not roll back or relabel the business result. Emit sanitized
telemetry and return the original acceptance/rejection; never log coordinates,
device data, request IP, or maps URLs.

**Rationale**: Attempts are explicitly observational and an accepted process
failure gap exists. Returning a false failure after a committed punch encourages
unsafe retries and violates telemetry non-interference.

**Alternatives considered**:

- Return 500 after a committed punch: rejected because the client cannot know
  whether the punch exists.
- Transactional outbox for attempts: rejected because it changes R-74 semantics
  and introduces an unapproved durability mechanism.

## Gate ordering and reference consistency

**Decision**: Preserve authentication/RBAC/strict validation before the attempt
boundary, then session state, attendance accuracy, and active geofence candidates.
Inside the business transaction, lock Config and load one snapshot of all 76
canonical Locations. Nearest uses the full snapshot and candidates filter its
active rows; nearest cannot call candidate classification or affect the business
branch.

**Rationale**: This is the exact CHOT order and keeps the quality gate independent
from radius. Locking Config before reference-data evaluation aligns attendance
with concurrent Location/Config administration.

**Alternatives considered**:

- Geofence before session state: rejected because it changes outcome precedence.
- Adjust radius with accuracy: rejected by the core business rule.
- Read nearest and candidates separately: rejected because a concurrent admin
  edit could make one request observe two reference-data versions.

## Maps projection ownership

**Decision**: Derive `maps_url` in one backend helper from each Attendance's
stored captured decimal coordinates, preserving their database representation
and URL-encoding the query. Never derive from Location coordinates or accept a
client URL. Frontend links open with `_blank` and `noopener noreferrer`; iframe,
SDK, reverse geocoding, and network map calls are excluded.

**Rationale**: The link must show captured evidence, stay deterministic, and
remain under the record's existing authorization without creating a third-party
runtime dependency.

**Alternatives considered**:

- Build URLs independently in serializers and clients: rejected because it
  duplicates security-sensitive formatting and can drift.
- Round coordinates for display: rejected because CHOT requires exact stored
  decimals in the link.

## Selected-location error precedence

**Decision**: Recompute active candidates before validating a supplied
`selected_location_id`. An empty set returns `OUTSIDE_RADIUS`; only a non-empty
set that omits the supplied id returns `INVALID_LOCATION_CHOICE`.

**Rationale**: CHOT step 8 precedes selection validation in step 10. This keeps
zero-candidate behavior stable whether or not a stale client selection is sent.

**Alternatives considered**:

- Treat every absent selected id as invalid: rejected because it bypasses the
  authoritative no-candidate branch.

## Read model and punch ordering

**Decision**: Derive `punch_index` on read over one combined IN/OUT sequence
ordered by `(recorded_at, id)`, where `id` is only a deterministic tie-break for
equal server timestamps. Sum only user-closed session durations; open and
job-closed/null-duration sessions do not contribute.

**Rationale**: The index is presentation state and must not become a mutable
stored sequence. The secondary key prevents unstable output without changing
the server-time business order.

**Alternatives considered**:

- Persist punch index: rejected because later corrections/deletions would make
  it a competing source of truth.
- Separate IN and OUT counters: rejected because CHOT requires one timeline.

## API and generated client

**Decision**: Add three versioned endpoints through DRF serializers/views,
describe them in drf-spectacular, regenerate the canonical OpenAPI document, and
regenerate the committed TypeScript schema consumed by openapi-fetch.

**Rationale**: This is the repository's existing one-contract pipeline and keeps
snake_case wire fields consistent.

**Alternatives considered**:

- Handwrite a frontend response interface: rejected because it would duplicate
  generated contract types.
- Add GraphQL/WebSocket/SSE: rejected because neither is required.

## Frontend geolocation lifecycle

**Decision**: Use foreground watch only for readiness feedback and obtain a
`maximumAge: 0` sample for each submission. Stop location activity on hidden,
unmount, cancel, timeout, or submit. Candidate confirmation obtains another fresh
sample and resubmits its selected id.

**Rationale**: This preserves privacy, avoids cached/background punches, and lets
the backend revalidate selection against current coordinates.

**Alternatives considered**:

- Reuse the first ambiguous sample: rejected because the employee may move and
  the server requires current candidates.
- Background tracking or auto-punching: explicitly out of scope.

## Audit and outbox

**Decision**: A successful Check In appends
`attendance.check_in.created`; a successful Check Out appends
`attendance.check_out.created`. The AuditLog targets the created Attendance,
joins the punch transaction, and contains only sanitized identifiers and business
state. Rejections append no AuditLog. Routine punches append no OutboxEvent.

**Rationale**: CHOT requires invariant-bound attendance audit evidence and now
defines the two closed actions. Separate actions preserve meaning without copying
GPS evidence into generic audit payloads. No consumer or attendance event type is
approved for the outbox.

**Alternatives considered**:

- One generic `attendance.punch.created` action: rejected because it makes audit
  interpretation depend on payload inspection.
- Add `attendance.checked_in/out` outbox events: rejected as an unapproved event
  contract with no current consumer.
- Treat AttendanceAttempt as AuditLog: rejected because their transaction and
  reporting semantics deliberately differ.

## Duration precision

**Decision**: Derive `duration_minutes` from the exact UTC timestamp delta and
quantize once to six decimal minute places with `ROUND_HALF_UP`.

**Rationale**: The approved DecimalField cannot represent every microsecond delta
without a precision rule. One named quantization preserves deterministic storage
and avoids minute-level payroll rounding.

**Alternatives considered**:

- Claim the six-decimal value is mathematically unrounded: rejected because many
  timestamp deltas produce repeating decimal minutes.
- Add a second exact-duration column: rejected as redundant schema not required
  by CHOT.

## Additive migration

**Decision**: Create new tables, constraints, and indexes additively; use database
defaults for new required defaultable fields; do not seed attendance data or
modify existing Location rows.

**Rationale**: Feature 004 starts with no attendance tables, so expansion is
sufficient and compatible with the previous application version.

**Alternatives considered**:

- Backfill synthetic punches/sessions: rejected because there is no trustworthy
  source and it would fabricate payroll history.
- Reuse or alter Feature 003 migration: rejected because shipped migrations are
  immutable and each app must retain a single leaf.
