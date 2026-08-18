# Feature Specification: Location, Geofence, Configuration and Reference Data

**Feature Branch**: `feature/003-location-config`

**Created**: 2026-08-18

**Status**: Ready for Implementation after remediation re-audit

**Input**: User description: "Location model and RBAC reads/updates; deterministic seed of 7 business centers and 69 shops from two separately mapped CSV files; GPS validation and haversine geofence classification; singleton attendance/task location configuration; and canonical Holiday management. Attendance and task workflows are excluded."

## Clarifications

### Session 2026-08-18

- Q: Is the 76-location requirement a seed-cohort count or the complete Location set? → A: R-113 makes it the complete, closed set: exactly 7 `BUSINESS_CENTER`, 69 `SHOP`, and 76 total records; Feature 003 has no Location-create operation.
- Q: What does an idempotent rerun do after an authorized Location edit? → A: R-113 preserves CSV/config authority: rerun restores source-controlled identity, display, hierarchy, coordinates, initial radius, and active state by immutable code without creating a 77th record.
- Q: Does Config use optimistic versioning in this feature? → A: No. Optimistic versioning and stale-conflict behavior are required only for `Location`; Config remains a singleton protected by atomic validation and persistence.
- Q: What happens when Config maximum radius is lowered below an existing Location? → A: R-114 rejects the entire update for active or inactive Locations; it never rewrites Location radii.
- Q: What happens when Location/Config PATCH supplies mutable fields but changes no state? → A: R-115 returns an idempotent `200` no-op with no save, audit, outbox, or version advance; Location stale-version comparison still wins first.
- Q: How are malformed Feature 003 route ids handled? → A: R-116 runs authorization/account gates first, then returns the same `404 NOT_FOUND` used for a nonexistent target.
- Q: How is the post-migration empty reference-data window prevented from serving traffic? → A: R-117 requires a read-only fail-closed readiness gate proving one complete Config and canonical 76/7/69 data before routes/UI are enabled.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Establish trusted location reference data (Priority: P1)

An operator initializes the system from the two approved location files and receives a complete, repeatable set of business centers and shops without losing legitimate duplicate coordinates.

**Why this priority**: Location identity and coordinates are the source of truth for every later location-aware workflow.

**Independent Test**: Run the seed twice and verify that both runs end with exactly the same 76 total locations, values, hierarchy, coordinates, radii, and active state.

**Acceptance Scenarios**:

1. **Given** the approved center and shop files, **When** the seed completes, **Then** the complete Location set contains exactly 7 `BUSINESS_CENTER` records, exactly 69 `SHOP` records, and exactly 76 records in total.
2. **Given** the center file uses `Mã TTKD` and `Tên` while the shop file uses `SHOP_CODE` and `NAME`, **When** either file is validated, **Then** its own explicit header mapping is required before any row is processed.
3. **Given** a required header is missing, **When** validation runs, **Then** the operation stops before seeding and identifies the affected file and missing column.
4. **Given** a shop code, **When** its parent is derived, **Then** the system uses `SHOP_CODE[:5] + '0000'`; an unmatched derived code leaves the parent empty rather than guessing from name, address, or distance.
5. **Given** `HCM000079` and `HCM010005` share the same coordinates, **When** seeding completes, **Then** both remain distinct valid locations.
6. **Given** a duplicate location code within the input or existing reference set, **When** seeding is attempted, **Then** the operation fails and does not leave a partial seed.
7. **Given** a Manager changed mutable fields on a Location, **When** the seed reruns successfully, **Then** that record is restored to the approved source values, derived hierarchy, configured initial radius, and active state without creating or deleting a Location identity.

---

### User Story 2 - View and safely maintain locations (Priority: P1)

Authorized users can view the location directory, while a Manager can update an existing location without overwriting a newer change or treating geofence overlap as invalid data.

**Why this priority**: Users need accurate location reference data, and Managers need safe maintenance before later attendance and field-evidence workflows can consume it.

**Independent Test**: Exercise location list and update operations as each canonical role, including stale-version, immutable-code, invalid-radius, duplicate-coordinate, and overlap cases, and verify that no create operation exists.

