# Phase 0 Research: Location, Geofence, Configuration and Reference Data

## Authority and scope

**Decision**: Use CHOT §§2–4.3, §7–§8.3, §9.3–§9.4, §10; R-01, R-16,
R-21, R-82–R-83, R-99, R-103–R-104, and R-113–R-117; and the matching QUY_TAC
location/GPS/config rules as controlling authority.

**Rationale**: R-113 closes the only material contradiction by making the Location set
exactly 76 and removing API creation. The spec now matches the authority chain and has no
governance marker.

**Alternatives considered**:

- A 76-row CSV cohort plus Manager-created rows: rejected by R-113 and the exact-total DoD.
- Keeping `POST /locations/` from the superseded part of R-83: rejected because it permits
  a 77th identity.
- Adding Attendance/Task placeholders to exercise geofence: rejected because their object
  ownership and workflows belong to Features 004/006.

## Module ownership

**Decision**: Add one business app `locations` owning Location, Config, Holiday, seed, and
pure geometry. Use Identity and Audit only through public ports; compose concrete adapters
in `config`.

**Rationale**: QUY_TAC already names the `locations` module, and these reference entities
share one configuration and transaction policy. Three smaller apps would add composition
and migration boundaries without independent business ownership.

**Alternatives considered**:

- Put geofence in `core`: rejected because it is location business policy.
- Put Config/Holiday in `operations`: rejected because operations owns deployment/runtime
  support, not business reference data.
- Import Identity permission or Audit model adapters directly: rejected by Constitution II.

## Cross-module authorization

**Decision**: Expose a framework-neutral authorization gateway through
`identity.ports.authorization`. A local Location DRF permission adapter calls that gateway
with the canonical action; Identity evaluates action permission and then the forced-password
gate. The port may re-export canonical action/decision types but never User models or role
branching.

**Rationale**: Feature 002 owns generic action authorization, while a Feature 003 adapter
must not import `identity.domain` or `identity.adapters`. This also keeps RBAC before DTO
validation without duplicating the matrix.

**Alternatives considered**:

- Import `CanonicalIdentityPermission`: rejected as an adapter-to-adapter cross-module
  dependency.
- Copy role/action maps into `locations`: rejected as a second authorization source.
- Trust frontend capabilities: rejected because capabilities are presentation-only.

## Exact coordinate persistence

**Decision**: Parse source coordinates directly into Decimal and persist with
`DecimalField(max_digits=18, decimal_places=15)`. Serialize persisted decimal measurements
as strings. Convert to float only inside pure trigonometric calculation.

**Rationale**: The center CSV contains values with 15 fractional digits; a six-decimal
field or a float parse would violate source preservation. Eighteen digits cover longitude
through 180 plus 15 fractional digits.

**Alternatives considered**:

- FloatField: rejected because binary representation cannot prove exact source decimal
  preservation.
- Six decimal places: rejected because three center rows carry more precision.
- PostGIS/geography: rejected because no approved dependency/extension is needed for 76
  rows and pure Haversine.

## Haversine and overlap

**Decision**: Implement pure standard-library Haversine using mean Earth radius
`6_371_008.8 m`. Classify inside iff `distance_m <= radius_m`. Detect overlap when the
center distance is at most the sum of radii; warnings never block.

**Rationale**: The mean-radius constant is a standard deterministic technical choice;
transcendental results are tested with tolerance. The classifier intentionally accepts no
accuracy input, preserving the two independent gates.

**Alternatives considered**:

- `d + accuracy <= radius`, `d - accuracy`, or `UNCERTAIN`: rejected by CHOT §4.2.
- Nearest-location or business-context resolution: rejected and deferred to owning
  workflows.
- Geometry library: rejected as unnecessary dependency/infrastructure.

## Config initialization and mutation serialization

**Decision**: Create Config schema without a data row. A controlled, attributable command
initializes the complete singleton using explicit shift/grace values and approved numeric
defaults. All Location/Config writes lock Config first; Location writes then lock target
rows in stable order.

**Rationale**: CHOT has no approved defaults for shift start/end, late grace, or early
checkout grace, so a data migration must not invent them. Config-first locking gives a
single order for radius-cap validation, seed, and Config changes.

**Alternatives considered**:

- Invent migration defaults: rejected by source-of-truth governance.
- Allow a partially null Config: rejected by singleton completeness requirements.
- Add Config optimistic version: rejected because Feature 003 explicitly limits stale
  version semantics to Location.
- Read Config without a lock during Location mutation: rejected because a concurrent lower
  max radius could commit against the Location candidate.

## Config maximum and same-value PATCH

