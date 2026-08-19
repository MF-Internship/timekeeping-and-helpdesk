# Tasks: Location Awareness and Geofence Guidance

**Input**: Design documents from `/specs/006-location-geofence-guidance/`

**Prerequisites**: [plan.md](./plan.md) (required), [spec.md](./spec.md) (required for user stories),
[research.md](./research.md), [data-model.md](./data-model.md),
[contracts/](./contracts/), [checklists/geofence-guidance.md](./checklists/geofence-guidance.md),
[checklists/ui-architecture.md](./checklists/ui-architecture.md)

**Tests**: Test tasks ARE included. The feature specification requires them explicitly (FR-043a,
FR-044, SC-003 through SC-008) and the requested task breakdown names a test per acceptance scenario.

**Organization**: Tasks are grouped by user story so each story can be implemented, tested, and
shipped as an independent increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: `[US1]`–`[US6]`, mapping to the user stories in spec.md. Setup, Foundational, and
  Polish tasks carry no story label.
- Every task names the exact file it changes.

## Path Conventions

Web application layout established by Features 002–005:

- Backend: `backend/<app>/{domain,application,ports,adapters}/`, tests in `backend/tests/`
- Frontend: `frontend/src/{app,features,shared}/`, tests in `frontend/tests/`
- Cross-language contract artifacts: `contracts/`

---

## Scope Decisions Applied Before Task Generation

These three decisions were resolved from the approved artifacts before writing tasks. They change
what the requested task groups expand into, so they are recorded here rather than silently applied.

### D1 — Requested Group 2 (backend preview/read API) is NOT APPROVED by the plan

The request scoped this group "only if approved by plan". It is not.

- `plan.md` §Summary: "**No new backend endpoint.** FR-034 forbids transmitting live guidance
  coordinates to the server; the clarification session closed this explicitly."
- `contracts/README.md`: Feature 006 "introduces no new API operation and modifies none", and
  explicitly rejects `locations_nearby`, `POST /api/v1/locations/guidance`, and any map-tile or
  geocoding proxy.
- `spec.md` FR-034: guidance MUST compute its result on the user's device.

Therefore no DTO, application query, repository read, serializer, route, or `operationId` task is
generated. The intent behind that group — a *read-only* computation that provably writes nothing —
is preserved by:

- reusing the two existing operations `locations_list` and `config_retrieve` (T002, T023–T025);
- the cross-language distance fixture that pins the on-device formula to the canonical server one
  (T007–T011);
- the backend PostgreSQL integration test proving those two reads create no `Attendance`,
  `AttendanceSession`, or `AttendanceAttempt` row (T069–T071).

Creating a guidance endpoint would require a governance amendment to FR-034 and to
`contracts/README.md` first.

### D2 — Requested Group 6 (map) is bounded by GR-001 (resolved by deferral)

`spec.md` GR-001 is **resolved by deferral**: a tile-based or SDK-based interactive map stays out of
scope, and lifting it requires an accepted amendment to `docs/CHOT_YEU_CAU.md` §6.2.1
first; FR-028 states such a map MUST NOT be introduced under this feature.
`plan.md`: "No map library, no tiles, no SDK, no iframe, no API key."

Group 6 therefore expands against the **self-contained inline-SVG spatial diagram** (FR-025–FR-027),
not a map provider. There is no map-dependency/setup task, and no external-Maps-link task: FR-029a
forbids building any external map link from live guidance coordinates. T095 records the deferral so
it stays visible rather than looking like an omission.

### D3 — Requested Group 9 (API contract) is a no-op verification, not an edit

No operation is added or changed, so `contracts/openapi.yaml` is not edited, the generated
`frontend/src/shared/api/schema.ts` is not regenerated, and no drift fixture changes. The
verification that this remains true is T093–T094.

---

## Phase 1: Setup — Existing Implementation Inspection and Reuse Contract

**Purpose**: Record, in a reviewable artifact, exactly which existing modules Feature 006 reuses, so
that no task later duplicates a geofence formula, a transport, or an authorization rule.

- [X] T001 Create `specs/006-location-geofence-guidance/reuse-inventory.md` with one empty section per reuse area (Location read model, geofence primitive, authentication/RBAC, API transport, Attendance GPS acquisition) and a "Duplication prohibited" header block (Principle I, Principle XII — one canonical geofence formula, no duplication)
- [X] T002 Record the Location and Config read model reuse in `specs/006-location-geofence-guidance/reuse-inventory.md`: `backend/locations/application/queries.py` (LocationQueryService, ConfigQueryService), `backend/locations/adapters/api/serializers.py`, exposed as `locations_list` and `config_retrieve`, consumed on the client by `listLocations()` and `getConfig()` in `frontend/src/features/locations/api/location-api.ts` — no new read path (FR-037, FR-038)
- [X] T003 Record the canonical geofence primitive in `specs/006-location-geofence-guidance/reuse-inventory.md`: `EARTH_RADIUS_M = 6_371_008.8`, `haversine_distance_m`, `classify_geofence`, `geofences_overlap` in `backend/locations/domain/geofence.py`, wrapped by `DefaultGeofenceService.evaluate` in `backend/locations/application/geofence.py`; state that the client mirror is pinned to it by the FR-043a fixture and that no second formula may be authored anywhere else
- [X] T004 Record the authentication and RBAC reuse in `specs/006-location-geofence-guidance/reuse-inventory.md`: `frontend/src/features/identity/model/IdentityRouteBoundary.tsx` for route gating and `useAuth().hasCapability("attendance.check_in.self")` from `frontend/src/features/identity/model/AuthProvider.tsx` for the punch affordance (FR-036, FR-037a); state that no new permission, role, or capability string is introduced
- [X] T005 Record the API transport reuse in `specs/006-location-geofence-guidance/reuse-inventory.md`: `frontend/src/shared/transport/authenticated-fetch.ts` remains the sole chokepoint and `frontend/src/shared/api/client.ts` the sole typed client; guidance adds no `fetch` call of its own and no `api/` folder under `features/guidance/` (FR-030, FR-034)
- [X] T006 Record the existing Attendance GPS acquisition path in `specs/006-location-geofence-guidance/reuse-inventory.md`: `frontend/src/features/attendance/model/use-foreground-position.ts` (`useForegroundPosition`, `FreshPosition`) stays the *only* acquisition used by the punch command via `freshCommand()` in `frontend/src/features/attendance/model/attendance-state.ts`; guidance gets a separate acquisition and MUST NOT feed it into a punch (FR-039)

**Checkpoint**: The reuse inventory is complete and reviewable; no production file has changed yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The shared distance fixture, the fixture-pinned client geometry, the bounded
acquisition primitive, the nearby ranking, and the privacy guard. Every user story depends on these.

**⚠️ CRITICAL**: No user story phase may start until this phase is complete.

### Shared distance fixture (FR-043a)

- [X] T007 Create `contracts/fixtures/geofence-distance.json` with `earth_radius_m: 6371008.8`, `tolerance_m: 0.001`, and the sample set defined in `specs/006-location-geofence-guidance/contracts/geofence-distance-fixture.md` (identical points, short baseline, cross-boundary pairs at the three known overlapping Location pairs, antipodal-safe long baseline), each entry carrying `expected_distance_m` (FR-043a)
- [X] T008 Add `backend/tests/contract/locations/test_geofence_distance_fixture.py` asserting every fixture entry against `haversine_distance_m` from `backend/locations/domain/geofence.py` within `tolerance_m`, plus symmetry (`d(a,b) == d(b,a)`) and the `earth_radius_m` constant match — path matches `plan.md` and the existing `backend/tests/contract/locations/` convention (FR-043, FR-043a)
- [X] T009 Create `frontend/src/features/guidance/model/geofence.ts` mirroring the canonical geometry exactly — same `EARTH_RADIUS_M`, same haversine `R·2·asin(min(1, sqrt(a)))`, and `classifyGeofence(distanceM, radiusM)` returning only `"INSIDE_GEOFENCE" | "OUTSIDE_GEOFENCE"` (closed two-value enum, no `UNCERTAIN`, accuracy never applied to radius per FR-015, FR-016)
- [X] T010 Add `frontend/tests/contract/geofence-parity.test.ts` asserting the same `contracts/fixtures/geofence-distance.json` entries against `frontend/src/features/guidance/model/geofence.ts` within `tolerance_m`, so both languages are pinned to one fixture (FR-043a)
- [X] T011 Add a boundary case to `frontend/tests/contract/geofence-parity.test.ts` proving `classifyGeofence` returns `INSIDE_GEOFENCE` at exactly `distance_m === radius_m` and `OUTSIDE_GEOFENCE` one ULP beyond (FR-015, SC-006)

### Geolocation primitive (Group 3)

- [X] T012 Create `frontend/src/features/guidance/model/position-types.ts` declaring `GuidancePosition` (`latitude`, `longitude`, `accuracyM`, `capturedAt`), `AcquisitionErrorKind = "PERMISSION_DENIED" | "UNAVAILABLE" | "TIMEOUT" | "UNKNOWN"` closed at exactly four values (FR-008a), `AcquisitionState`, and `NearbyEntry` (`code`, `name`, `address`, `distanceM`, `radiusM`, `status`, `distanceToBoundaryM`, `insideMarginM`) per data-model.md
- [X] T013 Create `frontend/src/features/guidance/model/use-guidance-position.ts` with a single-shot acquisition using `{ enableHighAccuracy: true, maximumAge: 0, timeout: 15000 }` that clears its watch/callback the instant one sample arrives (FR-002, FR-008)
- [X] T014 Add the acquiring/idle/resolved state machine to `frontend/src/features/guidance/model/use-guidance-position.ts` so the acquiring state always terminates into a displayed position or one of the four failure outcomes within the 15 s timeout, never indefinitely (FR-003)
- [X] T015 Add device-error classification to `frontend/src/features/guidance/model/use-guidance-position.ts` mapping `GeolocationPositionError.PERMISSION_DENIED` → `PERMISSION_DENIED`, a missing `navigator.geolocation` → `UNAVAILABLE`, code `TIMEOUT` → `TIMEOUT`, and anything else → `UNKNOWN`, with no fallthrough to an Attendance error code (FR-008a, FR-008b)
- [X] T016 Add `capturedAt` capture to `frontend/src/features/guidance/model/use-guidance-position.ts` from the device sample timestamp, stored as an ISO-8601 string, never derived from a server clock (FR-005)
- [X] T017 Add `accuracyM` capture to `frontend/src/features/guidance/model/use-guidance-position.ts` recording the device-reported horizontal 95% confidence radius verbatim, with no rescaling or reinterpretation (FR-003b)
- [X] T018 Add sample validation to `frontend/src/features/guidance/model/use-guidance-position.ts` rejecting a sample as unusable — before any distance is computed — when latitude, longitude, or accuracy is non-finite, out of range, or negative (FR-009)
- [X] T019 Add the explicit `refresh()` action to `frontend/src/features/guidance/model/use-guidance-position.ts` where a newer request supersedes an in-flight one, exactly one acquisition stays outstanding, and a superseded result is discarded even if it arrives first (FR-004)
- [X] T020 Add teardown to `frontend/src/features/guidance/model/use-guidance-position.ts` clearing the acquisition on unmount and on `document.visibilitychange` to hidden, so no fix continues in the background and no listener leaks (FR-002, Out of Scope: continuous tracking)
- [X] T021 Add `frontend/tests/unit/guidance/use-guidance-position.test.tsx` with a stubbed `navigator.geolocation` covering: single-shot clear-after-first-sample, acquiring-state termination, the four error kinds, `capturedAt`/`accuracyM` passthrough, unusable-sample rejection, refresh supersession with an out-of-order arrival, and unmount/hidden-tab teardown (FR-002, FR-003, FR-004, FR-005, FR-008a, FR-009, FR-044)
- [X] T022 Add an assertion to `frontend/tests/unit/guidance/use-guidance-position.test.tsx` proving no repeat callback fires after a resolved acquisition — the watch id is cleared and the stub receives no further invocation (explicit no-background-tracking proof) (FR-002, Out of Scope: continuous tracking)