**Acceptance Scenarios**:

1. **Given** a Leader, Manager, or Helpdesk user, **When** the user lists locations, **Then** the directory is visible and can be filtered by kind, parent, and active state.
2. **Given** a non-Manager, **When** the user attempts to update a location, **Then** access is denied before request-field validation and no state or success audit evidence is created.
3. **Given** a Manager and the current location version, **When** the Manager updates an allowed field, **Then** the change is saved, the version increases, and attributable audit evidence is recorded.
4. **Given** a Manager submits an older location version, **When** the update is attempted, **Then** the system returns `409 LOCATION_VERSION_CONFLICT` and preserves the newer location unchanged.
5. **Given** valid coordinates matching another location or a geofence overlapping another geofence, **When** a Manager saves the location, **Then** the save succeeds and returns a warning rather than an error.
6. **Given** a radius below the attendance accuracy threshold but otherwise valid, **When** a Manager saves the location, **Then** the save succeeds with a clear operational warning.
7. **Given** any caller, **When** a Location-create operation is attempted, **Then** no such business operation is available and the 76-record identity set remains unchanged.
8. **Given** a Manager submits an update reason and an older location version, **When** the update conflicts, **Then** the server preserves the client-entered reason in the conflict response so it can be reviewed and resubmitted after refresh.
9. **Given** a Manager submits the current version and at least one mutable field whose value already matches the Location, **When** the update is evaluated, **Then** it returns `200` with current warnings but does not save, increment either version, or create audit/outbox evidence.

---

### User Story 3 - Validate GPS and classify geofence membership (Priority: P1)

Later business workflows can submit a validated GPS position to a shared location rule and receive an unambiguous inside/outside result based on distance and the selected location's configured radius.

**Why this priority**: A correct, deterministic location rule is the prerequisite for both attendance and task evidence, while keeping their distinct quality policies out of this feature.

**Independent Test**: Validate boundary and non-finite GPS values, verify known haversine distances, and classify positions immediately inside, exactly on, and immediately outside a radius.

**Acceptance Scenarios**:

1. **Given** finite latitude, longitude, and non-negative accuracy, **When** GPS input is validated, **Then** it is accepted for geometry evaluation.
2. **Given** `NaN`, positive or negative infinity, latitude outside `[-90, 90]`, longitude outside `[-180, 180]`, or negative accuracy, **When** GPS input is validated, **Then** it is rejected before distance or geofence calculation.
3. **Given** a validated point and location center, **When** distance is calculated, **Then** haversine distance is returned in meters with verified boundary accuracy.
4. **Given** `distance_m <= radius_m`, **When** membership is classified, **Then** the result is `INSIDE_GEOFENCE`; given `distance_m > radius_m`, the result is `OUTSIDE_GEOFENCE`.
5. **Given** any GPS accuracy value, **When** membership is classified, **Then** accuracy does not enlarge, shrink, or otherwise alter the radius comparison, and no `UNCERTAIN` result is possible.

---

### User Story 4 - Manage shared operating configuration (Priority: P2)

All authenticated roles can read the single operating configuration needed to present consistent shift and GPS guidance, while only a Manager can change it within the approved invariants.

**Why this priority**: Central configuration prevents thresholds and calendars from drifting across later business workflows.

**Independent Test**: Read and update the singleton as each role, exercising every numeric, ordering, radius, shift, grace-period, threshold, and weekday validation boundary.

**Acceptance Scenarios**:

1. **Given** any authenticated canonical role, **When** configuration is read, **Then** the singleton configuration is returned.
2. **Given** a Leader or Helpdesk user, **When** configuration update is attempted, **Then** access is denied before payload validation and no state changes.
3. **Given** a Manager submits values satisfying all invariants, **When** configuration is updated, **Then** the same singleton is changed and attributable audit evidence is recorded.
4. **Given** an invalid radius, accuracy threshold ordering, negative grace period, overnight/equal shift boundary, or invalid weekday set, **When** update is attempted, **Then** the entire update is rejected with field-specific feedback.
5. **Given** any invalid partial configuration candidate, **When** an update is attempted, **Then** no field is partially committed and the previously valid singleton remains readable.
6. **Given** any active or inactive Location whose radius exceeds a proposed Config maximum, **When** a Manager lowers `max_radius_m`, **Then** the entire update is rejected with safe Location identifiers and no Location rewrite or evidence.
7. **Given** a Config PATCH whose complete candidate equals current state, **When** it is evaluated, **Then** it returns `200` with current warnings and creates no write, evidence, or aggregate-version advance.

