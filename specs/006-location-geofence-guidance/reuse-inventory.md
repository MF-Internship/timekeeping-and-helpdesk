# Reuse Inventory: Location Awareness and Geofence Guidance

**Feature**: 006 | **Branch**: `feature/006-location-geofence-guidance` | **Date**: 2026-08-20

## Duplication prohibited

This artifact exists so that no task in this feature duplicates an existing
geofence formula, transport, or authorization rule.

Binding rules for every task in `tasks.md`:

1. **One canonical geofence formula** (Principle XII). `backend/locations/domain/geofence.py`
   is the single authority for Earth radius, distance, and inside/outside
   classification. The client mirror added by this feature is a *mirror*, pinned
   by a committed cross-language fixture — not a second formula. No third
   implementation may be authored anywhere.
2. **No parallel read path** (Principle I). Guidance consumes only the two
   already-published read operations. No new endpoint, DTO, serializer, or
   repository read is created.
3. **No parallel transport.** `frontend/src/shared/transport/authenticated-fetch.ts`
   stays the sole HTTP chokepoint.
4. **No parallel authorization rule.** No new permission action, role, or
   capability string is introduced; existing gates are verified, not re-implemented.
5. **No parallel punch acquisition.** The authoritative punch keeps its existing
   GPS acquisition; guidance acquisition is separate and never feeds a command.

If a task appears to require a second implementation of any item below, stop the
task and report the conflict rather than duplicating.

## 1. Location and Config read model

| Layer | Module | Reused symbol |
|---|---|---|
| Backend application | `backend/locations/application/queries.py` | `LocationQueryService.list`, `ConfigQueryService.get` |
| Backend API | `backend/locations/adapters/api/serializers.py` | `LocationSerializer`, `ConfigSerializer` |
| HTTP contract | `contracts/openapi.yaml` | `locations_list`, `config_retrieve` |
| Frontend API | `frontend/src/features/locations/api/location-api.ts` | `listLocations()`, `getConfig()` |

Fields consumed: `id`, `code`, `name`, `address`, `kind`, `latitude`,
`longitude`, `radius_m`, `is_active` from `locations_list`;
`max_attendance_accuracy_m` from `config_retrieve`.

Wire precision is preserved as received: `latitude`/`longitude` are
`DecimalField(max_digits=18, decimal_places=15)` and `radius_m` is
`DecimalField(max_digits=10, decimal_places=3)`, serialized as strings.

**No new read path.** Feature 006 adds no DTO, no application query, no
repository read, no serializer, and no route. `features/guidance` therefore has
no `api/` folder; it imports `listLocations`/`getConfig` from
`features/locations/api/` (FR-037, FR-038).

## 2. Canonical geofence primitive

Authority: `backend/locations/domain/geofence.py`

| Symbol | Meaning |
|---|---|
| `EARTH_RADIUS_M = 6_371_008.8` | the only Earth radius constant |
| `haversine_distance_m(origin, destination)` | `2 · R · asin(min(1, sqrt(a)))` |
| `classify_geofence(distance_m, radius_m)` | `INSIDE_GEOFENCE` iff `distance_m <= radius_m` |
| `geofences_overlap(...)` | overlap detection used by Location administration |
| `LocationValidationResult` | closed two-value enum — `INSIDE_GEOFENCE`, `OUTSIDE_GEOFENCE` |

Wrapped for application use by `DefaultGeofenceService.evaluate` in
`backend/locations/application/geofence.py`.

The client mirror `frontend/src/features/guidance/model/geofence.ts` reproduces
this arithmetic exactly and is pinned to it by the FR-043a fixture
`contracts/fixtures/geofence-distance.json`, asserted from both languages
(`backend/tests/contract/locations/test_geofence_distance_fixture.py` and
`frontend/tests/contract/geofence-parity.test.ts`) at a 1 mm tolerance.

Prohibited anywhere in this feature: a second distance formula, a second Earth
radius constant, an `UNCERTAIN` third state, and any adjustment of a radius or a
distance by `accuracy_m` (QUY_TAC §10 items 7 and 8; FR-016).

## 3. Authentication and RBAC

