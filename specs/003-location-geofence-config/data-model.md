# Data Model: Location, Geofence, Configuration and Reference Data

## Ownership overview

```text
locations.Config (exactly one, id=1)
       │
       └── supplies radius/quality/shift/workweek policy

locations.Location (exactly 76)
       └── parent 0..1 ──> Location(kind=BUSINESS_CENTER)

locations.Holiday (0..*)

identity.User ── actor only ──> audit.AuditLog
locations aggregates ── logical identity ──> audit.OutboxEvent
```

`locations` owns all three persistent entities. It does not own or create Attendance, Task,
Report, or Notification relationships. Future modules reference Location/Config through
their own application ports and migrations.

## Domain value models

### LocationKind

Closed values:

- `BUSINESS_CENTER`
- `SHOP`

Centers have no parent. Shops use the source-derived parent center or null when the derived
code does not exist. API updates cannot change kind or parent.

### ValidatedPosition

| Field | Rule |
|---|---|
| `latitude` | Finite and inclusive `[-90, 90]`. |
| `longitude` | Finite and inclusive `[-180, 180]`. |
| `accuracy_m` | Finite and `>= 0`; carried as measurement quality only. |

Raw JSON/CSV values never construct this type until boundary validation succeeds.

### LocationValidationResult

Exactly two values:

- `INSIDE_GEOFENCE`
- `OUTSIDE_GEOFENCE`

`UNCERTAIN` and synonyms do not exist. Classification consumes distance and radius only.

### LocationWarning

| Value | Meaning | Persistence effect |
|---|---|---|
| `GEOFENCE_OVERLAP` | Candidate radius overlaps one or more other Locations. | None; save/seed continues. |
| `RADIUS_BELOW_ATTENDANCE_ACCURACY` | Effective radius is below Config attendance accuracy threshold. | None; save/config update continues. |

Warnings may carry related Location ids/codes and numeric thresholds, but never exact
coordinates. They are recomputed response/command results and are not stored.

## Persistent entities

### locations.Location

| Field | Type/nullability | Default/validation | Constraint/index |
|---|---|---|---|
| `id` | Big integer PK | Server generated | PK |
| `code` | varchar(16), NOT NULL | Source identity; trimmed/nonblank | UNIQUE; nonblank check; immutable trigger |
| `name` | varchar(255), NOT NULL | Source/Manager mutable; trimmed/nonblank | Nonblank check |
| `kind` | varchar(24), NOT NULL | Closed LocationKind | Check in two values; `(kind, code)` index |
| `parent` | self FK, NULL | Source-derived; API immutable | `PROTECT`; parent index |
| `address` | text, NOT NULL | Source/Manager mutable; nonblank | Nonblank check |
| `latitude` | decimal(18,15), NOT NULL | Exact source decimal or validated update | Check `-90 <= value <= 90` |
| `longitude` | decimal(18,15), NOT NULL | Exact source decimal or validated update | Check `-180 <= value <= 180` |
| `radius_m` | decimal(10,3) meters, NOT NULL | Seed from Config; Manager mutable | Check `> 0`; Config max checked under lock |
| `is_active` | boolean, NOT NULL | Seed true | Python + DDL default true; filter index |
| `version` | positive bigint, NOT NULL | Initial 1; server increments | Python + DDL default 1; check `>= 1` |

Cross-row invariants:

1. The complete table contains exactly the canonical 76 codes after seed.
2. Exactly seven rows are centers and 69 are shops.
3. Center parent is null; shop parent is null or a center.
4. `HCM000079.parent` is null; canonical derived matches such as `HCM020129` point to
   `HCM020000`.
5. `radius_m <= Config.max_radius_m` applies to active and inactive rows and is checked while
   Config is locked. A Config candidate below any current Location radius is rejected; it
   never rewrites Location radii.
6. Duplicate coordinates and overlaps are valid; no unique/exclusion constraint exists.

Code/kind/parent cannot change through API. The code immutability trigger protects ORM,
shell, and bulk update paths. Seed reconciles other source/config-owned fields but never
changes an identity code.

### locations.Config

Exactly one complete row with primary key `1`.

| Field | Type/nullability | Default/validation | Constraint |
|---|---|---|---|
| `id` | small integer PK | Always 1 | PK + check `id = 1` |
| `timezone` | varchar(64), NOT NULL | `Asia/Ho_Chi_Minh`; immutable through API | Check exact value |
| `working_weekdays` | JSON array, NOT NULL | `[0,1,2,3,4,5]` | Domain: duplicate-free subset of 0..6 |
| `default_radius_m` | decimal(10,3) meters, NOT NULL | 50 | finite; `> 0`; `<= max_radius_m` |
| `max_radius_m` | decimal(10,3) meters, NOT NULL | 70 | finite; `> 0` |
| `max_attendance_accuracy_m` | decimal(10,3) meters, NOT NULL | 25 | finite; `> 0` |
| `task_gps_good_accuracy_m` | decimal(10,3) meters, NOT NULL | 25 | finite; `> 0`; `<= task_gps_low_accuracy_m` |
| `task_gps_low_accuracy_m` | decimal(10,3) meters, NOT NULL | 100 | finite; `> 0` |
| `shift_start` | time, NOT NULL | Explicit initialization input | `< shift_end` |
| `shift_end` | time, NOT NULL | Explicit initialization input | `> shift_start` |
| `late_grace_minutes` | nonnegative integer, NOT NULL | Explicit initialization input | `>= 0` |
| `early_checkout_grace_minutes` | nonnegative integer, NOT NULL | Explicit initialization input | `>= 0` |
| `late_checkout_grace_minutes` | nonnegative integer, NOT NULL | 60 | `>= 0` |

