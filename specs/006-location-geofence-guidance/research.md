# Phase 0 Research: Location Awareness and Geofence Guidance

**Feature**: 006 | **Branch**: `feature/006-location-geofence-guidance` | **Date**: 2026-08-20

Every decision below was taken after inspecting the existing implementation.
Source references are to real files in this repository.

---

## 1. Architecture — module ownership and dependency direction

### Decision

Business ownership stays where it already is. The UX extension adds a narrow
shared presentation/shell layer and refactors the existing Attendance and
guidance UI without moving canonical GPS/geofence/Attendance decisions.

| Concern | Owner (existing) | Feature 006 relationship |
|---|---|---|
| Registered `Location` data | `backend/locations/` — model, `application/queries.py::LocationQueryService.list`, `adapters/api/serializers.py::LocationSerializer` | **Consumed unchanged** via `GET /api/v1/locations/` |
| Config thresholds | `backend/locations/application/queries.py::ConfigQueryService.get`, `ConfigSerializer` | **Consumed unchanged** via `GET /api/v1/config/` |
| Canonical geofence geometry | `backend/locations/domain/geofence.py` — `EARTH_RADIUS_M`, `haversine_distance_m`, `classify_geofence`, `geofences_overlap`; wrapped by `application/geofence.py::DefaultGeofenceService.evaluate` | **Mirrored, not forked** — see §2 |
| Attendance validation & candidate resolution | `backend/attendance/application/commands.py` + `backend/attendance/domain/attendance.py` (`passes_accuracy`, `is_inside`, `resolve_location`) | **Untouched.** Remains the sole authority |
| Browser geolocation acquisition | `frontend/src/features/attendance/model/use-foreground-position.ts` | **Generalized** into `features/guidance/model/use-guidance-position.ts`; attendance keeps its own punch-time acquisition |
| GPS presentation | *(new)* `frontend/src/features/guidance/ui/` | New, frontend-only |
| Attendance integration point | `frontend/src/features/attendance/ui/AttendancePanel.tsx` | Composes `GuidancePanel`; punch path unchanged in sequence |

Dependency direction: `features/guidance` → `features/locations/api` →
`shared/api/client` → `shared/transport/authenticated-fetch`. `features/guidance`
never imports from `features/attendance`; the composition happens the other way
round, inside `AttendancePanel`. No browser API (`navigator.geolocation`,
`window`, `document`) appears anywhere under `backend/`.

### Rationale

Constitution Principle II fixes an inward hexagonal dependency direction, and
Principle I puts CHOT above implementation convenience. The registered-Location
read model and the geofence geometry already exist and already satisfy every
data need in the spec (`LocationSerializer` returns `latitude`, `longitude`,
`radius_m`, `is_active`, `name`, `code`, `address`; `ConfigSerializer` returns
`max_attendance_accuracy_m`). Adding a module to own any of that would create a
second owner for a single fact — the exact failure the user's brief forbids.

### Alternatives considered

- **A shared `geo` package used by both backend and frontend.** Rejected: the
  stack is fixed (Python backend, TypeScript frontend) with no shared runtime,
  so a "shared package" would be a build-time code generator — far more
  machinery than a 30-line function and a fixture. The fixture in §2 gets the
  same guarantee for a fraction of the cost.
- **Putting the guidance hook in `features/attendance`.** Rejected: guidance is
  reachable independently of punching and must not inherit attendance's
  command-path assumptions. A sibling module keeps the preview/authority split
  visible in the directory tree.

---

## 2. Backend preview/read model — is a dedicated endpoint required?

### Decision

**No backend endpoint is introduced.** No new query, DTO, permission action,
serializer, OpenAPI operation, or URL. Guidance is computed on-device.

### Rationale

This is settled by the accepted spec, which outranks a default preference for
server-side computation (Principle I):

- **FR-034** states that guidance computes on-device from the authorized
  Location directory and Config, and that **live guidance coordinates MUST NOT
  be transmitted to the backend**.
- The clarification session (2026-08-19) closed the question directly: no
  preview endpoint is introduced; instead FR-043a mandates a committed shared
  distance fixture asserted by both a server-side and a client-side test.
- FR-031 requires guidance to produce no `Attendance`,
  `AttendanceAttempt`, `AttendanceSession`, `TaskUpdate` or `AuditLog`. The
  cheapest way to guarantee "the server writes nothing for a preview" is for the
  preview never to reach the server at all.

**Why client-side calculation does not duplicate or weaken canonical business
logic** — the four-part argument the brief asks for:

1. **It is not the authority, and cannot become one.** The client result never
   travels anywhere. Every Check In / Check Out sends a *fresh* GPS sample and
   the server independently recomputes distance, accuracy and candidates inside
   a locked reference snapshot (`backend/attendance/application/commands.py`,
   R-126). A wrong client answer changes what the user *expects*; it can never
   change what the system *decides*. The failure mode of a client bug is a
   confusing preview, not an unauthorized punch.
2. **The inputs are identical and already authorized.** The client uses the same
   `Location.latitude/longitude/radius_m/is_active` rows and the same
   `Config.max_attendance_accuracy_m` the server uses, delivered by the same
   RBAC-guarded endpoints. There is no second source of truth for the data.
3. **The geometry is pinned, not re-invented.** `features/guidance/model/geofence.ts`
   is a literal mirror of `backend/locations/domain/geofence.py`: same
   `EARTH_RADIUS_M = 6_371_008.8`, same haversine formula, same two-value
   classification (`INSIDE_GEOFENCE` iff `distance_m <= radius_m`), same refusal
   to subtract accuracy from radius, same closed enum. Both implementations are
   asserted against the **same committed fixture** (§ contracts/) with a stated
   tolerance, so drift is a CI failure in both languages, not a silent
   divergence. This is a stronger guarantee than "the server computed it",
   because it is checked on every run in both directions.
