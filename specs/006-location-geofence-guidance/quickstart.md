# Quickstart: Location Awareness and Geofence Guidance

**Feature**: 006 | **Branch**: `feature/006-location-geofence-guidance` | **Date**: 2026-08-20

A validation guide for verifying Feature 006 end to end. It proves the two
things that matter: the preview is useful, and the preview is **not**
authoritative.

## Prerequisites

- An untracked `.env` at the repository root, created from `.env.example`.
  `core/deployment.py` reads `os.environ` only — nothing autoloads a dotenv — so a
  `manage.py` command run without it stops on the first missing key
  (`ConfigurationError: invalid configuration: APP_ENV`).
- Backend running with the seeded canonical 76-`Location` set and a `Config` row
  with `max_attendance_accuracy_m`.
- Frontend served over **HTTPS or `localhost`** — browsers refuse the Geolocation
  API otherwise.
- A user account holding `attendance.check_in.self` / `attendance.check_out.self`
  and read access to Locations and Config.
- Browser DevTools able to override geolocation (Chrome: *More tools → Sensors*;
  Firefox: `geo.provider.network.url` override).
- The approved local MobiFone logo asset and intended header variant. If these
  have not been supplied, shell behavior may be validated but FR-055 logo
  acceptance MUST be reported blocked; do not substitute a remote asset.

## Setup

```bash
# backend — load the runtime environment first, from the repository root
set -a && . ./.env && set +a
cd backend
uv run python manage.py migrate          # Feature 006 adds none; on a current database
                                         # this reports "No migrations to apply"
uv run python manage.py runserver

# frontend
cd frontend
npm install                              # expect: no new runtime UI/map dependency
npm run dev
```

## Automated verification

```bash
# Frontend: unit, component, contract and architecture suites
cd frontend
npm run test
npm run api:check        # MUST report no diff — Feature 006 changes no API contract
npm run lint
npx tsc --noEmit

# Backend: geometry parity + no-write guarantees (PostgreSQL required)
cd backend
uv run pytest tests/contract/locations/test_geofence_distance_fixture.py -v
uv run pytest tests/integration/postgres/locations/test_guidance_reads_create_no_records.py -v

# Lint and types use the repository gates, run from the repository root. `ruff
# check .` and `mypy .` inside backend/ are not those gates: they sweep in the
# test tree and report pre-existing findings unrelated to this feature.
cd ..
uv run --project backend ruff check backend scripts
uv run --project backend mypy backend/core backend/config backend/operations \
  backend/identity backend/audit backend/locations backend/attendance scripts