| Concern | Module | Reused symbol |
|---|---|---|
| Route gating | `frontend/src/features/identity/model/IdentityRouteBoundary.tsx` | `IdentityRouteBoundary` |
| Punch affordance | `frontend/src/features/identity/model/AuthProvider.tsx` | `useAuth().hasCapability("attendance.check_in.self")` / `"attendance.check_out.self"` |

The capability gate already lives in the Attendance punch control and is
**verified, not re-implemented**, by this feature (T075).

Verified shape, read from `PunchButton` in
`frontend/src/features/attendance/ui/AttendancePanel.tsx`: the control selects
`attendance.check_out.self` when `today.has_open_session` is true and
`attendance.check_in.self` otherwise, and returns `null` — rendering no control
at all, rather than a disabled one — when `useAuth().hasCapability()` is false.
Feature 006 preserves that capability decision while extracting the control
into `PrimaryAttendanceAction`; it does not change the capability strings or
turn a missing capability into a disabled control. The regression test
`frontend/tests/unit/attendance/attendance-panel.test.tsx` →
"guidance stays fully visible to an actor without the punch capability" pins
both halves: the guidance preview renders in full while no punch control exists.

**No new permission action, role, or capability string is introduced**
(FR-036, FR-037a). Guidance is a read-only preview: nothing under
`features/guidance` reads `hasCapability` or gates an action, and an actor
without the punch capability still sees the full guidance panel.

Reference data reaches guidance through the two grants that already existed,
`location.view` and `config.view`, and through no other. Their canonical holder
set — LEADER, MANAGER and HELPDESK, for both grants alike — is unchanged by this
feature: no grant added, removed, or widened (FR-037). Pinned by
`backend/tests/contract/locations/test_reference_grants_unchanged.py` (T085a),
which states the holder set from both directions, asserts neither grant is a
mutation, asserts no `PermissionAction` value was invented for this feature, and
checks on the wire that each of the three roles still reads both
`/api/v1/locations/` and `/api/v1/config/`.

### External map links (T085b)

`backend/attendance/adapters/api/maps.py::attendance_maps_url` remains the
single producer of an external map link. Verified: it is the only module under
`backend/` containing an external map host literal, its only call site is
`AttendanceSerializer.get_maps_url` in
`backend/attendance/adapters/api/serializers.py`, and `git diff` against the
feature baseline `97ab2cc` reports no change to it — this feature neither edits
nor re-implements it.

Guidance previews a position that has not been recorded, so it has no stored
record to link to. Feature 004 FR-036 governs the link on a stored record and
continues to govern it alone; this feature neither restates nor diverges from it
(FR-029, FR-029a). Pinned by
`frontend/tests/architecture/guidance-boundary.test.ts` →
"reaches no external map link, neither the stored one nor one of its own", which
asserts that no file under `frontend/src/features/guidance/` mentions `maps_url`
or any external map host.

## 4. API transport

| Layer | Module | Role |
|---|---|---|
| Transport | `frontend/src/shared/transport/authenticated-fetch.ts` | sole HTTP chokepoint (auth, refresh, request id) |
| Typed client | `frontend/src/shared/api/client.ts` | sole `openapi-fetch` client |
| Generated types | `frontend/src/shared/api/schema.ts` | unchanged; `npm run api:check` must diff empty |

Guidance adds **no `fetch` call of its own**, no `XMLHttpRequest`, no alternate
origin, and **no `api/` folder under `features/guidance/`** (FR-030, FR-034).
Live coordinates are never placed in a URL, query string, or route.
`frontend/tests/architecture/api-transport-boundary.test.ts` covers the new
module automatically; the new `gps-privacy.test.ts` adds the coordinate-specific
guards.

## 5. Attendance GPS acquisition

| Module | Reused symbol | Role |
|---|---|---|
| `frontend/src/features/attendance/model/use-foreground-position.ts` | `useForegroundPosition`, `FreshPosition` | the **only** acquisition used by the punch |
| `frontend/src/features/attendance/model/attendance-state.ts` | `freshCommand()` | builds the punch payload from a freshly acquired sample |

`freshCommand()` is unchanged by this feature: every punch re-acquires its own
fresh fix at the moment of the command.

Guidance gets a **separate** acquisition
(`frontend/src/features/guidance/model/use-guidance-position.ts`) and **MUST NOT**
feed its snapshot into a punch payload (FR-039). The two acquisitions stay
independent: refreshing the preview does not arm a punch, and punching does not
consume the preview snapshot.