### Reference data and ranking

- [X] T023 Create `frontend/src/features/guidance/model/nearby.ts` with `rankNearby()` filtering to `is_active === true` Locations only, per the research.md seven-step algorithm (FR-010)
- [X] T024 Add distance, status, `distanceToBoundaryM = max(distanceM - radiusM, 0)` and `insideMarginM` derivation to `frontend/src/features/guidance/model/nearby.ts`, computed only through `model/geofence.ts` (FR-014, FR-018)
- [X] T025 Add ordering to `frontend/src/features/guidance/model/nearby.ts`: ascending `distanceM`, ties within `tolerance_m` broken by lexicographically smallest `code`, containing Locations never promoted ahead of a closer non-containing Location (FR-012, FR-013)
- [X] T026 Add the five-entry cap to `frontend/src/features/guidance/model/nearby.ts` that keeps **every** containing Location first and then fills up to five, so the list may exceed five when more than five geofences contain the position, with no maximum search distance applied (FR-013, FR-013a)
- [X] T027 Add `frontend/tests/unit/guidance/nearby.test.ts` covering: inactive exclusion, ordering, tie-break by `code`, the cap keeping all containing entries, the empty-active-directory case, and the outside-nearest-but-inside-farther case (FR-010, FR-012, FR-013, FR-013a, FR-018)
- [X] T028 Create `frontend/src/features/guidance/model/guidance-state.ts` exposing `useGuidance()` that composes the acquisition, `listLocations({ is_active: true })` and `getConfig()` from `frontend/src/features/locations/api/location-api.ts`, the ranked nearby list, and the focused target — holding all of it in component memory only (FR-034, FR-037)
- [X] T029 Add reference-data-unavailable handling to `frontend/src/features/guidance/model/guidance-state.ts`: when the directory or config cannot be loaded, expose an `unevaluated` result that keeps the position readout, states that reference data is unavailable, and substitutes no default radius or accuracy threshold (FR-021a)
- [X] T030 Add a 1 Hz age tick to `frontend/src/features/guidance/model/guidance-state.ts` computing `ageSeconds` as device-local elapsed time since `capturedAt` and `isStale = ageSeconds > 60`, used for display only and never to block an action (FR-005)
- [X] T031 Add `frontend/tests/unit/guidance/guidance-state.test.tsx` covering composition of position + directory + config, the `unevaluated` reference-data path with no defaulted values, and the stale flag flipping strictly above 60 s (exactly 60 s is not yet stale) (FR-005, FR-021a)

### Privacy guard (Group 8)

- [X] T032 Add `frontend/tests/architecture/gps-privacy.test.ts` statically asserting that no file under `frontend/src/features/guidance/` references `localStorage`, `sessionStorage`, `document.cookie`, `indexedDB`, `console.*`, or any telemetry/metric sink (FR-030, FR-032, FR-033, SC-004)
- [X] T033 Extend `frontend/tests/architecture/gps-privacy.test.ts` to assert that no file under `frontend/src/features/guidance/` constructs a URL, query string, or route parameter from a coordinate or accuracy value, and that it issues no `fetch`/`XMLHttpRequest` outside `frontend/src/shared/transport/authenticated-fetch.ts` (FR-029a, FR-030, FR-034, SC-005)
- [X] T033a Extend `frontend/tests/architecture/gps-privacy.test.ts` to assert that no file under `frontend/src/features/guidance/` references `task_gps_good_accuracy_m` or `task_gps_low_accuracy_m`, so the Task-module GPS thresholds can never be mistaken for the Attendance quality gate — `Config.max_attendance_accuracy_m` is the only accuracy threshold guidance may read (FR-017, FR-020)
- [X] T033b Add `frontend/tests/architecture/guidance-boundary.test.ts` constraining imports for `frontend/src/features/guidance/`: it may import from `shared/`, `features/locations/api/`, and its own module only; it MUST NOT import from `features/attendance/model/` (no reuse of the punch acquisition), MUST NOT be imported by `features/locations/`, and MUST expose no module that another feature imports for a geofence decision (FR-034, FR-039, Principle XII)

**Checkpoint**: Geometry is fixture-pinned in both languages, acquisition is bounded and leak-free,
ranking is correct, and the privacy guard is armed. User stories may now proceed in parallel.

---

## Phase 3: User Story 1 — Understand whether my current position will be accepted (Priority: P1) 🎯 MVP

**Goal**: An employee acquires a position and sees coordinates, accuracy, capture time, freshness,
the nearest active Location with distance / radius / inside-outside, boundary distance when outside,
and — separately — whether the accuracy is good enough for Attendance at all.

**Independent Test**: Open the guidance panel with permission granted, acquire a position, and
confirm every listed value is shown, that the inside/outside verdict flips exactly at
`distance_m = radius_m`, and that the accuracy verdict flips exactly at
`accuracy_m = Config.max_attendance_accuracy_m` independently of position.

### Implementation

- [X] T034 [US1] Create `frontend/src/features/guidance/ui/GuidancePanel.tsx` as the client component that calls `useGuidance()` and composes the position, nearby, and diagnostic regions behind an explicit "Xem vị trí" trigger — no acquisition on mount (FR-001)
- [X] T035 [US1] Create `frontend/src/features/guidance/ui/PositionStatus.tsx` rendering latitude and longitude rounded to six decimal places for display, while the unrounded values remain the only input to every computation (FR-003a)
- [X] T036 [US1] Add the accuracy readout to `frontend/src/features/guidance/ui/PositionStatus.tsx` showing `accuracy_m` against `Config.max_attendance_accuracy_m` as a measurement-quality verdict presented separately from the position verdict (FR-017, FR-020)
- [X] T037 [US1] Add the acquisition-time and age readout to `frontend/src/features/guidance/ui/PositionStatus.tsx`, marking the snapshot visibly stale strictly above 60 s and stating that a punch will take a new reading, labelled advisory (FR-005)
- [X] T038 [US1] Add the "Làm mới vị trí" refresh call-to-action to `frontend/src/features/guidance/ui/PositionStatus.tsx` wired to the hook's `refresh()`, enabled in every resolved and failed state (FR-004)
- [X] T039 [US1] Add weak-accuracy remediation text to `frontend/src/features/guidance/ui/PositionStatus.tsx` offering only device-side actions (enable precise location, move outdoors, wait for a better fix) and never implying that any action relaxes a server rule (FR-021)
- [X] T040 [US1] Add accessible status semantics to `frontend/src/features/guidance/ui/PositionStatus.tsx` — `role="status"` with `aria-live="polite"` for state transitions, a text label alongside every colour-coded verdict, and a labelled refresh button (FR-019, FR-020)
- [X] T041 [US1] Create `frontend/src/features/guidance/ui/NearbyList.tsx` rendering the ranked entries, each showing `code` together with name and registered address (FR-011)
- [X] T042 [US1] Add the distance and radius readouts per entry to `frontend/src/features/guidance/ui/NearbyList.tsx`, both in metres with the `_m` unit shown, sourced only from `nearby.ts` (FR-011, FR-014)
- [X] T043 [US1] Add the inside/outside status per entry to `frontend/src/features/guidance/ui/NearbyList.tsx` using the closed two-value vocabulary, with no third "uncertain" rendering and no accuracy folded into it (FR-015, FR-016)
- [X] T044 [US1] Add the distance-to-boundary guidance to `frontend/src/features/guidance/ui/NearbyList.tsx` for outside entries, explicitly labelled an estimate for guidance only and never described as a business acceptance rule (FR-018)
- [X] T045 [US1] Add the guidance status wording covering the FR-019 cases (inside exactly one, inside several, outside all, no active Location available, reference data unavailable) to `frontend/src/features/guidance/ui/GuidancePanel.tsx`
- [X] T046 [US1] Add the Vietnamese guidance strings to `frontend/src/shared/messages.ts` under a `guidance` group, reusing existing keys where they already exist rather than duplicating them (FR-019, FR-021)
- [X] T046a [US1] Add a projection step to `frontend/src/features/guidance/model/nearby.ts` that narrows each directory row to exactly the attributes guidance needs — `code`, name, address, registered latitude/longitude, `radius_m`, `is_active` — so no other Location field enters guidance state, no new directory field is requested, and no new endpoint is required (FR-038)

### Tests for User Story 1