---

### User Story 5 - Maintain holidays under canonical RBAC (Priority: P3)

A Manager can list, add, and remove manually maintained holidays used by configuration and reporting, while other roles cannot access holiday management.

**Why this priority**: Holidays are necessary reference data for later reporting but do not block the core location and geofence capability.

**Independent Test**: Exercise holiday list, create, duplicate-date, and delete behavior as Manager, Leader, and Helpdesk without invoking any attendance workflow.

**Acceptance Scenarios**:

1. **Given** a Manager, **When** holidays are listed, added, or removed, **Then** the operation succeeds and each mutation records attributable audit evidence.
2. **Given** an existing holiday date, **When** a Manager adds another holiday for that date, **Then** the request is rejected and the existing holiday remains unchanged.
3. **Given** a Leader or Helpdesk user, **When** any holiday operation is attempted, **Then** access is denied before payload validation and no state changes.
4. **Given** a valid date with no holiday, **When** no Manager adds one, **Then** the system does not generate a holiday automatically.

### Edge Cases

- A CSV is empty, has a byte-order marker, contains a required header with a misspelling, has an invalid numeric coordinate, has a duplicate code across the two files, or produces a count other than 7 centers and 69 shops.
- A Location was edited after initialization; a successful rerun intentionally restores its approved source/config-controlled values without changing the 76 business identities.
- A center contains the presentational `STT` column; it is ignored and never becomes location identity.
- A shop's derived parent code does not exist; the shop remains valid with no parent. `HCM000079` is the current expected example.
- A location shares its address and coordinates with another, or several geofences overlap; identity remains code-based and warnings never merge or reject the records.
- A point is exactly at a pole, on the antimeridian, at zero distance, exactly on the radius boundary, or on opposite sides of the antimeridian.
- Zero radius, radius above the configured maximum, non-finite configuration values, reversed shift times, duplicate weekdays, or weekday values outside `0` through `6` are rejected.
- Concurrent Managers edit the same location from the same starting version; only one update may succeed, and the other receives the version conflict.
- A client attempts to create a new Location or change code, kind, parent, or version; the fixed identity/hierarchy remains unchanged.
- A holiday deletion targets a missing record; the response reports that the target does not exist and creates no mutation audit evidence.

## Requirements *(mandatory)*

### Functional Requirements

#### Location and Seed Data

- **FR-001**: The system MUST represent each business center or shop as one `Location` with code, name, `LocationKind`, optional parent, address, latitude, longitude, effective radius in meters, non-null active state, and monotonic optimistic version.
- **FR-002**: `LocationKind` MUST be closed to exactly `BUSINESS_CENTER` and `SHOP`.
- **FR-003**: Location code MUST be the immutable, globally unique business identity. Duplicate code, including a concurrent create collision, MUST be rejected by the final persistence boundary; duplicate address or coordinates MUST remain valid.
- **FR-004**: The approved seed MUST consume `docs/dia_chi_ttkd.csv` and `docs/dia_chi_cua_hang.csv` through separate explicit mappings: center `Mã TTKD`/`Tên` and shop `SHOP_CODE`/`NAME`, with each file's `ADDRESS`, `LATITUDE`, and `LONGITUDE`; center `STT` MUST be ignored.
- **FR-005**: Each source file's required headers MUST be validated before its first data row. A missing header MUST stop the seed with an error naming the file and missing column.
- **FR-006**: The seed MUST preserve source code, name, address, latitude, and longitude values without rounding, coordinate correction, merging, or inference from display strings.
- **FR-007**: Seeded centers MUST have kind `BUSINESS_CENTER` and no parent. Seeded shops MUST have kind `SHOP` and derive parent code only as `SHOP_CODE[:5] + '0000'`; a missing derived center MUST leave parent empty.
- **FR-008**: Every seeded location MUST start active and use the singleton configuration's default radius, which defaults to 50 meters and MUST NOT exceed the configured maximum radius, which defaults to 70 meters.
- **FR-009**: A successful seed MUST atomically establish the complete Location set as exactly 7 centers, 69 shops, and 76 total records. Any invalid row, duplicate code, invalid configuration/radius, source-count mismatch, or pre-existing non-source Location identity MUST prevent a partial or 77-record result.
- **FR-010**: Re-running the seed MUST use immutable location code as identity, MUST NOT create or delete business identities, and MUST reconcile every record to its approved code, name, address, exact coordinates, kind, derived parent, singleton default radius, and active state. It MUST end with the same 76 identities and values.
- **FR-011**: Seed and maintenance validation MUST treat coincident coordinates and overlapping geofences as valid. Overlap MUST produce warnings only and MUST NOT merge locations or block persistence.

