# Phase 1 Data Model: Attendance Check-In and Check-Out Core

All persisted models belong to the new `attendance` Django app. Foreign keys to
`identity.User` and `locations.Location` use configured/string references at the
ORM boundary; application/domain code receives identifiers and snapshots through
ports. PostgreSQL is the authoritative constraint engine.

## Closed vocabularies

### AttendanceKind

- `IN`
- `OUT`

### LocationValidationResult used by Attendance

- `INSIDE_GEOFENCE`

`OUTSIDE_GEOFENCE` remains a domain classification value but is never persisted
on an accepted Attendance and is never an API error code.

### AttendanceResolutionMethod

- `AUTO_SINGLE`
- `USER_SELECTED`

`GPS_ONLY` is prohibited for Attendance.

### AttendanceAttemptOutcome

- `ACCEPTED`
- `WEAK_GPS`
- `OUTSIDE_RADIUS`
- `LOCATION_CHOICE_REQUIRED`
- `INVALID_LOCATION_CHOICE`
- `NO_OPEN_SESSION`
- `SESSION_ALREADY_OPEN`

### AttendanceAnomalyReason

- `LATE_CHECK_IN`
- `EARLY_CHECK_OUT`
- `LATE_CHECK_OUT`
- `MISSING_CHECK_OUT`

Feature 004 creates the schema and preserves transaction compatibility for this
already-governed relation. It does not add new anomaly reasons, manual adjustment,
or end-of-day scheduling behavior.

## Attendance

An immutable, accepted punch. No update or delete API is exposed.

| Field | Storage | Null/default | Rules |
|---|---|---|---|
| `id` | BigAutoField | required | Primary key |
| `user` | FK → User, PROTECT | required | Authenticated HELPDESK actor; server-owned |
| `kind` | CharField(3) | required | Closed `IN`/`OUT`; route-owned |
| `work_date` | DateField | required | `recorded_at` converted to Asia/Ho_Chi_Minh |
| `recorded_at` | DateTimeField | required | One server UTC timestamp captured for the request |
| `captured_at` | DateTimeField | nullable | Client GPS capture time retained only for evidence |
| `captured_latitude` | DecimalField(18,15) | required | `-90 <= value <= 90` |
| `captured_longitude` | DecimalField(18,15) | required | `-180 <= value <= 180` |
| `accuracy_m` | DecimalField(10,3) | required | Finite and `>= 0`; passed attendance threshold |
| `location` | FK → Location, PROTECT | required | One active candidate resolved for this request |
| `distance_m` | DecimalField(12,3) | required | Finite and `>= 0`; measured distance to resolved Location |
| `validation_result` | CharField(32) | required | Always `INSIDE_GEOFENCE` |
| `resolution_method` | CharField(32) | required | `AUTO_SINGLE` or `USER_SELECTED` |
| `device_metadata` | JSONField | `{}` with DB default | Approved device/browser evidence only |
| `request_ip` | GenericIPAddressField | nullable | Protected diagnostic evidence |

Constraints and indexes:

- Check `kind IN ('IN','OUT')`.
- Check coordinate, accuracy, and distance ranges.
- Check `validation_result = 'INSIDE_GEOFENCE'`.
- Check resolution method in the two-value Attendance set.
- Index `(user_id, work_date, recorded_at, id)` for the self timeline and
  deterministic punch-index derivation.
- Do **not** add uniqueness on `(user_id, work_date, kind)` or any equivalent
  validation. Multiple same-day pairs are required.

Relationships:

- Every accepted Attendance has exactly one accepted AttendanceAttempt when the
  post-transaction observational write succeeds; R-120 explicitly allows a gap
  when that writer fails or the process dies after commit.
- Every accepted Attendance is the target of exactly one punch AuditLog using the
  route-specific Check In/Out action; rejected attempts have no punch AuditLog.
- Every Attendance participates in at most one session edge: an `IN` as
  `check_in`, or an `OUT` as `check_out`.
- `maps_url`, `resolved_address`, `has_anomaly`, and `punch_index` are derived;
  they are not columns. `maps_url` uses the stored captured decimals exactly, not
  the related Location coordinates.