- [X] T047 [P] [US1] Add scenario A to `frontend/tests/unit/guidance/position-status.test.tsx`: accurate reading inside exactly one active Location names it by `code` and name, shows `distance_m`, `radius_m`, an "inside" status, and states the reading meets the accuracy requirement (FR-011, FR-014, FR-015, FR-017, SC-001)
- [X] T048 [P] [US1] Add scenario B to `frontend/tests/unit/guidance/nearby-list.test.tsx`: accurate reading outside every nearby active Location shows an "outside all" status, identifies the nearest, and shows the remaining distance to that boundary labelled as an estimate (FR-018, FR-019, SC-001)
- [X] T049 [P] [US1] Add scenario D to `frontend/tests/unit/guidance/position-status.test.tsx`: `accuracy_m` above `max_attendance_accuracy_m` states Attendance will reject for weak GPS regardless of position, while the position status is still reported separately (FR-017, FR-020, SC-002)
- [X] T050 [P] [US1] Add scenario H to `frontend/tests/unit/guidance/position-status.test.tsx`: refreshing into a better sample updates accuracy, coordinates, acquisition time, distances, and statuses, and discards the previous snapshot (FR-004, FR-005)
- [X] T051 [P] [US1] Add scenario I to `frontend/tests/unit/guidance/position-status.test.tsx`: refreshing into a worse sample shows the worse reading honestly, flips the accuracy verdict to insufficient, and never retains the older better snapshot (FR-004, FR-017, FR-020)
- [X] T052 [P] [US1] Add the stale-snapshot test to `frontend/tests/unit/guidance/position-status.test.tsx`: a snapshot older than 60 s is marked stale and states that a punch will take a new reading, while nothing is blocked (FR-005, FR-040)
- [X] T053 [P] [US1] Add the two-gate independence test to `frontend/tests/unit/guidance/nearby-list.test.tsx`: the inside/outside verdict flips exactly at `distance_m = radius_m` and the accuracy verdict flips exactly at `accuracy_m = max_attendance_accuracy_m`, with `accuracy_m` sampled at zero, just below, exactly at, just above the threshold, and above every configured `radius_m` (SC-006)
- [X] T053a [P] [US1] Add the data-minimisation test to `frontend/tests/unit/guidance/nearby.test.ts`: a directory row carrying extra attributes is projected down to the FR-038 set, and the guidance state exposes none of the extras (FR-038)

**Checkpoint**: User Story 1 is independently demonstrable. This is the MVP.

---

## Phase 4: User Story 2 — Recover when the device cannot give a position (Priority: P1)

**Goal**: Permission denied, geolocation unavailable, timeout, and unknown failures each produce a
distinguishable, actionable message with a working retry and no infinite spinner.

**Independent Test**: Simulate permission denied, geolocation unavailable, and acquisition timeout
and confirm three distinguishable messages, no infinite loading state, and a working retry.

### Implementation

- [X] T054 [US2] Add the permission-denied presentation to `frontend/src/features/guidance/ui/PositionStatus.tsx`: states permission was denied, explains the browser/OS setting the user must change, offers an explicit retry, and never re-prompts automatically or repeatedly (FR-006)
- [X] T055 [US2] Add the geolocation-unavailable presentation to `frontend/src/features/guidance/ui/PositionStatus.tsx`, distinct from denial, while position-independent Location reference information stays readable (FR-007)
- [X] T056 [US2] Add the timeout presentation to `frontend/src/features/guidance/ui/PositionStatus.tsx`, distinct from denial, keeping no partial or fabricated position and offering "Làm mới vị trí" (FR-008)
- [X] T057 [US2] Add the unknown-failure presentation to `frontend/src/features/guidance/ui/PositionStatus.tsx` as its own fourth outcome with retry, never silently reclassified into one of the other three (FR-008a)
- [X] T058 [US2] Add the error-vocabulary separation to `frontend/src/features/guidance/ui/PositionStatus.tsx`: device failures are worded from the guidance vocabulary only and are never rendered as, mapped onto, or worded as `OUTSIDE_RADIUS`, `WEAK_GPS`, `LOCATION_CHOICE_REQUIRED`, or any other canonical API error code from `frontend/src/shared/errors/api-error.ts` (FR-008b)
- [X] T059 [US2] Add the device-side-only remediation constraint to `frontend/src/features/guidance/ui/PositionStatus.tsx` for all four failure outcomes, with no wording that suggests a workaround relaxes a server rule (FR-021)

### Tests for User Story 2

- [X] T060 [P] [US2] Add scenario E to `frontend/tests/unit/guidance/acquisition-failure.test.tsx`: denial shows the permission message, offers retry, and the stubbed `getCurrentPosition`/`watchPosition` is not re-invoked without a user action (FR-006)
- [X] T061 [P] [US2] Add scenario F to `frontend/tests/unit/guidance/acquisition-failure.test.tsx`: with `navigator.geolocation` absent, the unavailable message renders and the Location reference information remains readable (FR-007)
- [X] T062 [P] [US2] Add scenario G to `frontend/tests/unit/guidance/acquisition-failure.test.tsx`: a 15 s timeout renders a message distinct from denial, holds no partial position, and exposes a working refresh (FR-008)
- [X] T063 [P] [US2] Add the vocabulary-separation test to `frontend/tests/unit/guidance/acquisition-failure.test.tsx` asserting no rendered failure text contains an Attendance error code, and that the unknown kind renders its own message (FR-008a, FR-008b)

**Checkpoint**: User Stories 1 and 2 are both independently demonstrable.

---

## Phase 5: User Story 3 — Tell overlapping Locations apart and choose what to look at (Priority: P2)

**Goal**: Every Location whose geofence contains the position is listed and distinguishable, the
user can switch which one is focused, and that choice commits nothing.

**Independent Test**: Place a position inside two overlapping Locations, confirm both are listed
with distinguishing `code`, that switching the focus changes only the display, and that a subsequent
punch still follows the Attendance Core candidate contract.

### Implementation

- [X] T064 [US3] Add the multi-containment rendering to `frontend/src/features/guidance/ui/NearbyList.tsx`: every containing Location appears as its own entry with `code`, name, address, `distance_m`, and `radius_m`, and overlap is presented as normal data, never as an error (FR-013, FR-024)
- [X] T065 [US3] Add the "multiple geofences contain your position" status to `frontend/src/features/guidance/ui/GuidancePanel.tsx`, stating that the server will ask which one at punch time (FR-019, FR-042)
- [X] T066 [US3] Create `frontend/src/features/guidance/ui/TargetSelector.tsx` letting the user focus any listed Location, defaulting to the nearest when no explicit selection has been made (FR-022)
- [X] T067 [US3] Wire target focus into `frontend/src/features/guidance/model/guidance-state.ts` as display state only — never transmitted as `selected_location_id`, never persisted, never pre-selecting a future punch (FR-023)

### Tests for User Story 3

- [X] T068 [P] [US3] Add scenario C to `frontend/tests/unit/guidance/target-selection.test.tsx`: a reading inside two overlapping active Locations lists both separately with their own `code`, name, address, distance, and radius, states that multiple geofences contain the position, and renders no error, using the three known overlapping Location pairs as the fixture data (SC-007)
- [X] T069 [P] [US3] Add the identical-coordinates test to `frontend/tests/unit/guidance/target-selection.test.tsx`: two Locations sharing coordinates and address are still distinguishable because each entry shows `code` with name, exercised against the coincident pair `HCM000079` / `HCM010005` (SC-007)
- [X] T070 [P] [US3] Add scenario J to `frontend/tests/unit/guidance/target-selection.test.tsx`: selecting a different listed Location switches the diagram, distance, radius, and boundary readouts, and submits, persists, and pre-selects nothing (FR-022, FR-023)
- [X] T070a [P] [US3] Add the overlap-is-not-an-error assertion to `frontend/tests/unit/guidance/target-selection.test.tsx`: across all three known overlapping Location pairs, the panel renders no error region, no warning role, and no failure vocabulary — the 0% half of SC-007, which the presence-based assertions above do not prove (SC-007, FR-024)

**Checkpoint**: Overlapping sites are legible and focusable without any commitment.

---

## Phase 6: User Story 4 — Trust the server, not the preview (Priority: P2)

**Goal**: The punch result is authoritative, the punch always uses a freshly acquired sample, and a
guidance session leaves no record behind.

**Independent Test**: Produce a preview, move across a geofence boundary, punch, and confirm the
punch used a freshly acquired sample, that the server verdict is the displayed outcome, and that
opening or refreshing the preview left no row behind.

### Implementation

- [X] T071 [US4] Mount `GuidancePanel` on the Attendance screen in `frontend/src/features/attendance/ui/AttendancePanel.tsx`, rendered as a clearly labelled preview region separate from the punch controls (FR-039)
- [X] T072 [US4] Keep the two acquisitions separate in `frontend/src/features/attendance/ui/AttendancePanel.tsx`: guidance uses `useGuidance()` and the punch keeps `useForegroundPosition()` via `freshCommand()` — the guidance snapshot is never passed into a punch payload (FR-039, SC-008)
- [X] T073 [US4] Verify and preserve the existing punch request shape in `frontend/src/features/attendance/model/attendance-state.ts`: `freshCommand()` continues to acquire at press time and Feature 006 adds no field to the check-in/check-out body (FR-039, SC-008)
- [X] T074 [US4] Add the non-authoritative preview labelling to `frontend/src/features/guidance/ui/GuidancePanel.tsx` and ensure it neither enables, disables, hides, nor gates the Check In / Check Out control (FR-040)
- [X] T075 [US4] Verify — do not re-implement — the capability gate that already exists in `frontend/src/features/attendance/ui/AttendancePanel.tsx`: the punch control selects `attendance.check_out.self` when a session is open and `attendance.check_in.self` otherwise, and renders nothing when `useAuth().hasCapability()` is false. Record it in `specs/006-location-geofence-guidance/reuse-inventory.md` and add a regression test asserting that an actor without the capability still sees the full guidance panel while no punch control renders. Feature 006 introduces no new capability string and changes no existing gate (FR-037a, FR-040)
- [X] T076 [US4] Ensure the server outcome is presented as the authoritative result in `frontend/src/features/attendance/ui/AttendancePanel.tsx` when it differs from the preview, with the preview never rewritten to look correct in hindsight (FR-041)
- [X] T077 [US4] Add per-code Attendance failure wording to `frontend/src/features/attendance/ui/AttendancePanel.tsx`. Today the catch block renders one generic string for every failure, so the quickstart Scenario 6 requirement that each server outcome be distinct is not yet met. Map the canonical codes from `frontend/src/shared/errors/api-error.ts` — `OUTSIDE_RADIUS`, `WEAK_GPS`, `SESSION_ALREADY_OPEN`, `NO_OPEN_SESSION`, `INVALID_LOCATION_CHOICE` — to distinct, server-attributed messages, keeping the existing generic text as the fallback for unmapped codes; `LOCATION_CHOICE_REQUIRED` stays on the candidate path (T078). The four guidance `AcquisitionErrorKind` values of FR-008a are device outcomes and MUST NOT be rendered here, and the canonical API code `PERMISSION_DENIED` (an authorization denial) MUST NOT be worded as, or confused with, the geolocation permission denial handled by T054 — that conflation is precisely what FR-008b forbids (FR-041, FR-008b)
- [X] T078 [US4] Present the server-returned candidate set unchanged in `frontend/src/features/attendance/ui/LocationChoice.tsx` on `409 LOCATION_CHOICE_REQUIRED`, without substituting, supplementing, filtering, reordering, or pre-selecting from the guidance list (FR-042)

### Tests for User Story 4