#### Location Access and Maintenance

- **FR-012**: The location directory MUST require `location.view`, granted directly to Leader, Manager, and Helpdesk, MUST expose the full authorized directory without role- or ownership-based object narrowing, and MUST support optional filters for kind, parent, and active state.
- **FR-013**: Location update MUST require `location.manage`, granted only to Manager; permission denial MUST precede input validation. This feature MUST NOT expose a Location-create or Location-delete business operation.
- **FR-014**: The closed Location identity and hierarchy MUST come only from the canonical seed. Code, kind, and parent MUST NOT be client-changeable, and no request may create a 77th Location.
- **FR-015**: Location update MUST allow only name, address, coordinates, radius, and active state. Code, kind, parent, and server-owned version progression MUST remain immutable through maintenance operations.
- **FR-016**: Every location update MUST require and atomically compare the current version before no-op detection. A state-changing success MUST increment Location version exactly once; a same-value candidate MUST return `200` with current warnings but perform no save, audit/outbox append, Location-version increment, or aggregate-version increment. A stale version MUST return `409 LOCATION_VERSION_CONFLICT` even when the candidate equals current state, with no mutation and with any submitted reason preserved for review; the server MUST NOT silently retry or apply last-write-wins behavior.
- **FR-017**: Location update MUST reject non-finite or out-of-range coordinates, non-positive radius, or radius above the singleton maximum. Radius below attendance accuracy threshold MUST warn but MUST NOT block an otherwise valid save.
- **FR-018**: State-changing successful Location updates MUST record immutable, attributable before/after audit evidence in the same unit of work, including the client-supplied reason when applicable and excluding precise coordinates from audit payloads. A same-value success under R-115 is explicitly a no-op and MUST create no audit/outbox evidence or version advance. Denied, invalid, stale, or rolled-back operations MUST create no success audit evidence.

#### GPS and Geofence Rules

- **FR-019**: GPS input validation MUST accept only finite latitude in `[-90, 90]`, finite longitude in `[-180, 180]`, and finite `accuracy_m >= 0`, and MUST reject invalid input before haversine or geofence evaluation.
- **FR-020**: The system MUST calculate great-circle distance between two validated coordinate pairs using the haversine rule and express the result in meters.
- **FR-021**: `LocationValidationResult` MUST contain exactly `INSIDE_GEOFENCE` and `OUTSIDE_GEOFENCE`; `UNCERTAIN` or any equivalent third membership state MUST NOT exist.
- **FR-022**: Geofence classification MUST return `INSIDE_GEOFENCE` exactly when `distance_m <= radius_m`, otherwise `OUTSIDE_GEOFENCE`.
- **FR-023**: Measurement quality and geofence membership MUST remain independent. Geofence classification MUST NOT consume `accuracy_m`, and accuracy MUST never be added to or subtracted from radius or distance.
- **FR-024**: This feature MUST expose validated GPS and geofence rules for later consumers but MUST NOT decide attendance acceptance, task completion, location-candidate choice, or workflow-specific GPS quality outcomes.

#### Singleton Configuration

