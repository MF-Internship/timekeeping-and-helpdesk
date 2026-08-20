# Implementation Plan: Location, Geofence, Configuration and Reference Data

**Branch**: `003-location-geofence-config` | **Date**: 2026-08-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-location-geofence-config/spec.md`

## Summary

Add one cohesive `locations` business module that owns the closed 76-row Location set,
pure GPS/Haversine/geofence rules, singleton Config, and Holiday reference data. The module
reuses Feature 001 contract/delivery gates and Feature 002 authentication, canonical RBAC,
audit, and outbox foundations through public ports. It exposes Location list/update,
Config read/update, and Holiday management; it does not create Location records through an
API and does not implement Attendance or Task workflows.

The two canonical CSVs are parsed with separate explicit mappings before any write. One
atomic, attributable seed/reconciliation use case establishes exactly 7 centers and 69
shops, preserves decimal coordinate values, accepts duplicate coordinates, rejects
duplicate codes, and reports overlaps as warnings. Location optimistic updates and Config
validation lock Config before Location so radius/config races serialize consistently.

## Technical Context

**Language/Version**: Python 3.12; TypeScript 5.9; Node.js 22

**Primary Dependencies**: Existing Django 5.2, Django REST Framework 3.16,
drf-spectacular 0.28, psycopg 3.2, Next.js 16, React 19, openapi-fetch 0.14; Python
standard-library `csv`, `decimal`, and `math`. No new dependency.

**Storage**: PostgreSQL 17 in CI/runtime; canonical CSVs under `docs/`; generated OpenAPI
and TypeScript schema remain committed artifacts.

**Testing**: pytest 8.4/pytest-django with unit, architecture, contract, API integration,
and real PostgreSQL integration/race groups; Vitest/Testing Library for frontend; existing
Ruff, mypy, ESLint, TypeScript, migration, schema drift, and compatibility gates.

**Target Platform**: Existing Linux-hosted web application, same-origin Next.js frontend
and Django REST API under `/api/v1/`.

**Project Type**: Web application with a modular Django backend and Next.js frontend.

**Performance Goals**: Unpaginated reads over the fixed 76 Location rows should remain
within the existing operator-measured p95 <= 500 ms budget; all accepted maintenance flows
must remain usable in under two minutes. These are evidence goals, not fabricated CI timing
assertions.

**Constraints**: Exactly 76 total Locations; no Location API create/delete; exact source
coordinate preservation; GPS quality independent from geofence radius; no precise
coordinates in audit/outbox/schema examples; RBAC before DTO validation; all mutation,
audit, and outbox writes atomic; no Attendance/Task implementation.

**Scale/Scope**: 7 centers, 69 shops, one Config, a small manually maintained Holiday set,
three roles, seven API operations across three resource groups, and pure geometry reusable by
future Features 004 and 006.

## Constitution Check

*GATE: PASS before research; PASS again after Phase 1 design.*

| Principle/gate | Status | Plan evidence |
|---|---|---|
| I. Source of truth | PASS | R-113–R-117 are synchronized in CHOT, QUY_TAC, PRD, and spec; no open Feature 003 governance marker remains. |
| II. Fixed stack/inward architecture | PASS | New `locations` module has domain/application/ports/adapters; no new dependency; cross-module use is through Identity and Audit ports. |
| III. Ordered authorization | PASS | Every protected view declares an action; injected permission adapter runs authentication/action/account gates before serializers. |
| IV. Server authority | PASS | Code/kind/parent/id/version progression and computed distance/results are server-owned; raw GPS is boundary-validated. |
| V. DB invariants/transactions | PASS | PostgreSQL constraints plus Config→Location/Holiday row locks; audit/outbox join caller UoW. |
| VI. Audit/privacy | PASS | Location/Config/Holiday mutations are attributable; coordinates are removed from audit/outbox payloads. |
| VII. Generated contracts | PASS | Backend schema regenerates `contracts/openapi.yaml`; only `schema.ts` is generated; `client.ts` stays handwritten and thin. |
| VIII. Schema evolution | PASS | New additive `locations.0001_initial`; no contraction or change to existing migration ownership. |
| IX. Security | PASS | Existing authentication/account gates; no secret, token, URL, or precise coordinate example in generated/public artifacts. |
| X. Location/GPS integrity | PASS | Separate CSV mappings, exact decimals, duplicate-coordinate acceptance, pure Haversine, two-state geofence, independent accuracy. |
| XI. Correct-layer tests | PASS | Pure rules use unit tests; constraints, rollback, locks, seed atomicity, and races use PostgreSQL. |
| XII. Naming/maintainability | PASS | Canonical `Location`, `LocationKind`, `LocationValidationResult`, unit suffixes, and existing size/complexity gates. |

Post-design re-check: the model, contracts, and test design below preserve every PASS. No
complexity waiver is required.

## Scope and Ownership

`locations` owns:

- `Location`, `LocationKind`, hierarchy, active state, radius, optimistic version;
- pure `ValidatedPosition`, Haversine distance, overlap detection, and
  `LocationValidationResult`;
- singleton `Config` and its complete validation policy;
- `Holiday` reference data;
- canonical two-file seed/reconciliation and warning production;
- Location/Config/Holiday API adapters and frontend feature UI.

Existing modules retain ownership:

- `identity`: current User authentication, account gates, canonical actions and
  permission provenance. Feature 003 adds only a public authorization gateway needed by a
  new module; it does not duplicate roles or grants.
- `audit`: immutable AuditLog/OutboxEvent persistence and payload sanitization. Feature 003
  generalizes the public record port so event enums are not Identity-only, without changing
  Feature 002 event behavior.
- `config`: settings, URLs, and late concrete composition only.
- `core`: unchanged technical primitives/error envelope; it receives only new canonical
  error constants/messages, not location business rules.

Deferred owners:

- Feature 004 Attendance owns accuracy acceptance, candidate selection, attendance
  ownership, and Check In/Out behavior.
- Feature 006 Task owns task GPS quality outcomes, creator/assignee scope, completion, and
  candidate selection.
- Neither future model, endpoint, serializer, helper, nor placeholder table is created here.

## Project Structure

### Documentation (this feature)

```text
specs/003-location-geofence-config/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── api.md
│   ├── events.md
│   ├── frontend.md
│   └── seed.md
└── tasks.md                 # generated later by /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── locations/
│   ├── apps.py
│   ├── models.py
│   ├── domain/
│   │   ├── config.py
│   │   ├── geofence.py
│   │   ├── locations.py
│   │   └── events.py
│   ├── application/
│   │   ├── container.py
│   │   ├── dependencies.py
│   │   ├── dto.py
│   │   ├── queries.py
│   │   ├── location_admin.py
│   │   ├── config_admin.py
│   │   ├── holidays.py
│   │   ├── readiness.py
│   │   └── seed.py
│   ├── ports/
│   │   ├── repositories.py
│   │   ├── unit_of_work.py
│   │   └── source_data.py
│   ├── adapters/
│   │   ├── api/
│   │   │   ├── permissions.py
│   │   │   ├── serializers.py
│   │   │   ├── urls.py
│   │   │   └── views.py
│   │   ├── persistence/
│   │   │   ├── repositories.py
│   │   │   └── unit_of_work.py
│   │   └── source_data/csv_source.py
│   ├── management/commands/
│   │   ├── initialize_location_config.py
│   │   ├── verify_location_reference_ready.py
│   │   └── seed_locations.py
│   └── migrations/0001_initial.py
├── identity/ports/authorization.py
├── identity/application/authorization.py
├── audit/ports/recording.py
├── audit/domain/records.py
├── config/composition.py
├── config/settings.py
└── config/urls.py