- [X] T079 [P] [US4] Add scenario M to `frontend/tests/unit/attendance/attendance-panel.test.tsx`: after a preview showed "inside", a punch from outside acquires a fresh sample, receives `422 OUTSIDE_RADIUS`, and the rejection is presented as the authoritative outcome (FR-041, SC-008)
- [X] T080 [P] [US4] Add scenario N to `frontend/tests/unit/attendance/attendance-panel.test.tsx`: after a preview showed "outside", a punch from inside is accepted and the earlier preview never blocked or disabled the control (FR-040, FR-041)
- [X] T081 [P] [US4] Add the fresh-sample test to `frontend/tests/unit/attendance/attendance-panel.test.tsx` asserting the punch payload carries the sample acquired after the press and never the guidance snapshot, by giving the two acquisitions distinguishable stub values (SC-008)
- [X] T082 [P] [US4] Add scenario P to `frontend/tests/unit/attendance/location-choice.test.tsx`: with a focused preview target, a punch still yields the server's own `409` candidate set and the user's selection is validated against that set (FR-042)
- [X] T083 [US4] Add `backend/tests/integration/postgres/locations/test_guidance_reads_create_no_records.py` (marked `postgres`) proving that repeated `locations_list` and `config_retrieve` reads by an authenticated HELPDESK actor create no `Attendance`, `AttendanceSession`, or `AttendanceAttempt` row — scenario O, first half (FR-031, SC-003)
- [X] T084 [US4] Extend `backend/tests/integration/postgres/locations/test_guidance_reads_create_no_records.py` to assert those same reads create no `AuditLog` and no `OutboxEvent` row — scenario O, second half (FR-031, SC-003)
- [X] T085 [US4] Extend `backend/tests/contract/locations/test_coordinate_safety.py` to assert that the `locations_list` and `config_retrieve` request paths emit no log record or metric label containing a coordinate, closing the server side of FR-033 for the two operations guidance consumes
- [X] T085a [US4] Verify in `specs/006-location-geofence-guidance/reuse-inventory.md` that guidance obtains reference data only through the existing `location.view` and `config.view` contracts, and add a backend contract assertion that the LEADER, MANAGER, and HELPDESK grants for those two contracts are byte-identical to the canonical role model before and after this feature — no grant added, removed, or widened (FR-037)
- [X] T085b [US4] Verify that `backend/attendance/adapters/api/maps.py::attendance_maps_url` remains the single external-map-link producer and is unchanged by this feature, and add an assertion that no call site under `frontend/src/features/guidance/` reaches it — Feature 004 FR-036 governs stored-record links and this feature neither restates nor diverges from it (FR-029, FR-029a)

**Checkpoint**: The preview is provably advisory and provably record-free.

---

## Phase 7: User Story 5 — See the situation spatially (Priority: P3)

**Goal**: A self-contained inline-SVG diagram showing the current position, the target Location, the
geofence circle at exactly `radius_m`, and the accuracy overlay at `accuracy_m` — with zero external
requests. Scope is bounded by D2 above.

**Independent Test**: Render the diagram for a known position and target and confirm the geofence
circle scales to `Location.radius_m`, the accuracy overlay scales to `accuracy_m`, both are visually
distinguishable, and no network request leaves the page while rendering.

### Implementation

- [X] T086 [US5] Create `frontend/src/features/guidance/ui/SpatialDiagram.tsx` as an inline `<svg>` with a metres-to-viewport projection and a stated scale legend, drawing only from props already in memory — no tile, SDK, iframe, image, font, or geocoding request (FR-025, FR-028)
- [X] T087 [US5] Add the current-position marker to `frontend/src/features/guidance/ui/SpatialDiagram.tsx`, visually distinct and labelled (FR-026)
- [X] T088 [US5] Add the focused target-Location marker to `frontend/src/features/guidance/ui/SpatialDiagram.tsx`, visually distinct from the current-position marker (FR-026)
- [X] T089 [US5] Add the geofence circle to `frontend/src/features/guidance/ui/SpatialDiagram.tsx` with radius exactly `Location.radius_m` in projected metres — never expanded, shrunk, or offset by `accuracy_m` (FR-016, FR-026)
- [X] T090 [US5] Add the accuracy overlay to `frontend/src/features/guidance/ui/SpatialDiagram.tsx` with radius `accuracy_m` around the current position, styled distinctly from the geofence circle and labelled diagnostic only (FR-026)
- [X] T091 [US5] Add secondary markers for the other ranked nearby Locations to `frontend/src/features/guidance/ui/SpatialDiagram.tsx`, visually subordinate to the focused target (FR-026, FR-027)
- [X] T092 [US5] Wire secondary-marker selection in `frontend/src/features/guidance/ui/SpatialDiagram.tsx` to the same focus action as `TargetSelector`, so clicking one makes it the focused target and changes nothing else (FR-022, FR-023)
- [X] T093 [US5] Add fit-to-bounds scaling to `frontend/src/features/guidance/ui/SpatialDiagram.tsx` so the current position, the focused target, and the full geofence circle are all within the viewport with padding, recomputed when the target changes (FR-027)
- [X] T094 [US5] Add the no-position and unusable-geometry fallback to `frontend/src/features/guidance/ui/SpatialDiagram.tsx` rendering an explanatory placeholder rather than an empty or distorted diagram, and rendering nothing spatial while acquisition is in flight (FR-025, FR-027)
- [X] T095 [US5] Add an explicit note in `frontend/src/features/guidance/ui/SpatialDiagram.tsx` header comment recording that a tile/SDK interactive map is deferred under GR-001 (resolved by deferral) and FR-028, and that no external map link is offered from live guidance coordinates under FR-029a

### Tests for User Story 5

- [X] T096 [P] [US5] Add scenario K to `frontend/tests/unit/guidance/spatial-diagram.test.tsx`: the rendered SVG contains a current-position marker, a target marker, and a geofence circle whose projected radius corresponds to `Location.radius_m`, with a stated scale and both markers inside the viewport (FR-025, FR-026, FR-027, SC-005)
- [X] T097 [P] [US5] Add scenario L to `frontend/tests/unit/guidance/spatial-diagram.test.tsx`: an accuracy overlay of radius `accuracy_m` is drawn around the current position, is distinguishable from the geofence circle, and is labelled diagnostic only (FR-026)
- [X] T098 [P] [US5] Add the radius-invariance test to `frontend/tests/unit/guidance/spatial-diagram.test.tsx`: across a range of `accuracy_m` values the geofence circle radius stays exactly `Location.radius_m`, never expanded, shrunk, or offset (FR-016, FR-026)
- [X] T099 [P] [US5] Add the zero-external-request test to `frontend/tests/unit/guidance/spatial-diagram.test.tsx`: rendering issues no `fetch`, produces no `<img>`, `<iframe>`, `<link>`, or `<script>` with an external `src`/`href`, and requests no external font (SC-005)
- [X] T100 [P] [US5] Add the target-switching test to `frontend/tests/unit/guidance/spatial-diagram.test.tsx`: selecting a secondary marker re-fits the bounds to the new target and changes only display state (FR-022, FR-023, FR-027)

**Checkpoint**: All five user stories are complete and independently demonstrable.

---

## Phase 8: Polish, Privacy Sweep, and Verification

**Purpose**: Cross-cutting guarantees and the full gate run. These are the last tasks; several are
verification-only and must not be used to introduce behaviour.

### Privacy sweep (Group 8, completion)

- [X] T101 Extend `frontend/tests/architecture/gps-privacy.test.ts` to cover `frontend/src/features/attendance/ui/AttendancePanel.tsx` as well, asserting the guidance snapshot never reaches storage, a log, a URL, or a punch payload (FR-032, FR-033, FR-039, SC-004)
- [X] T102 Confirm in `frontend/tests/architecture/origin-proxy-boundary.test.ts` that `frontend/src/features/guidance/` introduces no new external origin, and add the guidance module to whatever path set that test enumerates (FR-030, SC-005)
- [X] T103 Add a no-notification-payload assertion to `frontend/tests/architecture/gps-privacy.test.ts` proving no guidance coordinate reaches a `Notification`, push, or toast payload (FR-033)

### Contract verification (Group 9, no-op by D3)

- [X] T104 Run `npm --prefix frontend run api:check` and confirm it reports no diff, proving `contracts/openapi.yaml` and `frontend/src/shared/api/schema.ts` are unchanged by this feature (Principle VII)
- [X] T105 Run `uv run --project backend python scripts/check_contract_drift.py` and confirm the drift fixtures under `backend/tests/contract/fixtures/drift/` need no update, then record the result in `specs/006-location-geofence-guidance/reuse-inventory.md` (Principle VII, FR-035)
- [X] T105a Add an SC-009 change-set guard: run `git diff --stat main...HEAD -- backend/locations/domain/ backend/attendance/domain/ contracts/openapi.yaml` and confirm the output is empty, proving the two-value membership vocabulary, the independence of the two gates, candidate resolution, and the session invariants were delivered with an empty change set; record the command and its empty output in `specs/006-location-geofence-guidance/reuse-inventory.md` (SC-009)

### Verification gates (Group 11)

- [X] T106 [P] Run `uv run --project backend pytest backend/tests/unit backend/tests/architecture backend/tests/contract backend/tests/integration/api` and confirm all pass, including the new `test_geofence_distance_fixture.py` (FR-043a, FR-044)
- [X] T107 [P] Run `uv run --project backend pytest -m postgres backend/tests/integration/postgres` and confirm all pass, including `test_guidance_reads_create_no_records.py` (FR-031, SC-003)
- [X] T108 [P] Run `npm --prefix frontend run test` and confirm every new `frontend/tests/unit/guidance/*`, `frontend/tests/contract/geofence-parity.test.ts`, and `frontend/tests/architecture/gps-privacy.test.ts` suite passes (FR-044, SC-004, SC-005)
- [X] T109 [P] Run `uv run --project backend ruff format --check backend scripts` and `uv run --project backend ruff check backend scripts` (Principle XII)
- [X] T110 [P] Run `npm --prefix frontend run format:check` and `npm --prefix frontend run lint` (Principle XII)
- [X] T111 [P] Run `npm --prefix frontend run typecheck` and confirm zero TypeScript errors across the new guidance module (Principle XII)
- [X] T112 [P] Run `uv run --project backend mypy backend/locations backend/attendance scripts` and confirm no new error from the added test modules (Principle XII)
- [X] T113 [P] Run `uv run --project backend python scripts/migration_check.py check` and confirm no migration was created (FR-035)
- [X] T114 [P] Run `npm --prefix frontend run build` and confirm the production build succeeds (Principle XII)
- [X] T115 Run `scripts/check_all.sh` end to end and confirm every gate passes with no exclusion (FR-044)
- [ ] T116 Walk `specs/006-location-geofence-guidance/quickstart.md` manually against a running stack and confirm each documented step behaves as written, correcting the quickstart if a step has drifted (FR-044)
- [ ] T116a Run the SC-001 / SC-002 user-trial protocol defined in `spec.md` §Measurable Outcomes: ten scripted observation sessions covering at least three participants and at least three device/browser combinations, each participant reading the guidance aloud under a fixed position and reference-data condition. Record per-trial pass/fail and the 15-second read time in `specs/006-location-geofence-guidance/trial-results.md`; both criteria require at least 9 of 10 successes (SC-001, SC-002)