4. **A preview endpoint would create the risk it claims to remove.** It would
   require transmitting live coordinates — violating FR-034 — and would create a
   server-produced geofence verdict that is *not* an Attendance decision but
   looks exactly like one, inviting exactly the "stale preview authorizes a
   punch" confusion the boundary exists to prevent.

Deliberate omissions preserved: the client performs **no** R-119 nearest-
observation tie-break (R-119 selects among `AttendanceAttempt` rows, a
server-side observation record, and has business effect). The display ordering
does break equal distances by lexicographically smallest `code` per FR-012 —
that is a stable presentation convention with no business effect, not R-119.
The client also **never** auto-resolves among multiple containing Locations
(QUY_TAC §10 item 7) — it lists them and waits for a human choice.

### Alternatives considered

- **`GET /api/v1/locations/nearby?lat=&lon=`.** Rejected — violates FR-034,
  places precise employee coordinates in a URL query string (and therefore in
  every access log and proxy hop), and contradicts the recorded clarification.
- **`POST /api/v1/locations/guidance` with coordinates in the body.** Rejected
  for the same FR-034 reason; a POST that writes nothing also muddies the
  command/query split.
- **Server-side computation with coordinates rounded before transmission.**
  Rejected: rounding is a display concern (six decimals, FR-003a) and degrading
  precision to make transmission palatable still transmits.

---

## 3. Frontend geolocation primitives

### Decision

One hook, `features/guidance/model/use-guidance-position.ts`, generalized from
the proven `features/attendance/model/use-foreground-position.ts`. It exposes:

```text
position?        { latitude, longitude, accuracy_m, captured_at }   // strings, wire-shaped
status           "idle" | "prompting" | "acquiring" | "ready" | "error"
permission       "unknown" | "prompt" | "granted" | "denied"        // via navigator.permissions when available
error?           { kind: "PERMISSION_DENIED" | "UNAVAILABLE" | "TIMEOUT" | "UNKNOWN" }
ageSeconds       derived from captured_at against a 1 Hz tick
isStale          ageSeconds > STALE_AFTER_S (60 s, mirroring the server freshness window)
refresh()        explicit user-triggered re-acquisition
cancel()         stops any in-flight acquisition
```

Acquisition is **user-initiated only**: nothing is requested until the user
activates "Bật vị trí" / "Làm mới" (CHOT §5.1 — the client only asks for
permission after an explicit action).

### `watchPosition` justification (required by the brief)

The hook uses `navigator.geolocation.watchPosition` with
`{ enableHighAccuracy: true, maximumAge: 0, timeout: 15000 }` as a **single-shot
acquisition**, exactly as the existing attendance hook does, and this does not
become tracking because the watch is torn down on **every** exit path:

- on the **first** successful fix — the success callback calls `stop()` (which
  calls `clearWatch`) *before* resolving, so at most one fix is ever observed;
- on **error** — the error callback calls `stop()` before rejecting;
- on **tab hidden** — a `visibilitychange` listener calls `stop()` when
  `document.hidden`;
- on **unmount / navigation** — the effect cleanup calls `stop()`;
- on **explicit cancel** and at the **start of every new acquisition** —
  `acquire()` calls `stop()` first, so watches cannot accumulate;
- and the 15 s `timeout` bounds the worst case even if none of the above fires.

No fix sequence is retained (state holds one snapshot, replaced wholesale), no
fix is emitted while the tab is hidden, nothing is sent anywhere, and no punch is
ever triggered automatically. This is precisely the "GPS foreground có giới hạn,
không phải tracking" allowance in CHOT §5.1.

`watchPosition` is preferred over `getCurrentPosition` because on mobile
browsers `getCurrentPosition` with `maximumAge: 0` frequently returns a poor
first fix or times out while the GPS is still converging; `watchPosition`
delivers the first fix the device is willing to stand behind and is then
immediately cleared. The observable behaviour is identical to a one-shot read.

### Rationale

Reusing a hook that already ships, is already tested
(`tests/unit/attendance/use-foreground-position.test.tsx`), and already
implements the visibility teardown is strictly safer than writing a second
acquisition path. Generalizing it — rather than importing it across feature
boundaries — keeps attendance's punch-time acquisition independent of guidance
state, which is what makes §7's freshness guarantee structural.

### Alternatives considered

- **`getCurrentPosition` only.** Rejected for first-fix quality on mobile; kept
  as an acceptable fallback if a target browser misbehaves, since the hook's
  external contract does not expose which primitive is used.
- **A long-lived watch with throttled updates.** Rejected outright — that is
  continuous tracking, forbidden by FR-006 and the Out of Scope section.
- **Auto-acquire on mount.** Rejected — CHOT §5.1 requires an explicit user
  action before the permission prompt.

---

## 4. Nearby Location UI

### Decision

Three presentational components plus one pure ranking module.

`features/guidance/model/nearby.ts` (pure, no React, no I/O):

```text
rankNearby(position, locations, config) -> NearbyLocationView[]
  1. filter is_active === true
  2. distance_m = haversine(position, location)                  // canonical mirror
  3. status = distance_m <= radius_m ? INSIDE_GEOFENCE : OUTSIDE_GEOFENCE
  4. distance_to_boundary_m = max(distance_m - radius_m, 0)      // FR-018, meaningful when OUTSIDE
  5. inside_margin_m = max(radius_m - distance_m, 0)             // optional display, INSIDE only
  6. sort ascending by distance_m, then by code (stable, presentation-only)
  7. keep ALL entries with status INSIDE_GEOFENCE, then fill to five with the
     nearest OUTSIDE entries — no maximum distance filter (FR-013, FR-013a)
```

Step 7 is the only place the five-entry cap lives, and it is written so that a
containing Location is never displaced by the cap.

`ui/PositionStatus.tsx` — accuracy in metres, capture time, age/freshness badge,
GPS-quality verdict (`accuracy_m <= max_attendance_accuracy_m` → "đủ tốt",
otherwise a warning that a punch would be rejected as `WEAK_GPS`), permission and
error states, and a refresh button.