`features/guidance` must not import from `features/attendance/model/`, and
`features/locations/` must not import from `features/guidance/` — enforced by
`frontend/tests/architecture/guidance-boundary.test.ts`.

## 6. Contract and change-set verification (recorded at implementation time)

### `npm --prefix frontend run api:check` — T104

```
> node scripts/generate-api.mjs --check
```

No diff reported (exit 0). `contracts/openapi.yaml` and
`frontend/src/shared/api/schema.ts` are byte-identical to their pre-feature
state, as decision D3 requires.

### `uv run --project backend python scripts/check_contract_drift.py` — T105

No output, exit 0. The drift fixtures under
`backend/tests/contract/fixtures/drift/` need no update: this feature adds no
endpoint, no field, and no error code (FR-035).

### SC-009 empty-change-set guard — T105a

The task text names `main...HEAD`. That range is **not** the feature-006
baseline here: local `main` is at `7eef298` (feature 001), while this branch was
cut from `97ab2cc` (= `origin/develop`). Run against `main` the diff reports the
work of features 002–005 and proves nothing about feature 006, so the guard was
run against the real baseline as well and both results are recorded.

```
$ git diff --stat 97ab2cc -- backend/locations/domain/ backend/attendance/domain/ contracts/openapi.yaml
(no output)
```

Empty. The two-value membership vocabulary (`INSIDE_GEOFENCE` /
`OUTSIDE_GEOFENCE`), the independence of the accuracy gate from the radius gate,
candidate resolution, and the session invariants were all delivered by earlier
features and are reused here with a **zero-line change set** in the authoritative
domain and contract paths (SC-009).

For the record, the literal command from the task text:

```
$ git diff --stat main...HEAD -- backend/locations/domain/ backend/attendance/domain/ contracts/openapi.yaml
 backend/attendance/domain/…, backend/locations/domain/…, contracts/openapi.yaml
 12 files changed, 2941 insertions(+), 120 deletions(-)
```

Every one of those lines predates this branch and belongs to features 002–005.

## 7. FR-044 verification roll-up (recorded at implementation time)

FR-044 lists thirteen claims that verification must *prove*, not merely assert.
One row per clause, in the order the clause appears in the requirement, naming
the automated test that proves it. Every named test passes; no clause rests on
manual inspection alone.