## AttendanceSession

One work interval. The session's work date is copied from its Check In punch and
does not roll over at midnight.

| Field | Storage | Null/default | Rules |
|---|---|---|---|
| `id` | BigAutoField | required | Primary key |
| `user` | FK → User, PROTECT | required | Same user as both boundary punches |
| `work_date` | DateField | required | Same date as Check In |
| `check_in` | OneToOne → Attendance, PROTECT | required | Must reference an `IN` punch |
| `check_out` | OneToOne → Attendance, PROTECT | nullable | When present, must reference an `OUT` punch for same user |
| `duration_minutes` | DecimalField(12,6) | nullable | Exact timestamp delta quantized once to six decimal minutes with `ROUND_HALF_UP` |
| `closed_by_job` | BooleanField | false with DB default | Canonical job-closure marker |
| `created_at` | DateTimeField | auto/server | Persistence timestamp, not payroll time |

Canonical states:

| State | `check_out` | `duration_minutes` | `closed_by_job` |
|---|---|---|---|
| Open | null | null | false |
| User closed | OUT Attendance | non-negative | false |
| Job closed | null | null | true |

Constraints and indexes:

- Conditional unique constraint:
  `UNIQUE(user_id) WHERE check_out_id IS NULL AND closed_by_job = FALSE`, named
  `uniq_open_session_per_user`.
- State-shape check permitting only the three rows in the table above.
- Check `duration_minutes >= 0` when present.
- Unique one-to-one constraints on `check_in_id` and non-null `check_out_id`.
- Check In/Out kind, user equality, work-date equality, and duration derivation are
  cross-row invariants enforced by the application transaction and covered by
  PostgreSQL integration tests; Django check constraints cannot traverse FKs.
- Index `(user_id, work_date, id)` for today/session projection.

State transitions:

```text
no open session --valid IN--> open
open --valid OUT--> user closed
open --existing end-of-day process--> job closed
```

`IN` while open produces `SESSION_ALREADY_OPEN`; `OUT` without open produces
`NO_OPEN_SESSION`. There is no nested/open-twice state.

Duration calculation subtracts the two UTC server timestamps at microsecond
precision, converts to decimal minutes, and applies `ROUND_HALF_UP` exactly once
at six decimal places. Open and job-closed sessions retain null duration.

## AttendanceAttempt

Observational history for exactly one request after the attendance boundary that
ends in one of the seven classified business outcomes. It is inserted after the
business transaction exits and is never part of the accepted punch/session atomic
unit. Unexpected infrastructure 5xx failures create no row and are never relabeled
to satisfy this model.

| Field | Storage | Null/default | Rules |
|---|---|---|---|
| `id` | BigAutoField | required | Primary key |
| `user` | FK → User, PROTECT | required | Authenticated actor |
| `kind` | CharField(3) | required | Server route-derived |
| `work_date` | DateField | required | Derived from attempt `recorded_at` |
| `recorded_at` | DateTimeField | required | Same captured server timestamp used by accepted Attendance |
| `outcome` | CharField(32) | required | Exactly one of seven closed values |
| `attendance` | OneToOne → Attendance, PROTECT | nullable | Present if and only if `outcome=ACCEPTED` |
| `captured_latitude` | DecimalField(18,15) | required | Submitted validated coordinate |
| `captured_longitude` | DecimalField(18,15) | required | Submitted validated coordinate |
| `accuracy_m` | DecimalField(10,3) | required | Submitted validated accuracy |
| `nearest_location` | FK → Location, PROTECT | nullable | Nearest from the same locked 76-row snapshot used for active candidates; equal distance chooses smallest canonical `code` |
| `nearest_distance_m` | DecimalField(12,3) | nullable | Distance-only diagnostic; no radius membership |
| `candidate_count` | PositiveSmallIntegerField | nullable | Null until active candidate matching runs; zero is a real result |
| `device_metadata` | JSONField | `{}` with DB default | Approved protected evidence |
| `request_ip` | GenericIPAddressField | nullable | Protected diagnostic evidence |