`ui/NearbyLocations.tsx` — one row per `NearbyLocationView`: name, code,
distance, radius, inside/outside badge, and distance-to-boundary when outside.
The collapsed phone presentation keeps every INSIDE entry visible and adds the
nearest OUTSIDE entries until at least three rows show; “View more” reveals the
rest of the computed list. When two or more rows are INSIDE, the list renders a
neutral overlap note and **does not** resolve an Attendance winner.

`ui/GuidancePanel.tsx` — composition + focused-target state.

**Presentation is separated from authorization** by construction: `nearby.ts` is
a pure function over data, the components receive props, and *nothing* in
`features/guidance` reads `useAuth().hasCapability` or gates an action. The only
capability checks remain in `AttendancePanel`'s `PunchButton`
(`attendance.check_in.self` / `attendance.check_out.self`), untouched.

### Rationale

FR-010–FR-019 and FR-022–FR-024 are all display concerns over already-fetched
data. Keeping the ranking pure makes the overlap and cap rules unit-testable
without a DOM, and makes the fixture parity test in §11 possible.

### Alternatives considered

- **Ranking inside the component.** Rejected — untestable without rendering and
  invites business rules to drift into JSX.
- **Presenting the nearest visual target as the resolved Attendance Location.**
  Rejected. The nearest ranked Location is the automatic visual focus required
  by FR-022 until a user overrides it, but it is labelled as display focus only
  and never becomes `selected_location_id` or resolves overlapping candidates.

---

## 5. Map / spatial visualization

### Decision

**No map library is added. No tiles, no SDK, no iframe, no API key.**
FR-025–FR-028 are satisfied by `ui/SpatialDiagram.tsx`: an inline SVG rendered
entirely from data already in the browser.

Existing dependency evaluation (`frontend/package.json`): dependencies are
`next`, `react`, `react-dom`, `openapi-fetch` — **no map library exists**, so
there is nothing to reuse.

Why none is introduced, in authority order:

- **GR-001** in the spec, **resolved by deferral**: tile-based / SDK / iframe
  interactive maps are permanently out of scope for this feature. The decision
  taken was *not* to amend `docs/CHOT_YEU_CAU.md` §6.2.1; lifting the deferral
  requires an accepted amendment there first.
- **CHOT §6.2.1**: "Không nhúng iframe bản đồ, không tải SDK bản đồ bên ngoài",
  and MVP calls no external geocoding API — no key, no cost, no employee
  coordinates sent to a third party.
- **QUY_TAC §10 item 16**: no external geocoding API, no map iframe/SDK
  embedding.
- **Constitution Principle IX**: introducing a tile provider would introduce an
  environment/secret dependency the project has deliberately avoided.

Diagram MVP, mapping directly onto the brief's priority list:

| Brief MVP item | Diagram realization |
|---|---|
| user marker | centre-anchored marker at the acquired position |
| target Location marker | marker at the focused Location |
| target geofence radius circle | circle of exactly `radius_m` at the diagram's stated scale — never adjusted by accuracy |
| fit bounds | scale chosen so the user marker, the target marker and the full radius circle are all visible, with a printed metre scale bar |
| accuracy circle (only if straightforward) | included — a translucent circle of `accuracy_m` around the user marker, visually distinct from the geofence circle and labelled as uncertainty, not as a boundary |

Projection: local equirectangular approximation about the diagram centre
(`x = Δlon · cos(lat) · R`, `y = Δlat · R`). At the scale of a single geofence
(tens to hundreds of metres) the distortion is far below one pixel. Distances
*shown as text* always come from the canonical haversine mirror, never from the
projection — the projection is for pixels only.

Explicitly not built: routing, turn-by-turn, panning to arbitrary geography,
basemap imagery, address lookup.

Bundle impact: **zero new bytes of dependency**. The current large SVG component
is decomposed into projection, marker, legend and composition modules to satisfy
clean-code limits, and the diagram is mounted only after disclosure.

### Rationale

The only capability a tile basemap adds over the diagram is recognisable
scenery. It costs an external dependency, a network egress path for employee
coordinates, a possible API key, and a governance violation. The spec already
anticipated this trade and resolved it.

### Alternatives considered

- **Leaflet + OpenStreetMap tiles** (~45 KB gzip, no API key). Rejected: blocked
  by GR-001/CHOT §6.2.1, and every tile request leaks viewport and IP (see §6).
- **MapLibre GL** (~200 KB gzip, WebGL). Rejected: same governance block, larger
  cost, still needs a tile source.
- **Google Maps / Mapbox SDK.** Rejected: governance block plus an API key,
  which Principle IX and CHOT §6.2.1 both rule out.
- **Static tile image via a provider URL.** Rejected: puts precise coordinates in
  a third-party URL — the exact leak FR-032/FR-033 forbid.
- **No visualization at all.** Rejected: FR-025–FR-028 require a spatial view,
  and it is achievable without any of the above.

---

## 6. Map / guidance privacy

### Decision

Because no external host is contacted, the provider-leak analysis closes
trivially — but it is recorded explicitly, because the brief asks for it:

| Would a provider receive… | Answer |
|---|---|
| current coordinates | **No** — no request is made |
| viewport / bounding box | **No** — no request is made |
| client IP | **No** — no request is made |
| query parameters | **No** — no request is made |

Positive rules the implementation must satisfy (FR-031–FR-034):

1. Guidance coordinates live only in React state and are dropped on unmount /
   navigation / logout. No `localStorage`, `sessionStorage`, cookie, IndexedDB or
   Cache Storage write.
2. No `console.*`, logger, or telemetry call receives latitude, longitude, or a
   position object. Diagnostics may report accuracy and status only.
3. Guidance coordinates never appear in a URL — no path, no query string, no
   hash, no `router.push` argument.