- **FR-025**: The system MUST maintain exactly one operating `Config`, identified as the singleton record, containing timezone, working weekdays, default and maximum radius, attendance accuracy threshold, task good/low accuracy thresholds, shift start/end, late check-in, early-checkout, and late-checkout grace periods.
- **FR-026**: The singleton timezone MUST be `Asia/Ho_Chi_Minh`; working weekdays MUST default to Monday through Saturday (`[0,1,2,3,4,5]`) and, when changed, MUST be a duplicate-free subset of integers `0` through `6`.
- **FR-027**: Configuration defaults MUST include `default_radius_m = 50`, `max_radius_m = 70`, `max_attendance_accuracy_m = 25`, `task_gps_good_accuracy_m = 25`, `task_gps_low_accuracy_m = 100`, and `late_checkout_grace_minutes = 60`. Shift start/end and all grace-period values MUST be present and valid before the singleton is usable; no incomplete configuration may become readable.
- **FR-028**: Config validation MUST require every meter-valued radius and accuracy threshold to be finite and positive; `default_radius_m <= max_radius_m`; task-good no greater than task-low; all grace periods to be integers at least zero; and `shift_start < shift_end` so an overnight shift is invalid. `NaN`, positive infinity, and negative infinity MUST be rejected before comparison or persistence.
- **FR-029**: Configuration read MUST require `config.view`, granted directly to all three roles. Configuration update MUST separately require `config.manage_attendance`, granted only to Manager; neither action implies the other.
- **FR-030**: Configuration update MUST modify the singleton rather than create another record, validate the complete resulting configuration atomically, and never apply a partial change. A state-changing success MUST record attributable audit/event evidence. A same-value complete candidate MUST return `200` with current warnings but perform no save, audit/outbox append, or aggregate-version advance. Every failure MUST leave the prior singleton unchanged.
- **FR-031**: If a configuration change makes one or more active location radii lower than the attendance accuracy threshold, the update MUST remain permitted and return a clear warning; it MUST NOT rewrite location radii.
- **FR-032**: Attendance and task GPS thresholds MUST remain separately named and independently changeable; this feature MUST NOT cross-use or combine them.

#### Holiday Reference Data and Contracts

- **FR-033**: `Holiday` MUST contain a unique date and a display name, MUST be entered manually, and MUST never be generated automatically.
- **FR-034**: Holiday list, creation, and deletion MUST all require `holiday.manage`, granted only to Manager, with no additional per-owner or per-business-unit object scope. A duplicate date, including a concurrent create collision, MUST be rejected by the final persistence boundary without changing the existing holiday.
- **FR-035**: Successful holiday creation and deletion MUST record immutable, attributable audit evidence; denied, invalid, missing-target, and rolled-back attempts MUST not create success evidence.
- **FR-036**: Working weekdays and holidays in this feature MUST serve configuration and future reporting reference needs only; no attendance job, attendance validation, or task workflow behavior may be introduced.
- **FR-037**: The business contract MUST provide: filtered location list at `GET /api/v1/locations/`; optimistic location update at `PATCH /api/v1/locations/{id}/`; singleton read/update at `GET` and `PATCH /api/v1/config/` with method-specific actions; and holiday list/create/delete at `GET`/`POST /api/v1/holidays/` and `DELETE /api/v1/holidays/{id}/`. `POST /api/v1/locations/` and Location deletion MUST NOT exist.
- **FR-038**: Every protected operation MUST follow canonical ordering: authentication, action permission, body-independent target authorization, account gate, input validation, object/business invariants, atomic persistence, then audit/event evidence.
- **FR-039**: Verification MUST cover exact 76/7/69 total counts and source preservation, separate header mappings, missing headers, two-run idempotency, duplicate-code rejection, duplicate-coordinate acceptance, overlap warnings, parent derivation, GPS input boundaries, haversine/geofence boundaries, the two-value result vocabulary, independent quality/radius behavior, all configuration invariants, RBAC allow/deny precedence, holiday uniqueness, absence of Location creation, and stale Location-version concurrency.
- **FR-040**: Each state-changing successful Location update, Config update, or Holiday mutation MUST commit its business-state change, immutable Audit Record, and Outbox Event in one transaction. R-115 same-value Location/Config successes are no-ops and therefore commit no business write or evidence. A state-changing Location update MUST recompute overlap warnings from the candidate state within that same transaction. Any validation, authorization, concurrency, audit, event, or persistence failure MUST roll back the entire mutation.
- **FR-041**: Audit and outbox payloads MUST exclude precise coordinates and other prohibited sensitive values. Holiday create replay is bounded by its unique date and Location updates by optimistic version; this feature MUST NOT introduce a separate generic idempotency-key contract.
- **FR-042**: If a configuration change would make `max_radius_m` lower than the radius of any active or inactive Location, the update MUST fail atomically with `400 VALIDATION_FAILED`, identify violating Locations only by safe id/code, and MUST NOT rewrite Location state or create audit/outbox/version evidence. Equality with the greatest existing radius MUST remain valid.
- **FR-043**: After authentication, action RBAC, and account gating, malformed positive-id route input and a syntactically valid but nonexistent Location/Holiday target MUST both return `404 NOT_FOUND` without persistence or evidence; insufficient permission MUST still return `403 PERMISSION_DENIED` before id parsing.
- **FR-044**: Deployment MUST run a read-only fail-closed readiness check before enabling Feature 003 routes/UI. It MUST require exactly one complete Config and exactly 76 canonical Locations—7 centers and 69 shops—with matching codes, hierarchy, and source coordinates; it MUST return a failing exit status and MUST NOT mutate data when any condition is unmet.
- **FR-045**: Every Feature 003 API success, error, and conflict response MUST include `Cache-Control: private, no-store`; every canonical error body request id MUST match the server-generated `X-Request-Id` response header.