> **Manual-verification status (T116, T116a).** Both tasks need a human at a browser and are the
> the only work left from the pre-UI-extension task set. Both are **deferred as of `2026-08-20`** and registered in
> `specs/006-location-geofence-guidance/evidence/deferred-work.md`, which carries the resume
> conditions, the per-scenario remaining checklist and the empty execution records. Deferral is
> not a pass: Feature 006 is not signed off until that register reads PASS for both.
>
> - **T116** — the executable half is done and green: every command the quickstart documents was run
>   as written, and four drifted steps were corrected in `quickstart.md` (the `manage.py` commands
>   omitted loading the root `.env`, so they died on `ConfigurationError: APP_ENV`; Scenario 1 named
>   a *Bật vị trí* trigger that the UI calls *Xem vị trí*; Scenario 8's static counterpart omitted
>   `tests/architecture/guidance-boundary.test.ts`, which is what actually proves step 5's map-link
>   rule). Every threshold, label and path the quickstart quotes was re-checked against the source:
>   `STALE_AFTER_SECONDS = 60`, `ACQUISITION_TIMEOUT_MS = 15000`, `NEARBY_LIMIT = 5`,
>   `COORDINATE_DECIMALS = 6`, and the coincident pair `HCM000079` / `HCM010005` all match.
>   **Remaining**: the interactive DevTools walkthrough of Scenarios 1–9 against a running stack —
>   geolocation overrides, storage/network/console inspection, and the punch-time re-acquisition
>   observation. Playwright now covers responsive and accessibility behavior, but it cannot replace
>   the remaining privacy-sensitive DevTools and real-participant observations.
> - **T116a** — cannot be performed by tooling at all: it is ten scripted observation sessions with
>   at least three human participants across at least three device/browser combinations, scored at
>   9 of 10 for SC-001 and SC-002 separately. The recording sheet and the full protocol are prepared
>   at `specs/006-location-geofence-guidance/trial-results.md`, ready to fill in.
- [X] T116b Produce the FR-044 verification roll-up in `specs/006-location-geofence-guidance/reuse-inventory.md`: one row per clause of FR-044 naming the specific passing test that proves it, so no clause is left resting on manual inspection alone. Any clause without a named automated test is a gap to close before sign-off (FR-044)

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)** — no dependency. T001 precedes T002–T006 (same file).
- **Phase 2 (Foundational)** — depends on Phase 1. **Blocks every user story.**
  - T007 → T008, T010, T011 (fixture must exist first)
  - T009 → T010, T011, T024
  - T012 → T013 → T014 → T015 → T016 → T017 → T018 → T019 → T020 → T021 → T022 (same file, strictly sequential)
  - T023 → T024 → T025 → T026 → T027 (same file, strictly sequential)
  - T028 → T029 → T030 → T031 (same file, strictly sequential)
  - T032 → T033 → T033a (same file `gps-privacy.test.ts`, strictly sequential); T033b is a new
    file and runs beside them
- **Phase 3 (US1, P1)** — depends on Phase 2. This is the MVP.
  - T024 → T046a (same file `nearby.ts`); T027 → T053a (same file `nearby.test.ts`)
- **Phase 4 (US2, P1)** — depends on Phase 2; touches `PositionStatus.tsx`, so it must follow
  Phase 3's T035–T040 rather than run beside them.
- **Phase 5 (US3, P2)** — depends on Phase 2 and on T041–T044 (`NearbyList.tsx`).
  - T068 → T069 → T070 → T070a (same file `target-selection.test.tsx`, strictly sequential)
- **Phase 6 (US4, P2)** — depends on Phase 2 and on T034 (`GuidancePanel.tsx` must exist to mount).
  Independent of Phases 5 and 7. T085 → T085a → T085b extend the same reuse record.
- **Phase 7 (US5, P3)** — depends on Phase 2 and on T067 (focus state) for T092.
- **Phase 8 (Polish)** — depends on every preceding phase.
  - T105 → T105a (the change-set guard reads the same reuse record)
  - T116a and T116b are the final sign-off tasks: T116a needs the whole panel shipped, and
    T116b needs every FR-044 test named in it to be green

### Story independence

- **US1** is self-contained once Phase 2 lands and is shippable alone.
- **US2** extends the same panel; it is testable alone by stubbing failures.
- **US3** needs only US1's list rendering.
- **US4** needs only US1's panel to mount, and can be developed beside US3 and US5.
- **US5** is additive and can be dropped without affecting US1–US4.

---

## Parallel Example: User Story 1

The US1 test tasks touch three files and depend only on completed implementation tasks:

```text
# After T034–T046a are complete, launch together:
T047  frontend/tests/unit/guidance/position-status.test.tsx  (scenario A)
T048  frontend/tests/unit/guidance/nearby-list.test.tsx      (scenario B)
T053  frontend/tests/unit/guidance/nearby-list.test.tsx      (two-gate independence)
T053a frontend/tests/unit/guidance/nearby.test.ts            (FR-038 data minimisation)
```

Note that T047, T049, T050, T051, and T052 all write `position-status.test.tsx` — they are marked
`[P]` relative to the other file's tasks, but should be sequenced among themselves or authored as one
editing session to avoid write conflicts.

Genuinely file-disjoint parallel sets elsewhere:

```text
Phase 2:  T007 (fixture) ∥ T012 (types) — different files, no shared dependency
Phase 6:  T083/T084 (backend pytest) ∥ T079–T082 (frontend vitest)
Phase 8:  T106 ∥ T107 ∥ T108 ∥ T109 ∥ T110 ∥ T111 ∥ T112 ∥ T113 ∥ T114
```

---

## Implementation Strategy

### MVP first

1. Complete Phase 1 (setup and reuse inventory) — nothing is built until reuse is recorded.
2. Complete Phase 2 (foundational) — geometry parity, bounded acquisition, ranking, privacy guard.
3. Complete Phase 3 (US1) and stop.
4. **Validate**: the panel answers "will my punch be accepted, and why not?" — the support-load
   reduction this feature exists for.

### Incremental delivery

- Add **US2** next: it is also P1 and without it US1 fails silently for a large share of real users.
- Add **US4** before US3 if the Attendance screen is going live at the same time, because it carries
  the server-authority guardrail (FR-039–FR-042) that makes the preview safe to expose.
- Add **US3** for the three known overlapping sites.
- Add **US5** last; it is P3 and additive.

### Change-set discipline

- No `docs/CHOT_YEU_CAU.md` edit is authorized by any task here. If a task appears to require one,
  stop and raise a governance change instead (this applies in particular to §6.2.1 and GR-001).
- No migration is created (T113 verifies this). No PostGIS or other spatial platform is introduced —
  the canonical haversine in `backend/locations/domain/geofence.py` remains the only implementation,
  mirrored once on the client and pinned by `contracts/fixtures/geofence-distance.json`.
- No new runtime dependency is added to `frontend/package.json` or `backend/pyproject.toml`.

---

## Notes

- `[P]` marks file-disjoint tasks only. Tasks that edit the same file are deliberately left
  unmarked even when they are conceptually independent.
- Test tasks sit in the phase of the behaviour they prove, not in a trailing test phase.
- Acceptance-scenario coverage map: A→T047, B→T048, C→T068, D→T049, E→T060, F→T061, G→T062,
  H→T050, I→T051, J→T070, K→T096, L→T097, M→T079, N→T080, O→T083/T084, P→T082.

## Phase 9: Convergence

**Scope**: two documentation defects found in `reuse-inventory.md` during the convergence
pass. Neither is a code defect — every automated gate is green — but both weaken the
evidence trail that FR-043a and FR-044 depend on, so both are recorded rather than fixed
silently.

**Not duplicated here**: the interactive half of FR-044 and the SC-001 / SC-002 user trials
remain open under their existing, unchecked IDs **T116** and **T116a**. Convergence is
append-only and does not renumber or restate existing tasks; those two are the blocking
items and are tracked where they already live.

- [X] T117 Correct the FR-044 roll-up row 7 in `specs/006-location-geofence-guidance/reuse-inventory.md`, which names the non-existent path `contracts/geofence-distance-fixture.md`; both parity tests actually read `contracts/fixtures/geofence-distance.json` per FR-043a (partial)
- [X] T118 Correct the membership vocabulary in `specs/006-location-geofence-guidance/reuse-inventory.md` §6, which writes the two-value set as `INSIDE_GEOFENCE` / `OUTSIDE_RADIUS`; the canonical second member is `OUTSIDE_GEOFENCE`, and `OUTSIDE_RADIUS` is an Attendance business error whose mixing into the membership vocabulary is the conflation FR-008b forbids (contradicts)

---

## UI Modernization Scope Decisions (2026-08-20 Extension)

The completed T001–T118 implementation is the behavioral baseline. T119 onward refactors its
presentation without reopening canonical geofence or Attendance decisions.

- Repository inspection found no UI library, Tailwind setup, application shell, AppHeader,
  BottomNavigation, generic Button/Card/Badge, or approved local MobiFone asset. The existing
  `shared/ui/async-state` is extended rather than copied.
- The approved MobiFone header asset is a delivery dependency. T130 is blocked until product supplies
  it; no task authorizes downloading, redrawing, tracing, or substituting an arbitrary logo.
- The requested map-provider adapter/setup is intentionally absent. GR-001 and FR-025–FR-029a
  prohibit SDKs, tiles, iframes, geocoding, provider types, and live-position external links. The map
  tasks below decompose and progressively disclose the existing self-contained SVG spatial view.
- Preview GPS and punch GPS remain separate acquisition paths. UI refactoring MUST NOT pass a
  guidance snapshot into `freshCommand()` or make presentation state authoritative.

## Phase 10: Shared UI and Employee-Shell Foundation

**Purpose**: Establish reusable tokens, primitives, brand handling, navigation, shell structure, and
browser-level UI test infrastructure before story-level composition begins.

**⚠️ CRITICAL**: T119–T144 block the UI modernization story phases. T130 blocks brand acceptance and
T132, but shell/layout work that does not fabricate a logo may proceed in parallel.