4. Guidance coordinates are never sent to the backend outside a punch payload.
5. **No external map link is built from a live guidance position** (FR-029a).
   The single canonical link helper stays `backend/attendance/adapters/api/maps.py::attendance_maps_url`,
   applied only to *stored record* coordinates in reports (CHOT §6.2.1, R-42). A
   second copy of that URL template must not appear in the guidance module.
6. Display rounding to six decimals (FR-003a) is **presentation only** and never
   changes the value used for computation or for a punch payload.

Enforcement is not left to review: `tests/architecture/gps-privacy.test.ts`
statically scans `src/features/guidance/**` (and the guidance-touching parts of
`src/features/attendance/**`) for storage APIs, logging calls, URL construction
and `google.com/maps` strings in the same style as the existing
`api-transport-boundary.test.ts` and `origin-proxy-boundary.test.ts` guards.

### Rationale

Constitution Principle VI forbids precise coordinates in audit and observability
surfaces; the spec extends that to client-side persistence. A structural rule
plus a static test is the only version of this that survives future edits.

### Alternatives considered

- **Persisting the last position to speed up the next visit.** Rejected — FR-032
  forbids it, and a cached position is a stale position, which §7 exists to
  prevent.
- **Logging coordinates at debug level only.** Rejected — QUY_TAC §10 item 5 and
  the practical reality that debug logging gets enabled in production.

---

## 7. Attendance integration

### Decision

The required sequence is enforced **structurally**, not by convention:

```text
user opens Attendance screen
  → GuidancePanel: user taps "Bật vị trí"
  → useGuidancePosition acquires ONE bounded fix           (guidance sample)
  → preview rendered: accuracy, nearby list, status, diagram
  → user taps Check In / Check Out
  → AttendancePanel.punch() calls freshCommand(gps.acquire, selectedLocationId)
      ↳ useForegroundPosition.acquire() takes a NEW fix, maximumAge: 0   (business sample)
  → POST /api/v1/attendance/check-in|check-out
  → server: auth → RBAC → boundary (incl. 60 s captured_at freshness)
            → accuracy gate → geofence → candidate resolution → persist + audit
```

The guidance sample and the business sample come from **two different hook
instances with no shared state**. `AttendancePanel` continues to call
`freshCommand(gps.acquire, …)` at the moment of the punch, exactly as it does
today (`frontend/src/features/attendance/model/attendance-state.ts`), and
`features/guidance` exposes no API that could hand a stored snapshot into a punch
payload. Reusing a stale guidance sample is therefore not a discipline the code
must remember — there is no wire to do it through.

Error handling — replacing today's single generic message in
`AttendancePanel.tsx:47` with per-code handling:

| Server outcome | UI response |
|---|---|
| `WEAK_GPS` (422) | "Tín hiệu GPS chưa đủ chính xác" + the measured accuracy against `max_attendance_accuracy_m` + a retry affordance; the guidance panel already predicted this via its quality diagnostic |
| `OUTSIDE_RADIUS` (422) | "Bạn đang ở ngoài mọi địa điểm đã đăng ký" + the guidance nearby list, which shows how far outside and by how much (`distance_to_boundary_m`) |
| `LOCATION_CHOICE_REQUIRED` (409) | render `LocationChoice` from `details.location_candidates` — **server candidates only**, with no guidance substitution, supplementation, filtering or reordering |
| `INVALID_LOCATION_CHOICE` (422) | clear the selection, re-prompt from the server's freshly recomputed candidate set, explain that the position changed |
| `SESSION_ALREADY_OPEN` / `NO_OPEN_SESSION` (409) | refresh today's state and correct the button, since the client's view of the open session was stale |
| success | show a persistent inline action-specific confirmation beside the CTA, clear candidates, refresh today's session/timeline, and leave the preview explicitly advisory |

Authoritative rejection uses the same persistent inline outcome region with the
canonical reason, next step and retry path. It is never mapped onto a browser
acquisition failure. `LocationChoice` remains independent of the preview's
focused target and spatial state.

### Rationale

FR-039–FR-042 and Constitution Principle IV. The preview's whole value is that
it explains a rejection *before* it happens; the moment it can substitute for a
punch sample, it becomes an unaudited authorization path.

### Alternatives considered

- **Reusing the guidance fix when it is younger than 60 s.** Rejected explicitly
  by the brief and by FR-040. It would also be fragile: the 60 s window is a
  server rule that can change, and "fresh enough" client-side is exactly the kind
  of business decision the client must not make.
- **A single shared position hook for both purposes.** Rejected — the shared
  state *is* the leak.

---

## 8. Freshness and state management

### Decision

All guidance state is component-scoped React state in `useGuidance()`
(`model/guidance-state.ts`), with no global store, no persistence, and no
serialization:

| State | Type | Lifetime |
|---|---|---|
| `position` | `GuidancePositionSnapshot \| undefined` | until unmount / refresh replaces it |
| `capturedAt` | ISO string inside the snapshot | same |
| `ageSeconds` / `isStale` | derived from a 1 Hz tick, threshold 60 s | derived |
| `status` | `idle \| prompting \| acquiring \| ready \| error` | same |
| `permission` | `unknown \| prompt \| granted \| denied` | same |
| `error` | tagged browser-error union | cleared on next acquisition |
| `locations` | `LocationSummary[]` from `listLocations({ is_active: true })` | cached for the page; refetchable; contains **no** user coordinates |
| `config` | `{ max_attendance_accuracy_m }` | same |
| `nearby` | derived via `rankNearby`, memoized on `(position, locations, config)` | derived |
| `focusedLocationId` | `number \| undefined` | explicit user override; nearest ranked Location is the derived fallback; cleared on refresh/unmount |