```

Expected: all green, and `api:check` explicitly clean. A non-empty `api:check`
diff means someone added an endpoint this feature must not have.

## Scenario 1 — Acquire a position and read the preview (US1, SC-001, SC-002)

1. Open the Attendance screen. The guidance panel shows an idle state; **no
   permission prompt has appeared yet**.
2. Tap *Xem vị trí*. The browser permission prompt appears only now.
3. Grant permission. An acquiring state is shown, then within 15 s the default
   view shows the focused/nearest Location, `accuracy_m`, threshold, readiness,
   distance, and the primary Attendance action. Coordinates, capture time and
   exact diagnostics remain inside the labelled details disclosure.
4. The collapsed nearby list shows every containing Location plus nearest
   outside entries until at least three rows are visible. If more computed rows
   exist, “View more” reveals them; collapse never hides a containing row.

**Pass**: the panel answers "where am I relative to a registered Location, and
would a punch succeed" without any punch being made.

## Scenario 2 — Every browser failure mode is distinct (US2, SC-011)

Using DevTools, force each condition and confirm a **distinct** message plus the
correct affordance:

| Forced condition | Expected |
|---|---|
| Deny the permission prompt | permission-denied message explaining how to re-enable; no auto-retry loop |
| Location unavailable | unavailable message with a retry button |
| No fix within 15 s | timeout message with a retry button |
| Grant, then tap refresh | a **new** capture time and reset age |

**Pass**: none of these messages mentions `WEAK_GPS`, `OUTSIDE_RADIUS`, or any
other Attendance code. Browser errors and server rejections are separate
vocabularies.

## Scenario 3 — Overlapping and coincident Locations (US3, SC-007)

1. Override position to a point inside two overlapping registered geofences.
2. Both Locations appear, both badged INSIDE.
3. The nearest entry is the automatic **visual target** and is labelled as
   display focus only. No Attendance candidate is auto-selected.
4. The computed-list cap does not drop either containing Location: add distant
   Locations until more than five are nearby and confirm both INSIDE entries
   survive.
5. Override to the coincident pair `HCM000079` / `HCM010005` and confirm both are
   listed while both are active.

**Pass**: the preview presents ambiguity honestly instead of resolving it.

## Scenario 4 — No maximum distance filter (FR-013a)

1. Override position to a remote point with fewer than five Locations nearby.
2. Expand **View more** when it is present. The computed list still contains up
   to five entries, including far ones, each with its real distance.

**Pass**: the list never goes empty merely because the user is far away.

## Scenario 5 — The preview never authorizes (US4, SC-003, SC-008) — critical

1. Acquire a position and let the preview go stale (wait past 60 s; the panel
   shows a stale indicator).
2. In DevTools, set a breakpoint or spy on `navigator.geolocation` and note the
   call count.
3. Tap Check In.
4. Observe: geolocation is invoked **again**, and the outgoing request body
   carries a `captured_at` strictly newer than the preview's.

```bash
# While performing step 3, confirm no attempt row was created by merely viewing:
set -a && . ./.env && set +a          # from the repository root
cd backend
uv run python manage.py shell -c "from attendance.models import AttendanceAttempt; print(AttendanceAttempt.objects.count())"
```

5. Record that count **before** opening the guidance panel and **after**
   refreshing it several times without punching. The two numbers must be equal.

**Pass**: opening and refreshing guidance creates zero `AttendanceAttempt`,
`Attendance`, `AttendanceSession`, `TaskUpdate` and `AuditLog` rows, and a stale
preview cannot supply the business GPS sample.

## Scenario 6 — Attendance error codes are presented as server decisions (SC-011)

Force each server outcome and confirm the message is attributed to the server
and distinct from any browser error:

| Force | Expected UI |
|---|---|
| accuracy worse than `max_attendance_accuracy_m` | `WEAK_GPS` message quoting the measured accuracy vs the threshold — the guidance quality diagnostic already warned about this |
| position outside every geofence | `OUTSIDE_RADIUS` message; the nearby list shows how far outside |
| position inside two active geofences | `LOCATION_CHOICE_REQUIRED` → candidate chooser rendered **from the server's `details.location_candidates`** |
| choose a candidate, then move outside before confirming | `INVALID_LOCATION_CHOICE` → selection cleared, re-prompt from the recomputed set |
| check in twice | `SESSION_ALREADY_OPEN` → today's state refreshed and the button corrected |
| valid punch | persistent inline success beside the CTA naming the action and refreshed session state; preview remains advisory |

**Pass**: the candidate list always matches the server's, never the preview's.

## Scenario 7 — Spatial diagram (US5, SC-005, SC-015)

1. Confirm the spatial panel is collapsed by default and no external/spatial
   resource is loaded before it is opened.
2. Open it and focus a Location in the nearby list. The diagram renders: user
   marker, accuracy circle, target marker, geofence
   circle sized to `radius_m`, and a metre scale bar — with all of them visible.
3. Confirm the geofence circle is **not** shrunk or grown by `accuracy_m`; the
   accuracy circle is visually distinct.
4. Focus a Location at the same coordinates as the user and confirm the diagram
   still renders sanely.

## Scenario 8 — Privacy verification (SC-004) — critical

With the guidance panel open and a position acquired:

1. **DevTools → Network**: filter to *All*. Guidance itself may trigger only
   `/api/v1/locations/` and `/api/v1/config/` through the app's own origin;
   Attendance today/punch requests remain the separate existing flow.
   **No request to any tile, map, geocoding or analytics host exists.** Setting
   the network filter to third-party origins must yield an empty list.
2. **DevTools → Application → Storage**: Local Storage, Session Storage, Cookies,
   IndexedDB and Cache Storage contain **no** latitude, longitude or position
   object. Search each store for the leading digits of the current latitude —
   zero hits.
3. **DevTools → Console**: no coordinate appears in any log line during
   acquisition, refresh, focus or diagram render.
4. **Address bar**: the URL contains no coordinate in its path, query or hash,
   before or after focusing a target.
5. **Page source**: no `google.com/maps` link is built from the live position
   (FR-029a). Stored-record map links in reports are unaffected and still come
   from the single canonical server-side helper.
6. Navigate away and back: the position is **gone** and must be re-acquired.

```bash
# Static counterpart of steps 2-5, run in CI. Steps 2-4 are gps-privacy.test.ts;
# step 5 — the map link of FR-029a — is guidance-boundary.test.ts.
cd frontend
npx vitest run tests/architecture/gps-privacy.test.ts \
               tests/architecture/guidance-boundary.test.ts