- [X] T119 Create semantic brand, status, neutral, spacing, radius, typography, focus, touch-target, safe-area, and content-width CSS custom properties in `frontend/src/shared/ui/theme/tokens.css`, import them from `frontend/src/app/globals.css`, and replace the existing raw color literals used by shared global rules (FR-057–FR-060)
- [X] T120 [P] Add `frontend/tests/architecture/design-tokens.test.ts` asserting new shell/guidance/attendance styles consume semantic variables and introduce no raw brand, success, critical, surface, or text hex values outside `frontend/src/shared/ui/theme/tokens.css` (FR-057)
- [X] T121 [P] Add semantic variant, disabled/loading, accessible-name, and native button/link contract tests in `frontend/tests/unit/ui/button.test.tsx` before implementing the shared Button (FR-060, FR-064)
- [X] T122 Implement `frontend/src/shared/ui/button/Button.tsx`, `frontend/src/shared/ui/button/Button.module.css`, and `frontend/src/shared/ui/button/index.ts` with primary, secondary, quiet, and destructive presentations, a 44 CSS-pixel minimum target, and visible focus behavior (FR-058, FR-060, FR-064)
- [X] T123 [P] Add labelled-region, padding/boundary, and semantic-heading contract tests in `frontend/tests/unit/ui/card-section-heading.test.tsx` before implementing Card and SectionHeading (FR-058, FR-064)
- [X] T124 Implement the reusable surface primitive in `frontend/src/shared/ui/card/Card.tsx`, `frontend/src/shared/ui/card/Card.module.css`, and `frontend/src/shared/ui/card/index.ts` without feature data or status logic (FR-058, FR-064)
- [X] T125 Implement the caller-level-aware heading primitive in `frontend/src/shared/ui/section-heading/SectionHeading.tsx`, `frontend/src/shared/ui/section-heading/SectionHeading.module.css`, and `frontend/src/shared/ui/section-heading/index.ts` (FR-064)
- [X] T126 [P] Add text-plus-icon/shape variant tests for neutral, ready, warning, and critical badges in `frontend/tests/unit/ui/badge.test.tsx` before implementing Badge (FR-061, FR-064)
- [X] T127 Implement `frontend/src/shared/ui/badge/Badge.tsx`, `frontend/src/shared/ui/badge/Badge.module.css`, and `frontend/src/shared/ui/badge/index.ts` so no semantic meaning depends on color alone (FR-057, FR-061, FR-064)
- [X] T128 [P] Extend `frontend/tests/unit/ui/async-state.test.tsx` with stable loading, empty, and distinct recoverable/error-state contracts, including labelled retry actions and `aria-busy` semantics (FR-052–FR-053, FR-062, FR-064)
- [X] T129 Extend `frontend/src/shared/ui/async-state/AsyncState.tsx` and `frontend/src/shared/ui/async-state/index.ts` with reusable LoadingState, EmptyState, and ErrorState compositions instead of creating feature-local generic duplicates (FR-053, FR-064)
- [X] T130 Record the product-supplied approved header variant's provenance, original filename/format, intended header use, and intrinsic dimensions in `frontend/public/brand/README.md`, then place that unchanged approved file beside the README under the recorded filename; remain blocked rather than forcing SVG conversion, downloading, or improvising an asset if approval is unavailable (FR-055)
- [X] T131 [P] Add intrinsic-dimension, aspect-ratio, contain behavior, clear-space class, and `MobiFone` alternative-text tests in `frontend/tests/unit/ui/mobifone-logo.test.tsx` before implementing the brand primitive (FR-055)
- [X] T132 Implement the sole logo consumer in `frontend/src/shared/ui/brand/MobiFoneLogo.tsx`, `frontend/src/shared/ui/brand/MobiFoneLogo.module.css`, and `frontend/src/shared/ui/brand/index.ts`, importing only the exact approved local filename recorded by T130 (FR-055)
- [X] T133 [P] Add canonical order, implemented-route filtering, capability filtering, active-route, and authenticated-account-action tests in `frontend/tests/unit/shell/employee-navigation.test.ts` (FR-037a, FR-056)
- [X] T134 Create the declarative route/capability registry in `frontend/src/shared/ui/shell/employee-navigation.ts`, initially exposing only implemented and permitted destinations while retaining Tasks → Attendance → Reports → Account ordering after omissions (FR-056)
- [X] T135 [P] Add page title/back action, logo, avatar initials, account identity, change-password, and logout semantics tests in `frontend/tests/unit/shell/app-header.test.tsx` before implementing AppHeader (FR-054–FR-056)
- [X] T136 Implement `frontend/src/shared/ui/shell/AppHeader.tsx` and `frontend/src/shared/ui/shell/AppHeader.module.css` using MobiFoneLogo and existing AuthProvider identity/account operations without inventing an Account route (FR-054–FR-056)
- [X] T137 [P] Add shared-registry, `aria-current`, keyboard, mobile bottom-navigation, and tablet/desktop rail semantics tests in `frontend/tests/unit/shell/primary-navigation.test.tsx` (FR-054, FR-056, FR-060)
- [X] T138 Implement the phone presentation in `frontend/src/shared/ui/shell/BottomNavigation.tsx` with safe-area padding and no page-owned destination markup (FR-054, FR-056)
- [X] T139 Implement the tablet/desktop presentation in `frontend/src/shared/ui/shell/NavigationRail.tsx` using the identical filtered item list and relative order as BottomNavigation (FR-054, FR-056)
- [X] T140 Implement `frontend/src/shared/ui/shell/PrimaryNavigation.tsx` and `frontend/src/shared/ui/shell/PrimaryNavigation.module.css` as the single responsive presentation boundary for T138 and T139 (FR-054, FR-056, FR-059)
- [X] T141 [P] Replace the placeholder shell showcase with container, safe-area, content-padding, nav-mode, and no-duplicate-shell tests in `frontend/tests/contract/foundation-shell.test.tsx` (FR-054, FR-059, SC-012)
- [X] T142 Implement `frontend/src/shared/ui/shell/AppShell.tsx` and `frontend/src/shared/ui/shell/AppShell.module.css` as the lowest client boundary for AuthProvider/usePathname state, with a bounded content slot and bottom-nav clearance (FR-054, FR-059)
- [X] T143 Create `frontend/src/app/(employee)/layout.tsx`, move the existing Attendance route to `frontend/src/app/(employee)/attendance/page.tsx` without changing `/attendance`, and remove page-owned `<main>`/top-level shell markup while preserving IdentityRouteBoundary (FR-054, FR-056)
- [X] T144 Add `@playwright/test` and `@axe-core/playwright` as development-only dependencies and browser-test scripts in `frontend/package.json` and `frontend/package-lock.json`, create `frontend/playwright.config.ts`, and add a shared authenticated/geolocation fixture in `frontend/tests/e2e/fixtures/attendance.ts`; add no runtime UI or map dependency (FR-044, FR-059–FR-063)

**Checkpoint**: Reusable visual primitives and one authorization-aware employee shell are available;
no feature business decision has moved into shared UI.

---

## Phase 11: User Story 1 — Actionable GPS and Location Guidance (Priority: P1)

**Goal**: Replace the technical-first preview with reusable GPS, Location summary, nearby list, and
progressive diagnostic presentations while preserving the existing acquisition and geometry rules.

**Independent Test**: With one successful GPS sample, the default view identifies the nearest target,
accuracy and threshold, ready/weak meaning, distance/radius/inside-outside state, and up to the approved
nearby subset without exposing coordinates until details are expanded.

### Tests for User Story 1

- [X] T145 [P] [US1] Add discriminated view-state tests for idle, requesting, ready, weak, refreshing, stale, outside, overlap, and reference-loading/failure mappings in `frontend/tests/unit/guidance/guidance-view-state.test.ts` before presentation refactoring (FR-047, FR-050–FR-053)
- [X] T146 [P] [US1] Add numeric accuracy, threshold, textual label, non-color cue, and presentational-only indicator tests in `frontend/tests/unit/guidance/gps-status-card.test.tsx` (FR-050–FR-051)
- [X] T147 [P] [US1] Add name/code/address, distance/radius, nearest/focused, and independent inside/outside badge tests in `frontend/tests/unit/guidance/location-summary-card.test.tsx` (FR-011, FR-048)
- [X] T148 [P] [US1] Add ordering, empty state, all-containing visibility, three-row floor, View more, and collapse-never-hides-containing tests in `frontend/tests/unit/guidance/nearby-locations.test.tsx` (FR-013, FR-048)
- [X] T149 [P] [US1] Add closed-by-default technical details and textual coordinate/time/radius/precise-distance tests in `frontend/tests/unit/guidance/location-diagnostics.test.tsx` (FR-047, FR-063)

### Implementation for User Story 1

- [X] T150 [US1] Add a presentation-ready discriminated state mapper in `frontend/src/features/guidance/model/guidance-view-state.ts` that consumes existing guidance/reference results and makes no new eligibility, geofence, or Attendance decision (FR-051, FR-066)
- [X] T151 [US1] Create `frontend/src/features/guidance/ui/GpsAccuracyIndicator.tsx` and `frontend/src/features/guidance/ui/GpsAccuracyIndicator.module.css` as a numeric/icon/ring presentation of already determined state, never an authorization source (FR-050–FR-051)
- [X] T152 [US1] Create the base and ready-state presentation in `frontend/src/features/guidance/ui/GpsStatusCard.tsx`, showing `accuracy_m`, required threshold, positive text, non-color cue, and refresh action (FR-050)
- [X] T153 [US1] Add the weak state to `frontend/src/features/guidance/ui/GpsStatusCard.tsx` with the numeric comparison, distinct text/icon cue, device remediation, and no Attendance CTA gating (FR-017, FR-020–FR-021)
- [X] T154 [US1] Add refreshing and stale states to `frontend/src/features/guidance/ui/GpsStatusCard.tsx`, replacing the old claim while refreshing and retaining readable age/value plus fresh-punch guidance while stale (FR-005, FR-050, FR-053)
- [X] T155 [US1] Add focused live-region and `aria-busy` semantics to `frontend/src/features/guidance/ui/GpsStatusCard.tsx` so meaningful transitions announce once and the one-second age counter stays outside the live region (FR-062)
- [X] T156 [US1] Create `frontend/src/features/guidance/ui/LocationSummaryCard.tsx` using Card/Badge and presentation-ready Location props for name, code, address, distance, radius, nearest/focused state, and independent inside/outside state, with no Attendance command/capability/threshold import (FR-011, FR-048, FR-065)
- [X] T157 [US1] Create the reusable coherent row in `frontend/src/features/guidance/ui/NearbyLocationItem.tsx` with presentation-ready Location props, semantic status labels, and a 44 CSS-pixel target/focus affordance where selectable, importing no Attendance command/capability/threshold type so Task Evidence can reuse it directly (FR-048, FR-060, FR-065)
- [X] T158 [US1] Replace `frontend/src/features/guidance/ui/NearbyList.tsx` with `frontend/src/features/guidance/ui/NearbyLocations.tsx`, preserving canonical ordering, adding the empty state and collapsed/expanded rules, reusing NearbyLocationItem, and exposing no Attendance-specific API to future Task Evidence composition (FR-013, FR-048, FR-065)
- [X] T159 [US1] Move latitude, longitude, capture time, configured radius, precise distance, and troubleshooting into an accessible disclosure in `frontend/src/features/guidance/ui/LocationDiagnostics.tsx` (FR-047, FR-060, FR-063)
- [X] T160 [US1] Refactor `frontend/src/features/guidance/ui/GuidancePanel.tsx` to compose the view-state mapper, GpsStatusCard, LocationSummaryCard, NearbyLocations, and LocationDiagnostics without duplicating their markup or changing explicit acquisition behavior (FR-001, FR-045–FR-047, FR-066)
- [X] T161 [US1] Add a semantic integration regression covering acquire, ready, weak, outside, stale, refresh, disclosure, and list expansion in `frontend/tests/unit/guidance/guidance-experience.test.tsx`, asserting behavior and roles rather than exact CSS values (FR-044, SC-010–SC-011)