| # | FR-044 clause | Proving test |
|---|---------------|--------------|
| 1 | Opening and refreshing guidance writes no row of any kind | `backend/tests/integration/postgres/locations/test_guidance_reads_create_no_records.py::test_repeated_guidance_reference_reads_write_nothing_at_all` (PostgreSQL, row counts taken before and after repeated reads) |
| 2 | No guidance coordinate reaches storage, logs, telemetry, or a URL | `frontend/tests/architecture/gps-privacy.test.ts` — `guidance and its host never persist a coordinate`, `… never log or report a coordinate`, `… never put a coordinate on the wire`, `… never put a coordinate in a notification`; URL form additionally by `frontend/tests/architecture/guidance-boundary.test.ts::reaches no external map link, neither the stored one nor one of its own` |
| 3 | The spatial view issues no external request | `frontend/tests/unit/guidance/spatial-diagram.test.tsx::the diagram issues no external request → renders without fetching and without any external resource element` |
| 4 | The quality gate and the radius gate are evaluated independently at their exact boundaries | `frontend/tests/unit/guidance/nearby-list.test.tsx::two-gate independence` (membership flips exactly at `distance_m = radius_m`, unchanged across the accuracy sweep; the accuracy verdict flips alone at `accuracy_m = threshold`), reinforced by `frontend/tests/contract/geofence-parity.test.ts::geofence boundary is inclusive` (`INSIDE` at exactly `distance === radius`, `OUTSIDE` one ULP beyond, radius never adjusted by an accuracy value) |
| 5 | Inactive Locations are excluded | `frontend/tests/unit/guidance/nearby.test.ts::rankNearby → excludes inactive Locations` and `… returns an empty list when every Location is inactive`; the request side by `frontend/tests/unit/guidance/guidance-state.test.tsx::requests only the active Locations` |
| 6 | Overlapping and coincident Locations are listed individually with `code` | `frontend/tests/unit/guidance/target-selection.test.tsx::scenario C — overlapping Locations are listed separately` and `… identical coordinates stay distinguishable` (both codes shown, each offered as its own target, neither merged nor dropped) |
| 7 | Client and server distance calculations agree on the shared FR-043a fixture | `frontend/tests/contract/geofence-parity.test.ts` (same Earth radius, same tolerance, every fixture case) and `backend/tests/contract/locations/test_geofence_distance_fixture.py`, both reading `contracts/fixtures/geofence-distance.json` |
| 8 | The acquiring state always terminates | `frontend/tests/unit/guidance/use-guidance-position.test.tsx::terminates the acquiring state within the timeout instead of hanging`, with `… clears the watch the instant the first sample arrives and never fires again` and `… tears down on a hidden tab and on unmount` for the success and teardown paths |
| 9 | The four FR-008a acquisition failures are each reported distinctly | `frontend/tests/unit/guidance/acquisition-failure.test.tsx` — scenarios E, F and G plus `gives an unrecognised failure its own message rather than one of the other three` |
| 10 | No acquisition failure is ever rendered as an Attendance error code | `frontend/tests/unit/guidance/acquisition-failure.test.tsx::vocabulary separation → renders no Attendance error code for device error code %s` (parameterised over every kind), and `frontend/tests/unit/guidance/use-guidance-position.test.tsx::reports a denied permission without inventing an Attendance error code` |
| 11 | A refresh during an in-flight acquisition leaves exactly one outstanding acquisition | `frontend/tests/unit/guidance/use-guidance-position.test.tsx::supersedes an in-flight acquisition and discards its out-of-order result` |
| 12 | An unavailable directory or configuration produces no defaulted threshold or radius | `frontend/tests/unit/guidance/guidance-state.test.tsx::useGuidance reference data` — the parameterised unavailability cases plus `keeps the position readout and substitutes no defaulted values` |
| 13 | A punch after a preview carries a newly acquired sample | `frontend/tests/unit/attendance/attendance-panel.test.tsx::punches with the sample acquired at press time, never the guidance snapshot`, with the structural guarantee in `frontend/tests/architecture/gps-privacy.test.ts::builds every punch payload from a sample acquired at press time` |

No clause is unproven, so there is no gap to close before sign-off.

## 8. UI modernization reuse decisions (2026-08-20 plan update)

### Existing UI to reuse/refactor

| Existing responsibility | Decision |
|---|---|
| `shared/ui/async-state` | extend/re-skin; do not create duplicate generic loading/error components |
| `features/guidance/model/*` | preserve acquisition, geometry, nearby ranking, focus fallback and privacy behavior; add presentation mapping/disclosure state |
| `EntryReadouts`, `NearbyList`, `PositionStatus`, `TargetSelector` | refactor into cohesive cards/items/details while preserving tested wording and boundary semantics |
| `SpatialDiagram` | retain the local SVG behavior; split projection, markers and legend to satisfy clean-code limits; mount only after disclosure |
| `AttendancePanel` | extract orchestration into an Attendance model hook and reduce to ordered composition |
| `LocationChoice` | retain as Attendance-owned server-candidate selection; never share preview focus state |
| `TodayTimeline` | retain as Attendance-owned secondary history |
| `IdentityRouteBoundary`, `AuthProvider.hasCapability` | retain as route/visibility inputs; shell filtering never replaces enforcement |

### New shared responsibilities with clear reuse

- Button, Card, Badge and SectionHeading primitives;
- semantic CSS token layer;
- ApplicationShell, AppHeader, one ResponsiveNavigation and one declarative
  implemented-route/capability registry;
- one MobiFoneLogo consumer after the approved local asset is supplied.

### Deliberately not generalized

- Dialog/Sheet: Feature 006 outcomes are clarified as inline, and the existing
  generated-password dialog remains identity-specific.
- Map provider adapter: external providers remain prohibited; the valid boundary
  is `SpatialPanel -> decomposed local SpatialDiagram`.
- Shared GPS acquisition: preview and punch readings must stay independent.
- Tasks/Reports/Account navigation destinations: routes do not yet exist, so no
  placeholder entry is emitted.