```

## Scenario 9 — Cross-language geometry parity (FR-043, FR-043a)

```bash
cd backend  && uv run pytest tests/contract/locations/test_geofence_distance_fixture.py -v
cd frontend && npx vitest run tests/contract/geofence-parity.test.ts
```

Both must pass against the **same** `contracts/fixtures/geofence-distance.json`,
within the fixture's stated tolerance. Then verify by hand that a preview
distance shown in the UI matches the `distance_m` the server returns in a
`LOCATION_CHOICE_REQUIRED` candidate for the same position.

**Pass**: the client mirror and the canonical geometry agree.

## Scenario 10 — No migration (FR-035)

```bash
set -a && . ./.env && set +a          # from the repository root
cd backend
uv run python manage.py makemigrations --check --dry-run
```

**Pass**: reports no changes. Feature 006 requires no business-data migration.

## Scenario 11 — Shared shell and authorization-aware navigation (FR-054–FR-056)

1. Open Attendance as each canonical role/capability set.
2. Confirm one MobiFone header/account entry and one primary navigation are
   mounted; page markup does not contain a second shell.
3. Confirm only implemented routes for which the account holds the required
   capability appear. Tasks, Reports, and Account are absent while those routes
   are unimplemented; no disabled placeholder implies access.
4. Confirm Attendance route protection still rejects an unauthorized direct URL
   even if navigation markup is manipulated.

**Pass**: one navigation definition supplies stable order/labels to both
responsive presentations, while route/backend authorization remains effective.

## Scenario 12 — Responsive layout matrix (FR-059)

Exercise widths 320, 375, 390, 430, approximately 768, 1280 and 1440 CSS pixels.

| Width | Expected |
|---|---|
| 320–430 | one column, full-width bounded CTA, safe-area-aware bottom navigation, closed details/spatial disclosures, no horizontal overflow |
| tablet | navigation rail; primary flow first; optional second region only after CTA |
| desktop | rail; centered bounded content; at most two regions; controls do not stretch excessively |

At every width, enlarge text and use long Location/address content. Confirm no
clipping, shell overlap, hidden CTA, duplicated markup, or focus-order change.

**Pass**: behavior and semantic order are stable; only layout density/navigation
presentation changes.

## Scenario 13 — Complete visual-state matrix (FR-052–FR-053)

Force each state and verify the wording, non-color cue, and next action defined
in [`contracts/frontend-ui.md`](./contracts/frontend-ui.md): idle, reference
loading, requesting, refreshing, ready, weak GPS, outside radius, overlap, stale,
permission denied, unavailable, timeout, unknown acquisition failure, reference
failure, Attendance processing, success, and rejection.

Additional checks:

- `Đang Check In…` / `Đang Check Out…` replaces the active CTA label and duplicate
  submission is disabled without moving the CTA region.
- Success and rejection remain inline until the next Attendance action or
  navigation away.
- No device failure is presented with a server Attendance code.

**Pass**: no generic catch-all or empty normal screen represents a known state.

## Scenario 14 — Keyboard and assistive technology (FR-060–FR-063)

1. Traverse header, navigation, CTA, Refresh, View more, target selection,
   diagnostics and spatial disclosure using keyboard only.
2. Confirm visible focus, logical source order, native Enter/Space behavior,
   `aria-current` on navigation, and accessible names on every action.
3. With a screen reader, confirm meaningful state transitions announce once;
   the one-second age counter does not repeatedly announce.
4. Remove color cues and confirm readiness, errors, containment, overlap,
   selection, and radius/accuracy meanings remain available through text and
   icon/shape/numeric cues.
5. Enable reduced motion and confirm no necessary information disappears.

**Pass**: the textual Location list/details provide the full spatial alternative
and no keyboard trap or color-only meaning exists.

## Scenario 15 — Tokens and approved brand asset (FR-055, FR-057–FR-058)

1. Inspect feature and shared component styles: brand/status/surface colors,
   spacing, radii and typography reference semantic CSS custom properties.
2. Confirm no new component-scoped hexadecimal brand/status value exists.
3. Verify the single approved local logo has recorded provenance, meaningful alt
   text, declared intrinsic size, preserved aspect ratio, responsive header size
   and clear space.
4. Confirm no remote logo URL, repeated inline base64, cropped copy, or duplicate
   asset exists.

**Pass**: shared tokens are the only visual source. If the approved asset is
still absent, mark only logo acceptance blocked and do not improvise one.

## Scenario 16 — Loading and perceived performance

1. Open Attendance and confirm no guidance GPS request occurs before the
   explicit user action.
2. Trigger guidance once and confirm Location/Config reads run concurrently and
   rapid repeat activation does not create duplicate active acquisitions.
3. Confirm loading/refresh/processing retain stable status and CTA regions with
   understandable status text.
4. Confirm the spatial module is not mounted/imported before disclosure.
5. Punch after any preview and confirm a new GPS acquisition still occurs.

**Pass**: secondary work is deferred and duplicate work suppressed without
reusing a preview sample or weakening canonical GPS correctness.

## Scenario 17 — Radius versus GPS uncertainty comprehension (SC-015)

1. Prepare the spatial view with both the allowed Location radius and GPS
   accuracy uncertainty visible, then remove color cues while retaining shapes,
   line treatments, legend text, and textual Location alternatives.
2. Run ten moderated participant sessions. Ask each participant to identify
   which boundary is the allowed Location radius and which is GPS uncertainty,
   and to explain the difference using the legend or textual alternative.
3. Record aggregate pass/fail only in `trial-results.md`; do not record identity,
   coordinates, screenshots containing coordinates, or free-form responses that
   could identify a participant.
4. Require at least nine of ten participants to identify both meanings
   correctly. A partially correct answer is a failure for this criterion.

**Pass**: at least 9/10 participants distinguish both circles without color.

## Completion checklist

- [ ] Default hierarchy shows Location, Attendance state, GPS readiness and CTA before details
- [ ] Coordinates/time/diagnostics and spatial view are progressively disclosed
- [ ] Collapsed nearby list keeps all containing Locations and at least three rows; View more works
- [ ] All four browser error modes distinct and recoverable
- [ ] Overlapping and coincident Locations both listed; nearest visual focus resolves no candidate
- [ ] Five-entry cap never drops a containing Location; no max-distance filter
- [ ] Punch re-acquires GPS; stale preview never supplies the business sample
- [ ] Guidance creates zero business records
- [ ] Every Attendance error code has its own server-attributed message
- [ ] Diagram renders with radius unmodified by accuracy; no external request
- [ ] Shared shell/nav is single-source, responsive and capability-filtered
- [ ] Check-In/Out headlines, processing labels and persistent inline outcomes match the contract
- [ ] All visual states are distinct and recoverable where applicable
- [ ] Responsive, keyboard, focus, contrast, safe-area and reduced-motion checks pass
- [ ] At least 9/10 moderated trials distinguish allowed radius from GPS uncertainty without color
- [ ] Design tokens are centralized; approved local logo passes provenance/aspect/alt checks
- [ ] Zero third-party network requests; zero stored/logged/URL coordinates
- [ ] Geometry parity green in both languages
- [ ] `npm run api:check` clean; `makemigrations --check` clean