### Key Entities

- **Location**: One of the fixed 76 business centers or shops and its display data, source-derived hierarchy, exact source coordinates, effective geofence radius, active state, and optimistic version; code is its immutable business identity. A center is always parentless, while a shop may be parentless or reference one existing center.
- **LocationKind**: Closed classification of `BUSINESS_CENTER` or `SHOP`.
- **Validated Position**: Finite latitude, longitude, and non-negative measurement accuracy accepted for geometry; it carries no attendance or task decision.
- **Location Validation Result**: The two-state geofence membership outcome `INSIDE_GEOFENCE` or `OUTSIDE_GEOFENCE`.
- **Config**: The sole shared operating configuration for timezone, workweek, radii, independent attendance/task GPS thresholds, shift, and grace periods.
- **Holiday**: A manually maintained unique calendar date and display name used as reference data.
- **Location Warning**: Non-blocking evidence that geofences overlap or that radius is below the attendance accuracy threshold.
- **Audit Record**: Immutable evidence containing actor, target type, target identifier, action, sanitized before state, sanitized after state, optional reason, and creation time for an authorized successful Location, Config, or Holiday mutation.
- **Outbox Event**: Durable, sanitized evidence of the same successful mutation, committed atomically with business state and its Audit Record for later delivery.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Each successful seed run results in exactly 76 source-backed locations—7 centers and 69 shops—with 100% agreement on source codes and coordinates and no location lost because coordinates overlap.
- **SC-002**: Two consecutive seed runs produce the same 76 identities and hierarchy with zero duplicate records; every missing-header, duplicate-code, invalid-row, or count-mismatch test leaves zero partial-seed effects.
- **SC-003**: GPS validation rejects 100% of tested non-finite, out-of-range, and negative-accuracy inputs before geometry, while accepting all tested inclusive latitude/longitude boundaries and zero accuracy.
- **SC-004**: Geofence tests return the expected result for 100% of zero-distance, inside, exact-radius, and outside cases, expose exactly two result values, and show zero cases where accuracy changes membership.
- **SC-005**: Across the canonical role matrix, 100% of location/configuration/holiday reads and mutations match the required action decisions, and every unauthorized malformed request is denied before field-validation details are exposed.
- **SC-006**: Configuration tests reject 100% of non-finite or non-positive meter values, invalid radius/threshold ordering, grace-period, shift-ordering, and weekday cases without partial mutation, while all warning-only combinations remain saveable.
- **SC-007**: In every tested concurrent update pair starting from the same Location version, exactly one update succeeds and every stale update returns `409 LOCATION_VERSION_CONFLICT` without overwriting the committed change.
- **SC-008**: Every configuration validation test leaves either one complete valid singleton or the previous valid singleton, with zero partial-field updates and zero second Config rows.
- **SC-009**: A Manager can find a location, understand any warning, and complete an eligible location, configuration, or holiday maintenance task in under two minutes during acceptance testing.
- **SC-010**: The delivered feature contains zero Attendance records/workflows, zero Task records/workflows, zero workflow candidate selection, and zero holiday-driven attendance-job behavior.
- **SC-011**: Contract verification finds no Location-create/delete operation, and every readiness-enabled serving state contains exactly the canonical 76 Location identities. The intentional empty or incomplete pre-enable state after schema migration MUST fail the R-117 readiness gate rather than serve Feature 003 traffic.
- **SC-012**: All tested same-value Location/Config PATCH requests leave business and aggregate versions and AuditLog/OutboxEvent counts unchanged, while every stale Location version still conflicts.
- **SC-013**: Reference-data readiness returns success only for one complete Config and the canonical 76/7/69 dataset, returns failure for every tested incomplete/drifted state, and never repairs state itself.