Freshness is *shown*, not enforced: a stale preview is labelled ("cập nhật N
giây trước", visibly degraded past 60 s) with a refresh affordance. It is never
used to permit or block an action — the server's 60 s `captured_at` rule applies
to the punch sample only.

Only `locations` and `config` are non-sensitive and could in principle be cached
across pages; even they are kept in memory, because the directory is 76 rows and
a stale radius would produce a wrong preview.

### Rationale

FR-032 and the brief's "do not persist sensitive GPS state beyond the current
page/session". Component state satisfies this by default — the safe option
requires no extra machinery, which is why it is chosen.

### Alternatives considered

- **A React context provider for guidance.** Deferred: one screen consumes it
  today. If a second consumer appears, a provider can be added without changing
  the persistence rules.
- **`sessionStorage` for the Location directory.** Rejected as unnecessary
  complexity for 76 rows, and it invites someone to store the position beside it.

---

## 9. API contract

### Decision

**No API change.** `contracts/openapi.yaml` is byte-identical after this
feature; no `operationId` is added, renamed or removed; the generated
`frontend/src/shared/api/schema.ts` is unchanged (`npm run api:check` must
produce an empty diff, which the existing `tests/contract/api-generation.test.ts`
already gates).

Feature 006 consumes two existing operations, unchanged and with no new fields:

- `locations_list` — `GET /api/v1/locations/` → `latitude`, `longitude`,
  `radius_m`, `is_active`, `code`, `name`, `address`, `kind`
- `config_retrieve` — `GET /api/v1/config/` → `max_attendance_accuracy_m`

Both are called through the existing
`frontend/src/features/locations/api/location-api.ts`, which goes through
`shared/api/client.ts` → **`authenticatedFetch`**, the single transport
chokepoint. No `fetch`, `XMLHttpRequest`, `axios`, `EventSource`, `WebSocket`,
image beacon or third-party SDK is introduced anywhere in
`features/guidance` — enforced by the existing
`tests/architecture/api-transport-boundary.test.ts`, which the new module falls
under automatically.

FR-038 is satisfied without a schema change: everything the preview needs is
already exposed, so no additional Location data is surfaced.

### Rationale

Constitution Principle VII. The strongest form of "no contract drift" is no
contract change.

### Alternatives considered

- **Adding a lightweight `radius_m`-only listing variant.** Rejected —
  `LocationSerializer` already returns exactly the needed fields, and a second
  shape is drift for its own sake.

---

## 10. Error semantics — three disjoint families

### Decision

Three separate, non-overlapping error vocabularies, in three separate places.
They never share a rendering path, a type, or a message.

**(a) Browser / device errors** — from `GeolocationPositionError`, owned by
`use-guidance-position.ts`, rendered by `PositionStatus`:

| Kind | Trigger | UI |
|---|---|---|
| `PERMISSION_DENIED` | code 1 | explain the browser permission and how to re-enable it; do not auto-retry |
| `UNAVAILABLE` | code 2 | device/OS cannot fix a position; offer retry |
| `TIMEOUT` | code 3 / 15 s elapsed | offer retry, suggest moving outdoors |
| `UNKNOWN` | anything else | generic retry |

**(b) Preview data-read errors** — from `locations_list` / `config_retrieve`
through the existing `parseApiResultFailure` path: authentication
(`INVALID_TOKEN` → handled by `authenticatedFetch`'s refresh, then logout),
permission (`PERMISSION_DENIED` → the guidance surface is simply not offered),
validation (`SERVER_OWNED_FIELD` etc.), and 5xx (retry). These degrade the
*directory*, not the position: a position with no directory shows coordinates and
accuracy with a "không tải được danh sách địa điểm" notice.

**(c) Attendance rejection codes** — `WEAK_GPS`, `OUTSIDE_RADIUS`,
`LOCATION_CHOICE_REQUIRED`, `INVALID_LOCATION_CHOICE`, `SESSION_ALREADY_OPEN`,
`NO_OPEN_SESSION` — owned exclusively by `AttendancePanel` (§7), rendered in the
attendance area, and always attributed to the server.

**Conflation is forbidden and testable.** A browser `TIMEOUT` must never be
presented as `WEAK_GPS`; a preview that computes `OUTSIDE_GEOFENCE` must never
be presented as the server code `OUTSIDE_RADIUS`. The preview's own vocabulary is
the domain enum (`INSIDE_GEOFENCE` / `OUTSIDE_GEOFENCE`) plus a quality
diagnostic, and the guidance module never imports an attendance error code.

### Rationale

The three families have different owners, different remedies, and different
authority. Merging them is what makes GPS failures feel like arbitrary rejections
— the problem this feature exists to fix.

### Alternatives considered

- **One flattened error union for the screen.** Rejected: it makes the
  authority of each message invisible at the type level, which is precisely
  where the confusion starts.

---

## 11. Testing strategy

### Decision

**Frontend unit / component (`frontend/tests/unit/guidance/`)** — with
`navigator.geolocation` stubbed:

- acquisition loading state; success renders position, accuracy, capture time
- `PERMISSION_DENIED`, `UNAVAILABLE`, `TIMEOUT`, unknown error — each renders its
  own message and offers the correct affordance
- explicit refresh replaces the snapshot and resets age
- watch teardown: `clearWatch` called on first fix, on error, on
  `visibilitychange` hidden, on unmount, and before a second `acquire()`
- staleness: age crosses 60 s → stale indication appears; **no** action is blocked
- nearest Location rendered with distance, radius and status
- multiple nearby entries ordered ascending by distance
- **overlapping Locations**: two containing Locations both listed, neither marked
  as the resolved answer, cap does not drop either (FR-013)
- cap behaviour: more than five nearby → exactly five, unless more than five
  contain the position, in which case all containing entries are retained and the
  list exceeds five (FR-013)
- no maximum distance filter: a very distant Location still appears when fewer
  than five are nearer (FR-013a)
- target selection sets focus and re-renders the diagram; clearing focus works
- weak accuracy: `accuracy_m > max_attendance_accuracy_m` → warning, and the
  radius test is unchanged (accuracy never subtracted)
- diagram boundaries: radius circle equals `radius_m` at the stated scale; user
  marker, target marker and full circle all within the viewBox; accuracy circle
  is visually distinct from the geofence circle; renders with no target focused;
  renders with coincident user/target coordinates without dividing by zero

**Geometry parity (`frontend/tests/contract/geofence-parity.test.ts`)** — reads
`contracts/fixtures/geofence-distance.json` and asserts every case within the
stated tolerance (FR-043a).

**Privacy static checks (`frontend/tests/architecture/gps-privacy.test.ts`)** —
scan the guidance sources for: `localStorage` / `sessionStorage` / `document.cookie`
/ `indexedDB`, `console.*` or logger calls receiving a position, coordinate
interpolation into a URL or `router.push`, and any `google.com/maps` literal
(FR-029a — the canonical helper stays server-side).

**Backend** — no preview endpoint exists, so the endpoint checklist (auth, RBAC,
DTO validation, active filtering, nearest ordering, no-writes) is **not
applicable**. What replaces it:

- `backend/tests/contract/locations/test_geofence_distance_fixture.py` — the same fixture
  asserted against `haversine_distance_m` / `classify_geofence`, covering the
  known coincident pair (`HCM000079` / `HCM010005`), the three overlapping pairs,
  exact-boundary positions (`distance_m == radius_m` → INSIDE), duplicate
  coordinates, and antipodal/zero-distance edge cases
- `backend/tests/integration/postgres/locations/test_guidance_reads_create_no_records.py` — issuing the
  guidance reads (`locations_list`, `config_retrieve`) as an employee creates
  **zero** `Attendance`, `AttendanceAttempt`, `AttendanceSession`, `TaskUpdate`
  and `AuditLog` rows (PostgreSQL, per Principle XI)

**Integration / behavioural**:

- opening the guidance panel creates no `AttendanceAttempt` (asserted by row
  count before/after)
- refreshing guidance N times creates no `AttendanceAttempt`
- a punch invokes geolocation acquisition **again** — asserted by spying on the
  geolocation stub and requiring a second call after the preview already holds a
  position, with a `captured_at` strictly newer than the preview's
- a stale preview cannot authorize: with a preview snapshot older than 60 s in
  state, the punch payload still carries the fresh sample; and a directly-posted
  stale `captured_at` is rejected by the server's existing freshness rule

**Extended existing tests**: `tests/unit/attendance/attendance-panel.test.tsx`
gains one case per Attendance error code (§10c) replacing the single generic
message.

### Rationale

Principle XI: geometry is tested where geometry lives (both languages, one
fixture); UI behaviour at the component layer; write-absence against a real
database, because "no rows were created" is only meaningful against a real
transaction.

### Alternatives considered

- **A cross-language golden test that shells out to Python from vitest.**
  Rejected: slow, environment-fragile, and no stronger than a committed fixture
  both sides read.

---

## 12. Performance

### Decision

Plain O(n) computation over the in-memory array of 76 Locations. No spatial
index, no PostGIS, no geohashing, no external location service, no Web Worker.

Measured budget: 76 haversine evaluations plus a sort is on the order of tens of
microseconds in a browser — several orders of magnitude below one frame. The
directory is fetched once per page and reused across every refresh, so a position
refresh costs one geolocation fix and one recompute, with no network I/O.

The Location set is a **closed canonical set of 76 rows** (CHOT §3.1,
QUY_TAC §2). Introducing spatial infrastructure for 76 rows would add a
PostgreSQL extension, migrations, a deployment dependency and a second geometry
implementation — all of it to optimize a computation that is already free, and
all of it in violation of the brief's explicit prohibition absent evidence of
need. No such evidence exists.

Re-evaluation trigger, recorded so the decision is falsifiable: if the Location
set ever grows beyond roughly 10,000 rows, or if per-frame recomputation ever
appears in a profile, revisit — starting with memoization and a bounding-box
pre-filter, and only then with server-side or spatial infrastructure.

### Alternatives considered

- **PostGIS + `ST_DWithin`.** Rejected — no endpoint exists to run it in, and
  the dataset does not justify it.
- **Precomputed distance matrix.** Rejected — the user's position is the variable
  side; there is nothing to precompute.

---

## 13. Migration

### Decision

**Feature 006 requires no business-data migration.** No new model, no new field,
no new index, no new constraint, no backfill, no data transformation. The
`migrations/` directories of every backend app are untouched.

Every entity in the spec's Key Entities section (Guidance Position Snapshot,
Nearby Location View, Guidance Status, Focused Target) is ephemeral client view
state, as `data-model.md` records.

This also satisfies QUY_TAC §10 item 16's prohibition on `maps_url` /
`resolved_address` as DB columns — no such column is contemplated.

### Rationale

FR-035 and Constitution Principle VIII. A feature that persists nothing has
nothing to evolve.

### Alternatives considered

- **Persisting a "last known Location" per user for faster preview.** Rejected —
  it is precisely the stored GPS the privacy requirements forbid, and a stale
  value is worse than no value.

---

## 14. Documentation

### Decision

Documentation updates scoped to this feature (content authored during
implementation, not here):

1. **Feature documentation** — `specs/006-location-geofence-guidance/` artifacts
   (this plan, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`)
   plus a short entry in the frontend feature README describing
   `features/guidance/` and its module boundaries.
2. **User-facing GPS guidance behaviour** — how to enable location, what the
   accuracy diagnostic means, why a preview can say "inside" while a punch is
   still rejected (the position moved, or the sample was weak), and what each
   browser error means and how to recover. Vietnamese, matching the existing UI
   copy.
3. **Privacy notes** — a plain statement that the position is used only on the
   device, is never stored, never logged, never placed in a URL, and never sent
   to any third party or map provider; that no external map service is contacted;
   and that coordinates leave the device only as part of an explicit Check In /
   Check Out.
4. **Preview vs Attendance validation** — a short, prominently placed section
   stating that guidance is informational, that Attendance re-acquires GPS and
   re-validates server-side at punch time, and that a preview result never
   authorizes attendance. This distinction is repeated in the UI itself (FR-042),
   not only in documentation.
5. **Governance note** — record that interactive tile/SDK maps remain deferred
   under GR-001 (resolved by deferral) and that the shipped spatial view is a self-contained diagram, so
   a future reader does not mistake the absence of a basemap for an oversight.

### Rationale

Principle I keeps governance decisions traceable; SC-009 depends on users
actually understanding the preview/authoritative split, which is a documentation
and copy obligation as much as a code one.

---

## 15. Frontend baseline and reusable component boundary

### Decision

Refactor the current Attendance and guidance UI in place. Keep the established
`features/<name>/{api,model,ui}` convention and the existing `features/guidance`
feature name. Introduce shared UI only for responsibilities with demonstrated
cross-screen reuse: Button, Card, Badge, SectionHeading, the existing
AsyncState family, and the employee application shell. Do not add a second
`location-guidance` feature, a parallel Attendance wrapper, or a generic
Dialog/Sheet without a second use case.

`LocationSummaryCard`, `NearbyLocations`, and `NearbyLocationItem` form a
presentation-only reuse seam: their props contain Location display data and
already-derived status, never Attendance commands, capability rules, or
Attendance-specific thresholds. A future Task Evidence composition may import
these presentations without copying markup, while its distinct GPS thresholds
and evidence policy remain Task-owned.

Repository inspection found:

- no application shell, AppHeader, bottom navigation, navigation rail, brand
  component, or employee route registry;
- no Tailwind, CSS-in-JS, icon, map, or UI component dependency;
- only `shared/ui/async-state` as a shared UI component;
- repeated raw `<button>`, card classes, page `<main><h1>` markup, and raw colors;
- useful guidance model separation already present, but broad presentation in
  `GuidancePanel`, `PositionStatus`, and `SpatialDiagram`;
- Attendance orchestration, command state, CTA, result, and history combined in
  `AttendancePanel`.

### Rationale

This keeps the already tested acquisition, geometry, and command behavior while
moving composition and visual semantics to cohesive owners. It prevents both a
new monolith and a speculative design system larger than the current product.

### Alternatives considered

- **Wrap the current panels in a new designed page.** Rejected because two
  parallel presentation/state trees would retain the monolith and duplicate
  markup.
- **Adopt a third-party component library.** Rejected because the required
  primitive set is small and no runtime dependency is justified.
- **Create every conceptual component named in the brief.** Rejected; final
  boundaries follow actual reuse and state ownership.

---

## 16. Application shell and authorization-aware navigation

### Decision

Mount one employee `ApplicationShell` from a URL-neutral App Router route-group
layout. The shell owns the MobiFone brand slot, page context, back action,
authenticated avatar/account entry, content container, safe areas, and one
responsive navigation component. A single navigation registry contains stable
label/order, implemented route, and required capability; it emits only entries
whose route exists and whose capability is held. Route boundaries and backend
authorization remain mandatory.

Phones render the registry as bottom navigation; tablets and desktop render the
same data as a rail. Today only Attendance among the requested four employee
destinations has an implemented route. Tasks, Reports, and Account are not
placeholder links. The header may show initials/full name and existing account
actions; it must not imply a self-profile route that does not exist.

### Rationale

One registry prevents label/order/authorization drift between two responsive
navigation presentations. Capability filtering improves UX but does not become
the security boundary.

### Alternatives considered

- **Copy header and bottom navigation into each page.** Rejected as the exact
  duplication FR-054/FR-056 prohibit.
- **Render unauthorized items disabled or locked.** Rejected because it exposes
  unsupported capabilities and contradicts the clarified requirement.
- **Add Tasks/Reports/Account placeholder routes.** Rejected; their product
  behavior belongs to owning features.

---

## 17. Styling, design tokens, and MobiFone asset

### Decision

Use semantic CSS custom properties imported by `app/globals.css`, with
co-located CSS Modules for shared shell/primitives and feature UI. Tokens cover
brand primary, critical, success, neutral background, surface, primary and
secondary text, border, focus ring, spacing scale, touch target, radii,
typography, navigation size, and readable content widths. Components consume
tokens and do not contain raw color literals.

No approved MobiFone logo, logo variant, `field-clarity.html`, or reference
screenshot exists in the repository. Plan a single `MobiFoneLogo` consumer and
one canonical local asset path only after the approved file and intended header
variant are supplied. Preserve intrinsic dimensions/aspect ratio, use
`object-fit: contain`, meaningful `alt="MobiFone"`, and responsive size tokens.
Do not download, redraw, inline as base64, or duplicate the asset.

### Rationale

CSS variables fit the current zero-library styling architecture and make brand
and state semantics auditable. Treating the missing asset as a delivery gate is
safer than guessing brand artwork or color values.

### Alternatives considered

- **Add Tailwind or a theme package.** Rejected because the repository does not
  use it and the new dependency would not improve the small token surface.
- **Use component-local hexadecimal values.** Rejected because brand/state
  changes would drift.
- **Fetch a public logo URL.** Rejected by FR-055 and the asset-provenance rule.

---

## 18. Attendance composition and presentation-ready state

### Decision

Move today-load, processing, authoritative outcome, and candidate orchestration
from `AttendancePanel` into an Attendance-owned experience hook/view model.
Keep `useForegroundPosition` and `freshCommand` as the punch-only acquisition
path. `AttendancePanel` becomes a thin ordered composition:

1. Attendance context header (focused/nearest Location and open-session state);
2. GPS status card (Feature 006 view state);
3. primary Attendance action;
4. persistent inline authoritative outcome;
5. compact Location summary and nearby disclosure;
6. progressively disclosed spatial panel;
7. diagnostics/troubleshooting and daily/session history.

Guidance keeps its independent acquisition and returns a presentation-ready
closed state. `GpsStatusCard` accepts accuracy, threshold, status and label; it
does not calculate canonical authorization. Preview focus and the server's
`LOCATION_CHOICE_REQUIRED` selection stay distinct.

### Rationale

The split preserves the two mandatory GPS lifecycles while preventing browser,
API, formatting, spatial, command, navigation, and all markup from accumulating
in one component.

### Alternatives considered

- **Share the preview snapshot with the punch CTA.** Rejected as a correctness
  and privacy violation.
- **Let GPS presentation compute readiness from raw inputs.** Rejected because
  view components must consume calculated view state.
- **Merge preview target selection with server candidates.** Rejected because
  preview focus is non-authoritative.

---

## 19. Responsive and accessible interaction

### Decision

- 320–375 px: single source/visual column, compact gutters, full-width primary
  CTA, bottom navigation with safe-area padding, disclosures closed.
- approximately 390–430 px: same order/behavior with moderately larger gutters;
  no second column.
- tablet (content-driven switch near 48 rem): navigation rail and at most two
  regions after the primary CTA.
- desktop: rail plus centered bounded content, at most two regions, bounded CTA
  and card widths.

Use one DOM order across breakpoints. Native button/link/radio/details semantics
are preferred; `:focus-visible`, `aria-current`, accessible names, labelled
regions, at least 44 px touch targets, color-independent text/icon/shape cues,
and reduced-motion behavior are required. Meaningful transitions are announced
once; the one-second age counter is outside live regions. Text Location data and
focus controls remain the canonical alternative to the SVG.

### Rationale

One semantic order prevents visual reflow from corrupting keyboard/screen-reader
order. Content-driven breakpoints satisfy the clarified viewport behavior
without treating the reference as a fixed canvas.

### Alternatives considered

- **Duplicate mobile and desktop markup.** Rejected because state, navigation,
  accessible names, and focus behavior would drift.
- **Exact screenshot/pixel acceptance.** Rejected; behavior and semantic order
  are the contract.
- **Make tiny SVG markers the only controls.** Rejected; textual native controls
  remain available, and decorative markers need no button semantics.

---

## 20. Spatial isolation and perceived performance

### Decision

Keep the existing self-contained SVG behind `SpatialPanel -> SpatialDiagram`.
This is the feature adapter boundary; no provider abstraction, provider type,
SDK, iframe, tile source, or external dependency is added under GR-001.
`SpatialPanel` is collapsed by default on phones and mounts/imports the diagram
only after disclosure. Geolocation and Attendance command code remain client
boundaries; the route layout and inert presentation primitives remain
server-renderable where possible.

Fetch Location and Config concurrently as today, but coalesce their load within
one mounted guidance experience and suppress duplicate retry/acquisition
requests. Reserve stable status/action regions. Skeletons are used only where
structure is predictable and always include status text. Perceived speed never
reuses an old GPS sample for a punch.

### Rationale

The local SVG already satisfies the user need and governance constraint. Lazy
disclosure keeps secondary code/work off the critical path without weakening
GPS correctness.

### Alternatives considered

- **Introduce a generic map-provider interface now.** Rejected as speculative
  abstraction around a forbidden provider.
- **Render the diagram before disclosure.** Rejected because it adds secondary
  work and mobile length before the primary action.
- **Cache/reuse preview GPS for speed.** Rejected by FR-039.

---

## 21. UI verification architecture

### Decision

Use five layers:

1. pure/view-model tests for closed state mapping, threshold/boundary behavior,
   default visible rows, nearest target, and request supersession;
2. presentation tests by role/name/text for primitives, GPS states, disclosure,
   View more, recovery, and accessible announcements;
3. guidance integration tests with mocked geolocation and real feature state for
   reference loading, refresh, target selection, overlap, and privacy;
4. Attendance integration tests for fresh punch acquisition, action-specific
   headline/processing, persistent success/rejection, capability hiding, and
   separation from preview focus;
5. shell/architecture/browser checks for one navigation registry, implemented +
   capability filtering, token usage, responsive mode, overflow, safe areas,
   keyboard order, contrast, and reduced motion.

Vitest/Testing Library remain the semantic unit/integration tools. Exact CSS
pixels and screenshot matching are not acceptance assertions. Because jsdom
cannot prove media queries, sticky/fixed layout, overflow, safe areas, actual
tab order, or contrast, add `@playwright/test` plus `@axe-core/playwright` as
scoped development-test dependencies. They are not runtime UI dependencies and
must not introduce a map/provider package.

### Rationale

Each promise is tested at the boundary that can observe it, while visual
reference drift does not create brittle tests.

### Alternatives considered

- **Assert CSS class names and exact sizes in component tests.** Rejected as
  brittle and unable to prove user behavior.
- **Rely only on jsdom.** Rejected for responsive/layout/accessibility claims it
  cannot evaluate.
- **Use screenshot comparison as the primary contract.** Rejected because the
  reference is inspirational, not pixel-perfect.

---

## Resolved unknowns

| Question | Resolution |
|---|---|
| Backend preview endpoint required? | **No** — §2 |
| Which map library? | **None** — §5 |
| Is `watchPosition` acceptable? | **Yes, bounded single-shot only** — §3 |
| How is client geometry kept honest? | **Committed shared fixture, asserted in both languages** — §2, §11, `contracts/geofence-distance-fixture.md` |
| Any schema change? | **None** — §13 |
| Any OpenAPI change? | **None** — §9 |
| Shared shell or UI library already present? | **No** — §15 |
| Refactor or wrap existing Attendance? | **Refactor in place around explicit ownership** — §15, §18 |
| Styling/token technology? | **CSS custom properties + co-located CSS Modules; no Tailwind/library** — §17 |
| Approved logo/reference present? | **No; approved local asset is a delivery gate** — §17 |
| Navigation behavior? | **One implemented-route + capability-filtered registry** — §16 |
| Responsive shell? | **Phone bottom nav; tablet/desktop rail, at most two regions** — §19 |
| Map/provider architecture? | **Local progressive SVG boundary only; no provider abstraction** — §20 |
| UI testing strategy? | **Layered semantic + browser-level responsive/accessibility checks** — §21 |

No open clarification markers remain.