**Checkpoint**: User Story 1 is independently usable without the spatial disclosure or Attendance
composition refactor; all technical details remain available but secondary.

---

## Phase 12: User Story 2 — Distinct Device and Reference Recovery (Priority: P1)

**Goal**: Give every location-acquisition/reference failure a stable, accessible, state-specific
explanation and recovery path.

**Independent Test**: Permission denial, unavailable GPS, timeout, unknown acquisition failure, and
reference-data failure each show distinct wording/actions and never appear as an empty or Attendance
business-rejection state.

- [X] T162 [P] [US2] Add permission-denied, unavailable, timeout, unknown, and reference-failure presentation/recovery tests in `frontend/tests/unit/guidance/guidance-state-notice.test.tsx` before implementation (FR-006–FR-008b, FR-021a, FR-052–FR-053)
- [X] T163 [US2] Create `frontend/src/features/guidance/ui/GuidanceStateNotice.tsx` with distinct permission-settings, unavailable terminal guidance, timeout refresh, and unknown retry variants using shared Card/Button/Badge primitives (FR-006–FR-008b)
- [X] T164 [US2] Add the unavailable state to `frontend/src/features/guidance/ui/GpsStatusCard.tsx` without fabricated accuracy/threshold values or permission-denied/timeout wording (FR-007, FR-050, FR-052)
- [X] T165 [US2] Replace feature-local generic reference loading/error markup in `frontend/src/features/guidance/ui/GuidancePanel.tsx` with the extended shared AsyncState plus reference-specific copy and retry behavior (FR-021a, FR-053, FR-064)
- [X] T166 [US2] Add an acquisition/reference recovery integration suite in `frontend/tests/unit/guidance/acquisition-failure.test.tsx` covering focus preservation, explicit retries, no automatic re-prompt, stable primary regions, and separate device/server vocabularies (FR-006–FR-008b, FR-053, SC-011)

**Checkpoint**: User Story 2 can be reviewed independently by forcing each browser/reference failure.

---

## Phase 13: User Story 3 — Unambiguous Overlap and Visual Target Selection (Priority: P2)

**Goal**: Preserve every containing Location and make nearest, containing, preview-focused, and
server-candidate selection visibly and behaviorally distinct.

**Independent Test**: At each known overlap, every containing Location remains visible by code/name,
nearest becomes only the default visual focus, changing focus updates guidance/spatial presentation,
and no Attendance candidate is preselected or reordered.

- [X] T167 [P] [US3] Add overlap, coincident-code, nearest-fallback, user-focus-override, and all-containing collapsed-list tests in `frontend/tests/unit/guidance/overlapping-locations.test.tsx` (FR-022–FR-024, FR-048, SC-007)
- [X] T168 [US3] Add an informational overlapping-candidates badge and explanatory copy to `frontend/src/features/guidance/ui/LocationSummaryCard.tsx` and `frontend/src/features/guidance/ui/NearbyLocations.tsx`, never warning/error semantics (FR-024, FR-048)
- [X] T169 [US3] Fold the existing preview focus control from `frontend/src/features/guidance/ui/TargetSelector.tsx` into the semantic selection contract of `frontend/src/features/guidance/ui/NearbyLocations.tsx`, retaining native radio/keyboard behavior and nearest fallback (FR-022–FR-023, FR-060)
- [X] T170 [P] [US3] Extend `frontend/tests/unit/attendance/location-choice.test.tsx` to prove preview focus never changes, filters, reorders, or preselects the server-returned `LocationChoice` candidates (FR-023, FR-042)
- [X] T171 [US3] Add target selection and overlap integration coverage to `frontend/tests/unit/guidance/guidance-experience.test.tsx`, including View more and collapse behavior when containing Locations exceed the normal cap (FR-013, FR-022–FR-024, FR-048)

**Checkpoint**: User Story 3 distinguishes overlapping Locations without silently resolving the
Attendance business choice.

---

## Phase 14: User Story 4 — Attendance Composition and Server Authority (Priority: P2)

**Goal**: Recompose Attendance around the prioritized mobile hierarchy while preserving fresh punch
acquisition, capability checks, server candidate handling, session history, and authoritative results.

**Independent Test**: Both session states show the correct headline/CTA; submitting acquires a new
sample and remains stable; success/rejection persists beside the CTA; preview state never authorizes,
blocks, or supplies the command.

### Tests for User Story 4

- [X] T172 [P] [US4] Add today-loading, no/open-session, processing, success, rejection, candidate, and result-persistence orchestration tests in `frontend/tests/unit/attendance/use-attendance-experience.test.ts` before extracting the hook (FR-046, FR-052–FR-053)
- [X] T173 [P] [US4] Add page-title, Location/session context, and no/open-session headline tests in `frontend/tests/unit/attendance/attendance-context-header.test.tsx` (FR-045–FR-046)
- [X] T174 [P] [US4] Add Check In/Out, action-specific processing, duplicate-submit, capability-hiding, touch-target, and accessible-name tests in `frontend/tests/unit/attendance/primary-attendance-action.test.tsx` (FR-037a, FR-046, FR-060)
- [X] T175 [P] [US4] Add persistent inline success/rejection, updated-session, authoritative-reason, next-step, retry, and dismissal-lifetime tests in `frontend/tests/unit/attendance/attendance-outcome-card.test.tsx` (FR-053)
- [X] T176 [P] [US4] Replace the old sibling-panel assertions with semantic order, fresh-punch independence, candidate separation, and stable processing-layout tests in `frontend/tests/unit/attendance/attendance-panel.test.tsx` (FR-039–FR-046, SC-008, SC-010)

### Implementation for User Story 4

- [X] T177 [US4] Extract today fetch, action selection, fresh punch acquisition, processing, candidate, persistent outcome, and refresh orchestration from `frontend/src/features/attendance/ui/AttendancePanel.tsx` into `frontend/src/features/attendance/model/use-attendance-experience.ts` without reading guidance GPS state (FR-039–FR-042, FR-066)
- [X] T178 [US4] Create `frontend/src/features/attendance/ui/AttendanceContextHeader.tsx` for page/session headline and current/target Location context, consuming returned/calculated state only (FR-045–FR-046, FR-066)
- [X] T179 [US4] Create `frontend/src/features/attendance/ui/PrimaryAttendanceAction.tsx` using the shared Button, existing capability gates, Check In/Out labels, and action-specific busy labels without preview gating (FR-037a, FR-040, FR-046)
- [X] T180 [US4] Create `frontend/src/features/attendance/ui/AttendanceOutcomeCard.tsx` using shared Card/Badge/Button for persistent success and authoritative rejection with the required next action (FR-041, FR-053)
- [X] T181 [US4] Refactor `frontend/src/features/attendance/ui/AttendancePanel.tsx` into the ordered thin composition: context header → GPS status → primary action → inline outcome/candidates → Location summary → nearby summary → spatial/details → TodayTimeline, preserving one semantic source order (FR-045–FR-047, FR-053, FR-066)
- [X] T182 [US4] Replace Attendance today-loading/API-failure markup with shared AsyncState in `frontend/src/features/attendance/ui/AttendancePanel.tsx` and keep business rejection in AttendanceOutcomeCard rather than a generic device/location error (FR-052–FR-053, FR-064)

**Checkpoint**: User Story 4 preserves Attendance Core behavior and server authority while making the
primary action the dominant operational control.

---

## Phase 15: User Story 5 — Progressive Self-Contained Spatial Guidance (Priority: P3)

**Goal**: Decompose the existing local SVG into maintainable spatial responsibilities and mount it
only after a secondary disclosure, with no provider, external request, or Attendance logic.

**Independent Test**: Opening the spatial disclosure shows current and target markers, distinct
geofence/accuracy circles, nearby markers, legend, and fitted bounds; target switching updates only
visual focus; closing/default state requires no spatial module or external request; text remains complete.

### Tests for User Story 5

- [X] T183 [P] [US5] Add closed-by-default disclosure, lazy-mount, loading/error fallback, textual alternative, and semantic control tests in `frontend/tests/unit/guidance/spatial-panel.test.tsx` (FR-049, FR-053, FR-060, FR-063)
- [X] T184 [P] [US5] Extend `frontend/tests/unit/guidance/spatial-diagram.test.tsx` with separately labelled current/target markers, geofence/accuracy circles, nearby markers, legend, fit-bounds, and target-switching assertions without exact pixel checks (FR-026–FR-027)

### Implementation for User Story 5