## Assumptions

- The authority order is `docs/CHOT_YEU_CAU.md`, then `docs/QUY_TAC_CLEAN_CODE.md`, then stakeholder-facing PRD, then implementation; this specification follows the current CHOT and project constitution.
- R-113 resolves the former conflict in R-83: Feature 003 exposes Location list/read and optimistic update only; the complete Location identity set remains exactly 76 and has no create/delete operation. “Read” is satisfied by the filterable location directory because CHOT defines no separate location-detail operation.
- The existing Identity/RBAC feature supplies authentication, account-state gating, the closed canonical permission matrix, and ordered permission decisions. This feature consumes those decisions rather than defining new roles or implications.
- The existing project foundation supplies the versioned business-contract conventions, canonical errors, database-backed integration testing, correlation context, and sensitive-payload filtering.
- Seed idempotency means rerunning reconciles all 76 records to approved source/config values by immutable code, even when that replaces later mutable-field edits. There are no Manager-created Location identities outside the seed.
- Shift start/end and grace periods are required Config values. Exact deployment-specific values are supplied through the approved configuration initialization path; this feature validates them but does not invent new product defaults where CHOT defines none.
- Precise coordinates remain available to location-authorized users because they are necessary reference data, but they are excluded from audit/event/telemetry payloads under the project privacy rules.

## Dependencies

- Project Constitution Principles I, III, IV, V, VI, VII, X, XI, and XII, plus its Definition of Done.
- `docs/CHOT_YEU_CAU.md` §§2–4.3, §7 Location/Config/Holiday notes, §§8–8.3 canonical RBAC, §9.3 seed/calendar rules, and §10 management contracts and mandatory tests.
- `docs/QUY_TAC_CLEAN_CODE.md` location/GPS/configuration naming and verification rules.
- Feature `001-project-api-foundation` for shared contract, configuration, database-test, and delivery foundations.
- Feature `002-identity-auth-rbac` for canonical roles, permission actions, account gates, authorization order, and audit/outbox ownership.
- Approved source data: `docs/dia_chi_ttkd.csv` and `docs/dia_chi_cua_hang.csv`.

## Out of Scope

- Attendance check-in, checkout, session, anomaly, attempt, location-candidate selection, or weak-GPS workflow behavior.
- Task creation, assignment, update, field-evidence completion, task GPS quality outcome, location resolution, photo, or override workflows.
- Continuous location tracking, nearest-location auto-selection, reverse geocoding, map links, EXIF location extraction, or third-party location services.
- Reporting calculations, export, expected-workday calculation, or using working weekdays/Holidays to control an attendance job.
- Bulk location import beyond the two approved seed files, Location creation/deletion, automatic holiday generation, or additional location kinds/geofence result states.