**Decision**: R-114 rejects a Config candidate whose maximum is below any active or inactive
Location radius, without rewriting Locations. R-115 treats current-state Location/Config
PATCH candidates as `200` no-ops with no persistence/evidence/version advance; Location
version comparison occurs first.

**Rationale**: This preserves the global maximum invariant without an unauthorized bulk
rewrite and prevents false audit/outbox history for unchanged state while retaining stale
client detection.

## Route identifiers and readiness

**Decision**: R-116 maps malformed/nonpositive and nonexistent Feature 003 target ids to the
same `404 NOT_FOUND` after action/account gates. R-117 adds a read-only deployment readiness
gate for one complete Config and canonical 76/7/69 reference data before routes/UI enable.

**Rationale**: String route converters preserve RBAC-before-validation. The readiness gate
closes the intentional empty-schema window without data migrations, invented shift defaults,
or mutation hidden inside health checking.

## Seed architecture and idempotency

**Decision**: A stdlib CSV adapter defines two immutable header maps, validates/parses both
files before the UoW, then an application seed service runs one transaction under the Config
lock. It rejects unexpected database identities, inserts missing rows, reconciles changed
source/config fields by code, and verifies exact 7/69/76 state before commit.

**Rationale**: Parsing before mutation provides header and numeric errors without partial
state. Config locking serializes seed against API writes. An unchanged second run produces
no writes or evidence; changed rows are restored as R-113 requires.

**Alternatives considered**:

- Shared fallback header lookup: rejected because it silently loses the seven centers.
- `update_or_create` without a complete preflight: rejected because partial writes and
  unexpected extra identities can escape.
- Delete unknown rows: rejected because destructive cleanup must not be inferred.
- Coordinate-based identity: rejected because the source contains a valid duplicate pair.

## Seed/config command attribution

**Decision**: Initialization and seed commands require an existing active Manager actor id
and invoke the same Identity authorization gateway as HTTP writes. Each inserted/changed
aggregate appends sanitized audit/outbox evidence; a no-op rerun appends none.

**Rationale**: Constitution VI and CHOT require attributable Location/Config changes, while
AuditLog.actor is non-null and protective. Feature 002 already provisions Manager accounts
through controlled administration, so deployment can establish the actor before reference
data.

**Alternatives considered**:

- Null/system AuditLog actor: rejected by the approved eight-field AuditLog model.
- No evidence for reconciliation: rejected because a rerun may overwrite a Manager edit.
- One synthetic audit row for 76 targets: rejected because target identity and aggregate
  event ordering would be ambiguous.

## Audit/outbox reuse

**Decision**: Generalize the public Audit record types to accept owner-defined closed
`StrEnum` actions/event types. Feature 003 defines its vocabulary in `locations.domain.events`
and constructs records through `audit.ports.recording`; the existing adapter, sanitizer,
transaction behavior, and database remain unchanged.

**Rationale**: Current audit record annotations are coupled to `IdentityEventType`, which
would force raw strings or cross-module domain imports. A covariant enum-shaped public
record contract preserves Feature 002 behavior and permits future owners.

**Alternatives considered**:

- Add Location values to `IdentityEventType`: rejected as ownership contamination.
- Duplicate audit/outbox infrastructure in `locations`: rejected by R-104.
- Pass raw strings: rejected because event/action vocabularies are closed.

## API and frontend contract

**Decision**: Expose unpaginated GET/PATCH Locations, GET/PATCH Config, and
GET/POST/DELETE Holidays under `/api/v1/`. Return structured warning values on successful
Location/Config updates. Regenerate OpenAPI and `schema.ts`; add handwritten typed feature
wrappers and pages over the existing transport.

**Rationale**: The Location set is fixed at 76 and R-103 approved pagination only for User.
Structured warnings support accessible UI without treating valid data as failure. Existing
transport already owns refresh/replay/account behavior.

**Alternatives considered**:

- Add geofence API: rejected because this feature supplies a rule for later module use, not
  a standalone user workflow.
- Add map/reverse-geocoding integration: rejected by scope and privacy constraints.
- Hand-edit `schema.ts` or generate `client.ts`: rejected by the approved frontend boundary.

## Migration and CI

**Decision**: Add one new additive `locations.0001_initial`, do not alter deployed migration
history, and extend existing quality/contract workflows and scripts with locations paths.

**Rationale**: New tables are N-1 compatible and require no destructive phase. Existing CI
already provides PostgreSQL, migration, architecture, generated-contract, and frontend
gates.

**Alternatives considered**:

- Put tables in Identity/Audit migrations: rejected by ownership and migration history.
- Add a new workflow/database/cache: rejected because existing infrastructure suffices.