- [X] T185 [US5] Move metre projection and fit-bounds calculations from the oversized JSX module into pure `frontend/src/features/guidance/ui/spatial/projection.ts` while retaining current scale semantics (FR-027)
- [X] T186 [US5] Implement the current-position marker in `frontend/src/features/guidance/ui/spatial/markers.tsx` as labelled/presentational geometry with no tiny pseudo-button behavior (FR-026, FR-060, FR-063)
- [X] T187 [US5] Add the visually distinct target marker and subordinate nearby markers to `frontend/src/features/guidance/ui/spatial/markers.tsx`, routing any target change through the existing preview-focus callback only (FR-022–FR-023, FR-026–FR-027)
- [X] T188 [US5] Implement the allowed geofence radius layer in `frontend/src/features/guidance/ui/spatial/radius-layers.tsx` from `radius_m` only, never adjusted by accuracy (FR-016, FR-026)
- [X] T189 [US5] Add the visually and textually distinct GPS accuracy circle to `frontend/src/features/guidance/ui/spatial/radius-layers.tsx` from `accuracy_m`, labelled diagnostic only (FR-026)
- [X] T190 [US5] Create `frontend/src/features/guidance/ui/spatial/legend.tsx` defining current position, target, nearby marker, allowed radius, GPS uncertainty, and scale meanings in text and distinct visual treatments (FR-026–FR-027, FR-049)
- [X] T191 [US5] Refactor `frontend/src/features/guidance/ui/SpatialDiagram.tsx` to compose projection, markers, radius layers, and legend as a prop-only SVG with bounded JSX responsibilities and no provider type (FR-025–FR-028, FR-066)
- [X] T192 [US5] Create `frontend/src/features/guidance/ui/SpatialPanel.tsx` with an accessible post-CTA disclosure, dynamic local import after expansion, stable loading/error fallback, and a persistent textual Location alternative (FR-049, FR-053, FR-063)
- [X] T193 [US5] Extend `frontend/tests/architecture/origin-proxy-boundary.test.ts` and `frontend/tests/architecture/guidance-boundary.test.ts` to reject map SDK/provider imports, iframe/tiles/external fonts, external live-position URLs, and eager spatial loading (GR-001, FR-025, FR-028–FR-029a)

**Checkpoint**: User Story 5 is optional and independently testable; it never dominates or authorizes
Attendance and adds no runtime provider dependency.

---

## Phase 16: User Story 6 — Complete Attendance Confidently on Every Viewport (Priority: P1, Cross-Cutting)

**Goal**: Integrate the shell and story components into the final mobile-first Attendance experience,
then prove hierarchy, responsive behavior, navigation, accessibility, and visual consistency.

**Independent Test**: At 320, 375, 390/430, 768, and 1280/1440 CSS pixels, the same DOM/task order
keeps Location, Attendance state, GPS, and CTA immediately usable; navigation never overlaps content;
all operational states remain understandable by touch, keyboard, and assistive technology.

- [X] T194 [P] [US6] Add an integrated semantic hierarchy test in `frontend/tests/unit/attendance/attendance-experience.test.tsx` covering default diagnostics/spatial disclosure state, CTA precedence, shell ownership, and all GPS/Location/Attendance states (FR-045–FR-053, SC-010–SC-012)
- [X] T195 [US6] Add co-located responsive styles in `frontend/src/features/attendance/ui/AttendancePanel.module.css` and `frontend/src/features/guidance/ui/GuidancePanel.module.css`: one column at 320–430 px, one DOM order, bounded CTA width, and at most two post-CTA regions at tablet/desktop widths (FR-045, FR-059)
- [X] T196 [P] [US6] Add 320 px and 375 px browser scenarios in `frontend/tests/e2e/attendance-responsive.spec.ts` asserting no horizontal overflow, wrapped long content, reachable full-width CTA, safe-area clearance, collapsed-by-default spatial/details regions, and a usable non-overflowing spatial view after disclosure (FR-049, FR-054, FR-059, SC-013)
- [X] T197 [P] [US6] Add 390 px and 430 px scenarios to `frontend/tests/e2e/attendance-responsive.spec.ts` asserting unchanged task order, bottom navigation, CTA priority, and stable state transitions with larger mobile spacing only (FR-045–FR-046, FR-059, SC-013)
- [X] T198 [P] [US6] Add 768 px and 1280/1440 px scenarios to `frontend/tests/e2e/attendance-responsive.spec.ts` asserting navigation rail, centered bounded content, at most two regions, non-stretched controls, unchanged source/focus order, and usable fitted spatial guidance (FR-054, FR-059, SC-013)
- [X] T199 [P] [US6] Add capability/implemented-route navigation, active item, bottom-nav/rail switch, shell/content non-overlap, and account-action browser coverage in `frontend/tests/e2e/employee-shell.spec.ts` (FR-054–FR-056, SC-012–SC-013)
- [X] T200 [P] [US6] Add keyboard order, visible focus, native button/radio/disclosure semantics, accessible names, one-time status announcements, and textual spatial alternative checks in `frontend/tests/e2e/attendance-accessibility.spec.ts` (FR-060–FR-063, SC-014)
- [X] T201 [P] [US6] Add automated contrast, color-independent status, 44-by-44 target, and reduced-motion checks in `frontend/tests/e2e/attendance-accessibility.spec.ts`, covering primary, ready, warning, critical, navigation, and recovery states (FR-057, FR-060–FR-062, SC-014)
- [X] T202 [US6] Perform and record a non-pixel visual-consistency review for MobiFone header/logo spacing, card boundaries, primary blue action, success/error treatments, bottom navigation, typography, spacing, and status hierarchy in `specs/006-location-geofence-guidance/evidence/ui-visual-review.md`; compare directly with Field Clarity only if the missing reference is supplied, otherwise record its absence and evaluate against FR-045–FR-067 without claiming a reference comparison (FR-055–FR-058, FR-067)
- [X] T203 [US6] Add the complete GPS/Location/candidate/refresh/spatial-target/CTA regression matrix to `frontend/tests/unit/attendance/attendance-experience.test.tsx`, asserting roles, names, values, state, order, and commands rather than exact CSS values (FR-044, FR-050–FR-053)
- [ ] T204 [US6] Run a ten-participant moderated legend trial with the spatial view's color cues removed, requiring each participant to distinguish the allowed Location radius from GPS accuracy uncertainty using the legend and textual alternatives; add the protocol and aggregate pass/fail table to `specs/006-location-geofence-guidance/trial-results.md`, record no identity or coordinates, and require at least 9 of 10 successes (SC-015)

**Checkpoint**: User Story 6 provides the integrated mobile-first experience and objective responsive/
accessibility evidence without changing the meaning of Stories 1–5.

---

## Phase 17: UI Modernization Polish and Release Gates

**Purpose**: Enforce architecture boundaries, run all automated gates, and complete the human
validation that cannot be inferred from component tests.

- [X] T205 [P] Extend `frontend/tests/architecture/guidance-boundary.test.ts` with shared-ui-no-business-import, zero duplicate Button/Card/Badge/SectionHeading/loading/empty/error/shell/navigation/primary-action product behaviors inside Feature 006, no second feature-local Dialog/Sheet abstraction, presentation-only GPS indicator, separate preview/punch acquisition, presentation-ready Location props with no Attendance imports for Task Evidence reuse, component/function size, and no parallel legacy-panel-wrapper guards (FR-039, FR-051, FR-064–FR-066, SC-016)
- [X] T206 [P] Run `npm --prefix frontend run test` and record passing primitive, shell, GPS, Location, candidate, refresh, spatial target, and Attendance CTA suites in `specs/006-location-geofence-guidance/evidence/ui-verification.md` (FR-044)
- [X] T207 [P] Run the browser suite configured by T144 and record the viewport, navigation, accessibility, contrast, reduced-motion, and overflow results in `specs/006-location-geofence-guidance/evidence/ui-verification.md` (FR-059–FR-063, SC-012–SC-014)
- [X] T208 [P] Run `npm --prefix frontend run format:check`, `npm --prefix frontend run lint`, `npm --prefix frontend run typecheck`, `npm --prefix frontend run api:check`, and `npm --prefix frontend run build`, recording that no API/runtime-map dependency drift occurred in `specs/006-location-geofence-guidance/evidence/ui-verification.md` (Principles VII, IX, XII)
- [ ] T209 Update and execute the UI scenarios in `specs/006-location-geofence-guidance/quickstart.md` for every named state, shell/nav capability matrix, View more, progressive spatial/details disclosure, Check In/Out labels/outcomes, approved-logo provenance, representative viewport, and SC-015 legend trial; record SC-010–SC-015 observations in `specs/006-location-geofence-guidance/trial-results.md` without storing participant identity or coordinates (FR-044, SC-010–SC-015)

---

## UI Extension Dependencies and Execution Order

### Phase dependencies

- **Phase 10** blocks all UI-extension story work. T130 is an external asset dependency for T132 and
  final brand acceptance, but it does not authorize a substitute and need not block non-logo layout work.
- **Phase 11 (US1)** starts after Phase 10 and provides the view-state/GPS/Location components used by
  US2, US3, US4, and US6.
- **Phase 12 (US2)** depends on the view-state and GpsStatusCard boundaries from US1.
- **Phase 13 (US3)** depends on NearbyLocations and LocationSummaryCard from US1.
- **Phase 14 (US4)** depends on US1 presentation components and the Phase 10 primitives/shell; it may
  proceed in parallel with US2 and US3 after those shared boundaries stabilize.
- **Phase 15 (US5)** depends on US1 target/location state, but may proceed in parallel with US2 and US4.
- **Phase 16 (US6)** is deliberately integrated last despite its P1 priority: its independent test spans
  the completed story components and responsive shell rather than duplicating them early.
- **Phase 17** depends on every story selected for release and does not replace still-open T116/T116a.

### Parallel examples

```text
Phase 10: T121 (Button tests) ∥ T123 (Card/heading tests) ∥ T126 (Badge tests) ∥ T128 (AsyncState tests)
US1:      T145 (view-state tests) ∥ T146 (GPS tests) ∥ T147 (summary tests) ∥ T148 (nearby tests) ∥ T149 (details tests)
US4:      T172 (hook tests) ∥ T173 (header tests) ∥ T174 (CTA tests) ∥ T175 (outcome tests) ∥ T176 (composition tests)
US6:      T196/T197/T198 (viewport classes) ∥ T199 (navigation) ∥ T200/T201 (accessibility)
Polish:   T205 (architecture) ∥ T206 (unit suite) ∥ T207 (browser suite) ∥ T208 (static/build gates)
```

### Suggested MVP for this extension

1. Complete Phase 10 except any work blocked solely by the not-yet-supplied logo asset.
2. Complete US1 and US2 so field employees receive the prioritized GPS/Location flow and explicit
   recovery states.
3. Complete US4 to place the unchanged authoritative Attendance CTA in the new hierarchy.
4. Complete the mobile 320–430 px portion of US6 and validate it independently.
5. Add US3 overlap refinement, US5 spatial disclosure, wider viewports, and full release gates.

### Format and scope guard

- Every T119–T209 item follows `- [ ] T### [P?] [US?] Description with exact file path`.
- Test tasks precede their owning implementation tasks and assert behavior/semantics, not pixel values.
- No task adds a backend endpoint, schema/migration, map provider, runtime UI framework, or alternate
  Attendance/geofence authority.