Config has no optimistic version in Feature 003. Updates lock the singleton, overlay a
partial DTO on the latest row, validate the complete candidate, and commit atomically.
Concurrent same-field updates linearize in lock order.

Finite checks apply independently to all five meter-valued decimal fields before ordering
comparisons. Boundary/domain validation rejects `NaN` and positive/negative infinity, and
PostgreSQL constraints remain the final defense against non-finite direct writes.

### locations.Holiday

| Field | Type/nullability | Default/validation | Constraint/index |
|---|---|---|---|
| `id` | Big integer PK | Server generated | PK |
| `date` | date, NOT NULL | Client supplied | UNIQUE; stable ordering index |
| `name` | varchar(255), NOT NULL | Trimmed/nonblank | Nonblank check |

No automatic generation, soft/hard-delete cascade, or job behavior is attached. The public
delete operation removes only the Holiday row after attributable evidence is appended in
the same transaction.

## DTO and result models

### LocationFilter

Optional `kind`, `parent`, and `is_active`. Unknown/invalid values are boundary validation
errors. Absence means the full 76-row directory, including inactive rows.

### UpdateLocationRequest

| Client-owned | Server-owned/rejected |
|---|---|
| Required `version`; optional name, address, latitude, longitude, radius_m, is_active, reason | id, code, kind, parent, version progression, warnings, distance/result |

At least one mutable state field is required; `reason` alone is not a mutation. Stale result
contains current version and submitted reason, not current coordinates.

### UpdateConfigRequest

Any subset of working weekdays, radii, thresholds, shift, and grace fields. `id`, timezone,
version, and unknown fields are rejected. The service validates the full resulting
singleton, not fields independently.

### Holiday requests

- Create: date and nonblank name only.
- Delete: route id only.
- No update endpoint.

### GPS rule inputs/results

The public domain entry points consume `ValidatedPosition` and a Location center/radius
snapshot and return distance plus one of the two validation results. There is no Feature
003 HTTP DTO for geofence evaluation.

## Seed source records

### CenterSourceRow

Explicit mapping:

| Domain field | CSV header |
|---|---|
| code | `Mã TTKD` |
| name | `Tên` |
| address | `ADDRESS` |
| latitude | `LATITUDE` |
| longitude | `LONGITUDE` |

`STT` is ignored. Kind is constant `BUSINESS_CENTER`; parent null.

### ShopSourceRow

Explicit mapping:

| Domain field | CSV header |
|---|---|
| code | `SHOP_CODE` |
| name | `NAME` |
| address | `ADDRESS` |
| latitude | `LATITUDE` |
| longitude | `LONGITUDE` |

Kind is constant `SHOP`. Parent code is exactly `SHOP_CODE[:5] + "0000"`; an unmatched
canonical center makes parent null.

## State transitions

### Location

```text
absent canonical code --seed--> version 1, active, source/config state
existing canonical code --unchanged seed--> no-op, same version/evidence
existing canonical code --changed seed--> reconciled state, version + 1
existing canonical code --valid PATCH(current version)--> candidate, version + 1
existing canonical code --same-value PATCH(current version)--> 200 no-op, same versions/evidence
existing canonical code --stale PATCH--> unchanged, conflict
```

Location identity is never created/deleted by API and never changes code.

### Config

```text
absent --controlled complete initialization--> singleton id=1
present --valid PATCH under lock--> complete new state
present --same-value PATCH under lock--> 200 no-op, same evidence/aggregate version
present --max below any Location radius--> validation failure, unchanged
present --invalid PATCH--> unchanged
present --second initialization--> rejected
```

### Holiday

```text
absent date --create--> one Holiday
existing date --create--> validation/unique failure, unchanged
existing id --delete--> absent with evidence
missing id --delete--> not found, no evidence
```

## Transaction/evidence model

- Location/Config/seed paths lock Config first. Location paths then lock Location rows in
  stable id order.
- Location version comparison precedes no-op detection. Config and Location no-ops return
  current warnings but never call persistence/evidence appenders.
- Holiday create relies on unique date; delete locks the target row.
- State, AuditLog, and OutboxEvent share one caller UoW.
- Location aggregate lock, Config singleton lock, or Holiday row lock remains held through
  outbox aggregate-version allocation.
- Newly inserted aggregate records exist before event version 1 is allocated.
- Audit/outbox Location payloads never contain latitude/longitude. Coordinate changes are
  represented by changed-field names only.