backend/tests/
├── unit/locations/
├── integration/api/locations/
├── integration/postgres/locations/
├── contract/locations/
└── architecture/

frontend/src/
├── app/locations/page.tsx
├── app/config/page.tsx
├── app/holidays/page.tsx
├── features/locations/
│   ├── api/location-api.ts
│   ├── model/
│   └── ui/
└── shared/api/
    ├── schema.ts            # generated
    └── client.ts            # existing handwritten thin transport wrapper
```

**Structure Decision**: Add one cohesive Django app named `locations`, matching the
approved QUY_TAC module name and keeping Config/Holiday beside the location policies they
configure. Django-required command and model shims remain thin; business behavior stays in
application/domain layers. Frontend code is one `features/locations` slice with three pages,
not three competing business modules.

## Domain Design

### Pure value types and rules

- `LocationKind`: exactly `BUSINESS_CENTER`, `SHOP`.
- `LocationValidationResult`: exactly `INSIDE_GEOFENCE`, `OUTSIDE_GEOFENCE`.
- `ValidatedPosition`: finite latitude `[-90, 90]`, longitude `[-180, 180]`, and
  `accuracy_m >= 0`; construction occurs only after API/source boundary validation.
- `haversine_distance_m(a, b)`: standard mean Earth radius `6_371_008.8 m`, pure and
  database-free. Decimal coordinates convert only at the calculation boundary.
- `classify_geofence(distance_m, radius_m)`: inside iff `distance_m <= radius_m`; it has
  no `accuracy_m` parameter.
- `detect_overlaps(candidate, others)`: overlap iff center distance is less than or equal
  to the sum of effective radii. It produces warnings and never rejects or merges data.
- Config candidate validation enforces every numeric, ordering, shift, grace, timezone,
  and weekday invariant in one pure pass.

Warning values are closed transport/domain values:

- `GEOFENCE_OVERLAP`, optionally listing related Location ids/codes but never coordinates;
- `RADIUS_BELOW_ATTENDANCE_ACCURACY`, with configured threshold/radius values.

Warnings are recomputed results, not persistent entities or DB constraints.

### Numeric representation

- Store latitude/longitude as `DecimalField(max_digits=18, decimal_places=15)` so the
  15-decimal center source values and all shop values persist without rounding.
- Store radii and accuracy thresholds as nonnegative decimal meter values with an explicit
  fixed scale; API serialization uses decimal strings, avoiding binary-float source drift.
- Haversine returns a finite float meter result; tests use declared tolerances rather than
  comparing transcendental results as exact decimals.

## Application Services and Ports

Application services:

- `LocationQueryService.list(filters)` returns all 76 authorized rows in stable
  `kind, code, id` order; no object-scope narrowing and no pagination.
- `LocationAdminService.update(actor, id, version, patch, reason)` locks Config then the
  target Location, rechecks version, validates the complete candidate, recomputes warnings,
  returns a same-value candidate as a no-write/no-evidence `200`, otherwise writes
  state/version/audit/outbox atomically, and returns candidate plus warnings.
- `ConfigQueryService.get()` returns the initialized singleton.
- `ConfigAdminService.update(actor, patch)` locks Config, overlays the patch on the current
  row, validates the complete candidate, rejects a maximum below any active/inactive
  Location radius, computes warning-only relationships, returns same-value candidates as
  no-write/no-evidence `200`, and otherwise writes state/audit/outbox atomically. It never
  rewrites Location radii.
- `HolidayService.list/create/delete` owns date uniqueness, target existence, row locking,
  and mutation evidence.
- `ConfigInitializationService.initialize(actor, complete_values)` is a controlled,
  attributable, one-time command use case; it rejects an existing singleton and incomplete
  values. No public Config-create endpoint exists.
- `LocationSeedService.seed(actor, parsed_sources)` validates both files before the UoW,
  locks Config then existing Locations, rejects any noncanonical identity, atomically
  inserts/reconciles all 76, and emits evidence only for rows actually inserted/changed.
- `ReferenceDataReadinessService.check()` is read-only and returns a failing result unless
  Config is complete and the canonical 76/7/69 code/hierarchy/source-coordinate state holds;
  its command never repairs state or appends evidence.

Ports:

- repository/query ports return framework-free snapshots and accept typed candidates;
- UoW port owns one caller `transaction.atomic()` and never commits evidence separately;
- source-data port exposes parsed center/shop rows and warning/error results without Django;
- Identity authorization gateway accepts a canonical `PermissionAction`, evaluates current
  action permission, then the forced-password account gate, and exposes no role checks to
  `locations`;
- Audit recorder remains the only append boundary. Its record types accept owner-defined
  closed `StrEnum` actions/events rather than an Identity-only enum; the adapter still
  sanitizes and joins the ambient caller transaction.

Ports do not expose Django models, raw JSON, coordinates in evidence payloads, or future
Attendance/Task types.

## Authorization Pipeline and Object Scope

Every protected API operation follows:

`DatabaseBackedJWTAuthentication → required action via injected Identity gateway →
must_change_password account gate → serializer/query/path validation → global object scope
→ business validation → UoW/constraint → audit/outbox`.

There is no body-independent target restriction for these resources and no owner scope:

| Operation | Action | DTO/filter after permission | Object scope | Mutation evidence |
|---|---|---|---|---|
| GET locations | `location.view` | kind/parent/is_active filters | Full 76-row directory | None |
| PATCH location | `location.manage` | path id, version, mutable fields, reason | Existing route target; global Manager scope | Location update audit/outbox |
| GET config | `config.view` | None | Singleton | None |
| PATCH config | `config.manage_attendance` | Config patch | Singleton | Config update audit/outbox |
| GET holidays | `holiday.manage` | None | Full holiday set | None |
| POST holiday | `holiday.manage` | date/name | Global | Holiday create audit/outbox |
| DELETE holiday | `holiday.manage` | path id after permission | Existing route target; global | Holiday delete audit/outbox |

Use string route converters so malformed ids do not bypass RBAC in URL resolution. Views
must not construct serializers before permission checks. `locations` contains no direct
`if role == ...`, does not import Identity models/domain/adapters, and does not trust
frontend capabilities.

After action/account gates, malformed/nonpositive route ids and nonexistent targets map to
the same `404 NOT_FOUND`. Location version is compared before same-value detection. A
current-version same-value Location or same-value Config PATCH returns `200` with current
warnings but skips persistence and evidence entirely.

## Persistence, Constraints, and Indexes

The detailed schema is in [data-model.md](data-model.md). Required database protections:

- Location unique/nonblank immutable code; closed kind; parent self-FK `PROTECT`; finite
  decimal range checks; positive radius; non-null active; version >= 1; indexes for
  `(kind, code)`, parent, and active filtering.
- Config primary key/check fixed to `1`; timezone fixed to `Asia/Ho_Chi_Minh`; finite and
  positive radius/threshold checks, default <= max, task-good <= task-low, nonnegative
  grace, and shift start < shift end. Domain/API validation rejects decimal `NaN` and
  infinities before comparisons, while PostgreSQL constraints reject non-finite direct
  writes. Weekday uniqueness/range remains a complete-candidate domain/API rule because
  cross-element JSON checks are not safely expressed as a portable constraint.
- Holiday unique date and nonblank name; stable date ordering.
- Cross-row rules—Location parent kind, radius <= Config maximum, overlap warnings, and
  exact table count—are enforced by the seed/service transaction and PostgreSQL tests, not
  fake single-row constraints.
- Config maximum validation covers active and inactive Locations under the Config lock;
  a violating Config candidate is rejected and no bulk radius rewrite exists.

No coordinate uniqueness or overlap exclusion constraint is added.

## Seed and Reference-Data Transaction

1. Thin command receives both canonical paths by default and requires an active Manager
   actor id; it delegates authorization through the Identity gateway.
2. CSV adapter strips an optional BOM, checks the exact per-file required-header set, and
   parses all rows using two immutable mappings. Center `STT` is ignored.
3. Before DB writes, reject missing headers, invalid decimals/ranges, duplicate code within
   or across files, or wrong 7/69 counts. A derived parent code absent from the seven centers
   is valid and produces a null parent.
4. Begin one UoW; lock singleton Config first, then all existing Location rows in stable id
   order. Config initialization is a deployment prerequisite.
5. Reject any database Location code outside the 76 canonical codes; do not delete or hide
   an unexpected row.
6. Insert missing canonical identities and reconcile changed rows by code. Parent ids are
   assigned only after all centers exist. Source strings are converted directly to Decimal;
   no float round-trip occurs.
7. Validate exact 7/69/76 state, active/default radius, hierarchy, and source coordinate
   equality; compute duplicate-coordinate and overlap warnings without blocking.
8. Append one sanitized audit/outbox pair per inserted or changed Location. Unchanged second
   run writes no Location/evidence/version and remains an idempotent no-op.
9. Commit all 76 state changes/evidence together; any validation, constraint, or evidence
   failure rolls back the full run. Command prints only counts/codes/warning categories—no
   precise coordinates.

## Transaction and Lock Matrix

All mutation paths use the same lock order to prevent deadlocks.

| Operation | Transaction/locks | Final invariant |
|---|---|---|
| Seed/reconcile | Begin; lock Config; lock all Locations ordered by id; insert/reconcile; evidence; commit | Exactly the canonical 76; no partial seed; unchanged rerun is no-op |
| Location update | Begin; lock Config; lock target Location; compare version; validate/warn; no-op without writes or save+version+evidence; commit | One version winner; same-value current version is evidence/version no-op; max evaluated against stable Config |
| Config update | Begin; lock Config; validate complete candidate; read all Locations; reject cap violation or no-op without writes, otherwise save+evidence; commit | One valid singleton; no Location radius exceeds max; no Location radii rewritten |
| Config initialize | Begin; authorize; ensure no row; insert pk=1+evidence; commit | At most one complete singleton |
| Holiday create | Begin; insert under unique date; evidence; commit | At most one Holiday per date; duplicate leaves no evidence |
| Holiday delete | Begin; lock target Holiday; append evidence; delete; commit | Existing target deleted once with attributable evidence |

Location update vs Location update, seed, or Config update is proven with real competing
connections. Serializing these rare writes on Config is intentional at 76-row scale and
prevents a radius from being accepted against a Config version that commits concurrently.
Reads remain lock-free.

## Audit and Outbox

Closed actions/events:

- `locations.location.seeded`, `locations.location.reconciled`,
  `locations.location.updated`;
- `locations.config.initialized`, `locations.config.updated`;
- `locations.holiday.created`, `locations.holiday.deleted`.

Rules:

- HTTP mutations use authenticated actor; controlled initialization/seed commands require
  an existing active Manager actor and the same canonical action authorization.
- Location before/after excludes latitude/longitude. It records non-sensitive changed
  fields, version, warning categories, and optional reason; a coordinate change is recorded
  only as a changed-field name.
- Outbox payloads contain aggregate id, version/action, and minimal changed-field metadata;
  never exact coordinates, address prose unnecessary to a consumer, tokens, URLs, or UI
  messages.
- Existing aggregate row locks protect `MAX(aggregate_version)+1`. Newly inserted
  Location/Config/Holiday rows are inserted before aggregate version 1. Holiday deletion
  uses its immutable row id as aggregate id, so delete/recreate by date is a new aggregate.
- Denied, invalid, stale, missing-target, duplicate-date, unchanged seed, and rollback paths
  append no success evidence.
- Current-version same-value Location and same-value Config PATCH paths are successful no-ops
  and likewise append no evidence or aggregate-version increment.

## API and Error Contracts

Exact request/response shapes are in [contracts/api.md](contracts/api.md).

- Locations list is unpaginated and stably ordered because R-103 approved page pagination
  only for Users and the set is fixed at 76.
- Decimal coordinates/radii serialize as strings; generated schema examples omit exact
  coordinates.
- PATCH Location accepts required `version`, optional mutable fields and optional `reason`;
  code/kind/parent/id and other unknown/server-owned fields return
  `400 SERVER_OWNED_FIELD` after permission.
- Stale version returns `409 LOCATION_VERSION_CONFLICT`; details return current version and
  the submitted reason, but no current coordinates. It never auto-retries.
- Current-version same-value Location PATCH and same-value Config PATCH return `200` without
  save/evidence/version; lowering Config maximum below any Location radius returns
  `400 VALIDATION_FAILED` with safe id/code details and no rewrite.
- Invalid fields/filters and duplicate Holiday date use `400 VALIDATION_FAILED` with the
  canonical envelope. Missing targets are `404 NOT_FOUND` through the canonical handler.
- Extend the centralized error registry/message map with spec-approved
  `LOCATION_VERSION_CONFLICT` and the canonical-envelope `NOT_FOUND` mapping; do not create
  a Location-local error renderer or bypass the shared handler.
- Authentication/account/action precedence retains `INVALID_TOKEN`, `ACCOUNT_INACTIVE`,
  `PERMISSION_DENIED`, and `PASSWORD_CHANGE_REQUIRED` from Feature 002.
- Malformed/nonpositive and nonexistent Location/Holiday route ids both return
  `404 NOT_FOUND` after action/account gates. Every Feature 003 response is private/no-store,
  and error `request_id` matches `X-Request-Id`.
- There is no geofence-evaluation endpoint, Config-create endpoint, Config version conflict,
  Location POST/DELETE, or Attendance/Task path.

## Frontend Integration

- Regenerate `contracts/openapi.yaml` and generated
  `frontend/src/shared/api/schema.ts`; do not hand-edit either.
- Keep `frontend/src/shared/api/client.ts` as the existing thin authenticated transport.
- Add typed wrappers under `features/locations/api/location-api.ts`; all calls use
  `apiClient`/`authenticatedFetch` and current account state.
- Location page is readable for all three roles and shows stable code/name/kind/parent,
  address, coordinates, radius, active state, and version. Only capability
  `location.manage` reveals edit controls; the backend remains authoritative.
- On `LOCATION_VERSION_CONFLICT`, retain the reason and draft, refresh the server record,
  and require explicit resubmission—never silently overwrite.
- Config page is readable for all roles; only `config.manage_attendance` reveals edit
  controls. Warnings remain visible but do not appear as failed saves.
- Holiday page is only presented with `holiday.manage`; list/create/delete failures still
  rely on backend authorization.
- No map SDK, reverse geocoder, continuous tracking, GPS collection, Attendance UI, or Task
  UI is introduced.

## Migrations and Compatibility

- Add `locations` to installed apps and package/mypy/maintainability paths.
- Create one additive `locations.0001_initial` for Location, Config, Holiday, constraints,
  indexes, and the immutable-code trigger. Existing identity/audit/operations migrations
  are not edited.
- New tables are backward-compatible with the N-1 application because old processes do not
  reference them. No destructive contract operation is scheduled.
- Do not insert Config or source Locations in schema migration: shift/grace values have no
  canonical product defaults. Deployment runs the attributable Config initialization
  command, then the seed command, then the read-only R-117 readiness command before enabling
  Feature 003 routes/UI. A failed readiness exit blocks enablement and never repairs state.
- The readiness application service depends on typed repository/source ports. Its concrete
  adapters are wired only in `backend/config/composition.py`; the management command resolves
  that composed use case and MUST NOT construct or import concrete persistence adapters.
- Because provider-specific IaC remains deferred, the executable enablement boundary is the
  nonzero-exit readiness management command plus the operator rollout sequence in
  `docs/TRIEN_KHAI.md`. A contract test pins the order `migrate → initialize → seed →
  readiness → enable`; no release procedure may describe route/UI enablement before a
  successful readiness result.
- Migration checker must report one leaf and no unsafe contraction. PostgreSQL migration
  tests prove constraints, trigger behavior, N-1 graph compatibility, and AuditLog FK
  compatibility.

## Test Strategy

Tests precede the implementation they constrain.

### Pure unit/domain

- exact two-value enums and closed warning values;
- exact seven-value Feature 003 event vocabulary and rejection of unknown values;
- GPS finite/range boundaries including NaN/infinities/poles/antimeridian;
- known Haversine distances, symmetry, zero distance, antimeridian, boundary tolerance;
- exact-radius inside and immediately-outside classification with no accuracy parameter;
- Config complete-candidate validation for `NaN`/positive and negative infinity, every
  finite numeric invariant, and every warning-only combination;
- CSV mapping/header/BOM/decimal parsing, parent derivation, duplicate code/coordinates,
  exact 7/69 counts, and no float round-trip.

### Application/service

- query filters and stable ordering;
- Location update candidate/immutable-field/version/warning behavior;
- Location/Config same-value no-op and stale-before-no-op ordering;
- Config singleton update, maximum-below-active/inactive rejection, and no Location rewrite;
- Holiday create/delete and missing target;
- seed first run, unchanged rerun, drift reconciliation, extra identity rejection;
- authorization/DTO/business ordering via substitute ports;
- audit/outbox record vocabulary and coordinate-free payload construction.

### PostgreSQL integration

- all Location/Config/Holiday constraints, indexes, FK deletion policies, and code trigger,
  explicitly including Location name/address nonblank and `is_active` NOT NULL/default;
- exact coordinate persistence including all 15-decimal source values;
- seed atomic rollback, exact 76/7/69, two-run no-op, duplicate coordinate acceptance,
  duplicate code failure, unexpected 77th identity failure;
- state+AuditLog+OutboxEvent rollback when either recorder fails;
- aggregate version allocation while Location/Config/Holiday rows are locked;
- unique Holiday date under concurrent create;
- concurrent same-version Location updates; update vs seed; update vs Config maximum change;
- concurrent different-Location updates serialized through Config, with independent versions;
- singleton concurrent initialization; one row only;
- real threads/connections with `django_db(transaction=True)`, barriers, persisted-state
  assertions, and no lock mocks/SQLite claims.

### API contract/integration

- role/action allow/deny matrix and malformed-body/filter precedence;
- inactive/forced-password behavior inherited from Identity gateway;
- server-owned fields, malformed ids, nonexistent targets, invalid filters/coordinates,
  invalid Config, duplicate Holiday date, and no forbidden persistence/evidence;
- stale Location error shape/reason retention and warning success shapes;
- confirm Location POST/DELETE and geofence/Attendance/Task endpoints do not exist;
- malformed/nonpositive vs nonexistent target equivalence after authorization, Holiday
  inactive/forced-password gates, private/no-store on every outcome, and request-id/header
  equality;
- no precise coordinate values in schema examples, audit, outbox, or logs;
- deterministic OpenAPI/schema generation and compatibility checks.

### Architecture/frontend

- `locations.domain` remains Django/DRF-free;
- `locations` does not import Identity/Audit models, domain, or adapters and contains no
  Attendance/Task workflow helpers;
- Identity/Audit integration crosses public ports only; config is late composition;
- generated `schema.ts` vs handwritten `client.ts` boundary;
- all-role Location/Config read presentation, Manager-only controls, Holiday capability
  presentation, warning display, and stale-draft preservation;
- no token storage regression and no frontend-only authorization trust.

## PostgreSQL Race Matrix

| Race | Rows locked / order | Expected serialization | Final assertion |
|---|---|---|---|
| Location update vs same Location update | Config → target Location | One version wins; follower sees incremented version | One state/evidence pair; loser 409/no evidence |
| Location update vs different Location update | Same Config → each target | Serialize on Config | Both valid commits in lock order; versions independent |
| Location update vs Config update | Same Config → optional Location | Config order defines which radius/threshold candidate is evaluated | No Location exceeds committed max; warning reflects serialized state |
| Location update vs seed | Same Config → Locations | Seed or update linearizes first | Seed-last restores source; update-last applies valid versioned edit; table stays 76 |
| Seed vs seed | Same Config → all Locations | Second begins after first commit | One canonical 76 set; unchanged follower writes no evidence |
| Holiday create vs same date | Unique date insertion | Constraint selects one winner | One row and one create evidence pair |
| Holiday delete vs delete | Same Holiday row | First deletes; follower observes missing target | One deletion/evidence pair |
| Config initialize vs initialize | Singleton PK/check/unique insertion | Constraint selects one winner | Exactly one complete Config and one evidence pair |
| Per-aggregate evidence allocation | Aggregate row lock held through append | `MAX+1` occurs serially | Unique consecutive versions, no gaps from rollback |
| Same-value PATCH vs mutation | Config → relevant Location | Lock order decides observed candidate | No-op produces no evidence/version; real mutation produces exactly one pair |

## CI and Verification

Reuse `.github/workflows/quality.yml`, `.github/workflows/contract.yml`, and
`scripts/check_all.sh`; add the `locations` paths/test suites to existing commands rather
than creating a workflow or service. Required gates are Ruff format/lint, strict mypy,
maintainability, unit/architecture/contract/API tests, PostgreSQL integration/races,
OpenAPI safety/drift/compatibility, generated frontend schema drift, migration checker,
frontend format/lint/type/test/build, and deterministic seed verification.

Do not make wall-clock p95 or two-minute usability assertions in CI. Reuse the existing
operator evidence pattern for measured capacity/usability and record actual measurements
only after implementation.

## Implementation Dependency Order

1. Freeze synchronized R-113–R-117/spec/contracts; add tests for prohibited Location create,
   same-value semantics, maximum-cap rejection, route-id precedence, and readiness.
2. Add pure domain value types, GPS/Haversine/geofence and Config tests, then rules.
3. Generalize Audit public record types and add Identity authorization gateway contract
   tests without changing Feature 002 behavior.
4. Add Location/Config/Holiday model and migration tests, then additive migration/models.
5. Add repository/UoW port tests, then persistence adapters.
6. Add CSV source tests, then separate source mappings/parser.
7. Add seed and Config initialization tests, then services and thin commands.
8. Add Location/Config/Holiday application tests, then mutation/query services.
9. Add PostgreSQL rollback/constraint/race tests, then locking and evidence integration.
10. Add API precedence/contract tests, then serializers/permissions/views/URLs.
11. Wire concrete adapters in `config/composition.py` only after all dependencies exist.
12. Regenerate OpenAPI and `schema.ts`; add handwritten feature API wrapper.
13. Add frontend pages/state/tests for Location, Config, and Holiday.
14. Add read-only readiness tests and service/command, wire it through the late composition
    root, then pin the fail-closed operator rollout sequence before route/UI enablement.
15. Run architecture, migration, contract drift, full PostgreSQL, frontend, and quickstart
    verification; record non-CI usability/performance evidence separately.

## Complexity Tracking

No Constitution violation or additional infrastructure is required.