Constraints and indexes:

- Check kind and closed outcome sets.
- Check accepted consistency:
  `(outcome='ACCEPTED' AND attendance_id IS NOT NULL) OR
  (outcome<>'ACCEPTED' AND attendance_id IS NULL)`.
- Check nearest pair consistency: Location and distance are both null or both
  present; distance is non-negative.
- Check coordinate/accuracy ranges and non-negative candidate count.
- Index `(user_id, work_date, recorded_at, id)` for request history.
- Index `(work_date, outcome)` for governed date/outcome aggregation.
- Index `(nearest_location_id, outcome)` for governed reporting.
- No uniqueness by user/date/kind and no candidate-id array/JSON field.

Outcome field semantics:

| Outcome | Candidate matching ran? | `candidate_count` | Attendance link |
|---|---:|---:|---:|
| `SESSION_ALREADY_OPEN` | no | null | null |
| `NO_OPEN_SESSION` | no | null | null |
| `WEAK_GPS` | no | null | null |
| `OUTSIDE_RADIUS` | yes | 0 | null |
| `LOCATION_CHOICE_REQUIRED` | yes | >=2 | null |
| `INVALID_LOCATION_CHOICE` | yes | current count | null |
| `ACCEPTED` | yes | >=1 | required |

Nearest metadata is populated independently for every row when the 76-row
reference-data readiness invariant holds. Exact distance ties select the
lexicographically smallest canonical Location `code`; this does not affect the
active candidate set. `nearest_is_approximate` is derived as
`outcome == WEAK_GPS`; it is not a column.

The domain's report-neutral classification treats the five rejection outcomes
other than `LOCATION_CHOICE_REQUIRED` as failure-numerator members, treats
`ACCEPTED` as denominator-only, and excludes `LOCATION_CHOICE_REQUIRED` from both.
No reporting table, endpoint, or screen is part of Feature 004.

## AttendanceAnomaly

Immutable/correctable governed anomaly evidence attached to accepted attendance.

| Field | Storage | Null/default | Rules |
|---|---|---|---|
| `id` | BigAutoField | required | Primary key |
| `attendance` | FK → Attendance, PROTECT | required | Accepted punch |
| `reason` | CharField(32) | required | Closed four-value set |
| `metadata` | JSONField | `{}` with DB default | Sanitized business context, never coordinates |
| `created_at` | DateTimeField | auto/server | Evidence timestamp |

- Unique `(attendance_id, reason)` prevents duplicate identical anomalies.
- Check the four-value reason set.
- Index `(reason, created_at, id)` for later reporting.
- Feature 004 does not create an adjustment endpoint or expand job behavior.

## Self Attendance Read Model

Not persisted. Query inputs are only `actor_id` and server `now`.

```text
TodayAttendance
├── work_date
├── has_open_session
├── total_duration_minutes
├── punches[]
│   ├── attendance fields needed by employee UI
│   ├── location {id, code, name, address}
│   ├── maps_url
│   ├── resolved_address
│   └── punch_index
└── sessions[]
    ├── id, work_date
    ├── check_in_at, check_out_at
    ├── check_in_location_id, check_out_location_id
    ├── duration_minutes
    └── closed_by_job
```

Rules:

- Work date comes from server time converted to Asia/Ho_Chi_Minh.
- Query always filters `user_id=actor_id`; no supplied user id exists.
- Punches order by `(recorded_at, id)` and are enumerated from one across both
  kinds.
- `has_open_session` uses both canonical predicate terms.
- Total sums only non-null user-closed durations; breaks, open sessions, and
  job-closed sessions contribute nothing.

## Data retention and privacy

- Attendance, sessions, attempts, and anomalies are not hard-deleted by Feature
  004. User and Location references use `PROTECT` to retain history.
- Precise coordinates, accuracy, device metadata, and request IP remain in
  protected business tables and coordinate-bearing self responses only.
- These values are excluded from AuditLog, OutboxEvent, generic logs, and error
  telemetry. No reverse-geocoded address is persisted.
