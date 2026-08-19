# Implementation Plan: Location Awareness and Geofence Guidance

**Branch**: `feature/006-location-geofence-guidance` | **Date**: 2026-08-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-location-geofence-guidance/spec.md`

## Summary

Feature 006 gives an employee a **client-side, read-only preview** of where they
are standing relative to the registered `Location` directory, so that a Check
In / Check Out rejection stops being a surprise. The preview shows the acquired
position (accuracy, capture time, freshness), every containing Location plus
nearest outside Locations to a five-entry floor, with distance / radius /
inside-outside status and distance-to-boundary when outside, a GPS-quality
diagnostic against `Config.max_attendance_accuracy_m`, a focusable target, and a
self-contained spatial diagram drawn only from data already held in the browser.

The 2026-08-20 UX extension reorganizes that behavior into a mobile-first,
MobiFone-branded employee shell and a thin Attendance composition. The default
phone view presents Location context, Check In/Check Out state, GPS readiness,
and the primary action before nearby details, diagnostics, and the progressively
disclosed spatial view. Repeated shell and visual responsibilities become shared
primitives; GPS/geofence presentation remains owned by `features/guidance`; the
Attendance command, server outcome, candidate selection, and daily/session
history remain owned by `features/attendance`.

**The single architectural boundary this plan protects**: guidance is a
*preview*. It never authorizes anything. Feature 004 Attendance Core remains the
only authoritative command path — it re-acquires a fresh GPS fix at punch time,
re-runs the canonical gates server-side against a locked reference snapshot, and
owns every `Attendance`, `AttendanceSession`, `AttendanceAttempt` and `AuditLog`
write.

Technical approach, in one line each:

- **No new backend endpoint.** FR-034 forbids transmitting live guidance
  coordinates to the server; the clarification session closed this explicitly.
  Guidance is computed on-device from `GET /api/v1/locations/` and
  `GET /api/v1/config/`, both of which already return every field required.
- **No second geofence implementation.** The client mirrors
  `backend/locations/domain/geofence.py` (same `EARTH_RADIUS_M`, same haversine,
  same two-value classification) and is pinned to it by a **committed shared
  distance fixture** (FR-043a, tolerance 0.001 m) asserted by a backend pytest *and* a frontend
  vitest, with a stated tolerance.
- **No map library, no tiles, no SDK, no iframe, no API key.** GR-001 is
  **resolved by deferral**: interactive maps stay out of scope, and lifting the
  deferral requires an accepted amendment to `docs/CHOT_YEU_CAU.md` §6.2.1; a
  client-rendered SVG diagram satisfies FR-025–FR-028 with zero external
  requests, which makes the map-privacy analysis trivially closed.
- **No new persistent model, no migration.** Every entity in the spec is
  ephemeral React view state.
- **No new HTTP transport.** `authenticatedFetch` remains the only chokepoint.
- **No parallel Attendance page.** Refactor the existing `AttendancePanel` and
  `GuidancePanel` around explicit view-state and presentational boundaries;
  preserve the independent preview and punch acquisition paths.
- **No UI framework added.** The repository uses global CSS and has no Tailwind
  or component library. Add CSS custom-property design tokens and a narrow set
  of shared primitives only where the shell and multiple screens have a clear
  reuse case.
- **No unsupported navigation.** A shared employee navigation registry filters
  implemented destinations through authenticated capabilities. Tasks, Reports,
  or Account entries are not rendered until their routes and owning capability
  rules exist.
- **No guessed branding.** No approved MobiFone logo or Field Clarity artifact
  exists in the repository. Shell structure can proceed with a reserved brand
  slot, but logo acceptance is blocked until an approved local asset and its
  intended header variant are supplied; no remote download or duplicate copy is
  planned.

## Technical Context

**Language/Version**: Backend Python 3.12 (Django + DRF); Frontend TypeScript 5
on Next.js 16.3.1 App Router, React 19.1.1

**Primary Dependencies**: Runtime dependencies remain existing only. Frontend:
`openapi-fetch` 0.14.0 + generated `src/shared/api/schema.ts`, browser
Geolocation API, CSS custom properties, and self-contained SVG. Development
verification adds `@playwright/test` and `@axe-core/playwright` as test-only
dependencies for real-browser responsive and accessibility checks.
Backend: unchanged. **No new runtime dependency is added by this feature** — in
particular no map/tile library, no geocoding client, no geospatial extension.

**Storage**: None. Feature 006 reads two existing endpoints and holds all state
in component memory. No table, no column, no index, no migration.

**Testing**: Frontend `vitest` 3.2.7 + `@testing-library/react` + `jsdom` with a
stubbed `navigator.geolocation` for component/integration semantics;
`@playwright/test` + `@axe-core/playwright` for real-browser viewport, overflow,
keyboard, focus, touch-target, contrast, reduced-motion, and shell-layout
checks. Backend uses `pytest` against PostgreSQL for the shared-fixture
assertion and the no-write integration checks.

**Target Platform**: Modern mobile and desktop browsers with the Geolocation
API, served over HTTPS (required for geolocation permission).

**Project Type**: Web application — `backend/` (hexagonal Django) + `frontend/`
(Next.js), contract-linked through `contracts/openapi.yaml`.

**Performance Goals**: Nearby computation over the closed canonical set of 76
Locations is a single O(n) pass — ~76 haversine evaluations, sub-millisecond in
the browser. Preview must render within one animation frame of a position
update; position acquisition is bounded by a 15 s timeout with an explicit
retry affordance (FR-008).
Opening Attendance MUST NOT start duplicate location requests. The spatial
module is loaded only after the user expands it; shell and primary action remain
interactive without waiting for that module. Loading/refresh states reserve the
primary regions so state transitions do not cause disruptive layout movement.

**Constraints**:
- Live guidance coordinates MUST NOT be sent to the backend (FR-034) and MUST
  NOT reach `localStorage`, `sessionStorage`, cookies, IndexedDB, URLs, logs, or
  telemetry (FR-030, FR-032, FR-033).
- No continuous or background tracking (FR-002, Out of Scope). A bounded
  `watchPosition` is permitted only as a single-shot acquisition that clears
  itself — see research.md §3.
- No external network request may originate from the guidance view (FR-025).
- Guidance MUST NOT create `AttendanceAttempt` or any other business record
  (FR-031).
- Canonical distance semantics are fixed: `EARTH_RADIUS_M = 6_371_008.8`,
  `INSIDE` iff `distance_m <= radius_m`, accuracy is never subtracted from
  radius, and the classification enum stays closed at two values.
- Phone layouts from 320–430 px stay single-column with safe-area-aware bottom
  navigation. Tablets and desktop use a capability-filtered navigation rail and
  at most two content regions without changing semantic reading order.
- Location/GPS status is never communicated by color alone; all controls retain
  keyboard focus visibility, accessible names, and comfortably usable touch
  targets. Reduced-motion preferences disable decorative motion.
- A CSS token is the only source for brand/status/surface colors, spacing,
  radius, and typography values used by the new UI. Feature components do not
  introduce raw hexadecimal colors.

**Scale/Scope**: 76 canonical Locations; one redesigned Attendance surface;
one reusable employee shell; a small shared primitive set; refactoring of the
existing Attendance and guidance UI modules; zero backend production modules,
database objects, or API operations changed.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluated against `.specify/memory/constitution.md` v1.0.1.

| Principle | Gate | Status |
|---|---|---|
| I. Source-of-Truth Governance | Feature honours CHOT → QUY_TAC → PRD authority chain; no requirement invented below the chain | **PASS** — GR-001 in the spec records the governance ceiling and is resolved by deferral (no amendment made); the plan implements that resolution rather than overriding it. CHOT §6.2.1 and QUY_TAC §10 item 16 (no map iframe/SDK, no external geocoding) are respected. |
| II. Fixed Stack & Hexagonal Architecture | Dependencies point inward; no new production stack element | **PASS** — no backend code changes; browser geolocation lives only in `frontend/src/features/*`, never in `backend/*/domain`. Shared UI owns no business state. No runtime dependency is added; the only package additions are scoped browser/a11y development-test tools. |
| III. Layered, Ordered Authorization | Authorization order unchanged and enforced server-side | **PASS** — guidance performs no authorization. The Attendance gate order (auth → RBAC → boundary → accuracy → geofence → resolution) is untouched. Shell navigation uses capabilities only for presentation and never substitutes for route/backend enforcement; unimplemented or unauthorized entries are absent. |
| IV. Server Authority & Boundary Validation | Client never decides business outcomes | **PASS** — the preview is explicitly labelled non-authoritative (FR-039). Every punch re-acquires GPS and is re-validated server-side; a preview result can never substitute for it. |
| V. DB-Backed Invariants & Transactions | Transaction boundaries stated | **PASS (N/A)** — Feature 006 writes nothing, so it opens no transaction. Attendance's existing `unit_of_work_factory()` boundary and locked reference snapshot (R-126) are unchanged. |
| VI. Auditability & Safe Observability | No precise coordinates in audit/telemetry/logs | **PASS** — guidance emits no `AuditLog` (FR-031) and no log line or telemetry event carrying coordinates (FR-033). Enforced by a static architecture test. |
| VII. Stable Generated API Contracts | OpenAPI is the source of truth; drift gated in CI | **PASS** — no operation added or modified. `contracts/openapi.yaml` and the generated client are unchanged; `npm run api:check` must remain a no-op diff, which the existing drift test already asserts. |
| VIII. Safe Schema Evolution | Migrations are additive and reversible | **PASS (N/A)** — no schema change and no migration (FR-035). |
| IX. Secrets & Environment Isolation | No new secret or key | **PASS** — the no-map-provider decision means no API key, tile endpoint, or third-party account. Branding uses only an approved local asset; remote logos and inline base64 copies are forbidden. |
| X. Location & GPS Domain Integrity | Two independent gates; no accuracy subtraction; overlaps valid; no silent nearest resolution | **PASS** — the client mirrors, and is fixture-pinned to, the canonical geometry. Accuracy is shown as a *separate* quality diagnostic and never folded into the radius test. Overlapping Locations are all listed (FR-013 keeps every containing Location) and the preview never auto-picks a winner among them; selection stays a user action carried by `selected_location_id`. |
| XI. Testing at the Correct Layer | Right layer, PostgreSQL where concurrency matters | **PASS** — geometry parity at the fixture layer (both languages), primitive and state semantics at component level, geolocation/target/refresh at feature integration level, fresh-punch authority at Attendance integration level, accessibility and architecture rules at their owning boundaries, and no-write guarantees against PostgreSQL. |
| XII. Canonical Naming | snake_case wire, camelCase TS, unit suffixes | **PASS** — wire fields remain unchanged; new frontend identifiers are camelCase and retain unit suffixes. Semantic CSS tokens centralize visual values, while UI components consume view-state labels rather than inventing business-state strings. |

**Result: no violations. Complexity Tracking stays empty.**

**Post-Phase 1 re-check**: re-evaluated after `research.md`, `data-model.md`,
`contracts/` and `quickstart.md` were produced. All twelve gates still PASS. The
Phase 1 design adds no backend module, runtime dependency, endpoint, table,
secret, external map provider, or unsupported capability. Its cross-cutting
artifacts are the existing shared geometry fixture plus a documented frontend UI
contract. The shared shell owns only presentation and capability-filtered
navigation; canonical Attendance and geofence decisions remain in their owning
features and server paths.

## Project Structure

### Documentation (this feature)

```text
specs/006-location-geofence-guidance/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── reuse-inventory.md   # inspected reuse/refactor boundaries
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── README.md                    # "no new operation" contract statement
│   ├── frontend-ui.md               # shell/component/state/accessibility contract
│   └── geofence-distance-fixture.md # FR-043a shared fixture contract
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/                                   # UNCHANGED production code
├── locations/
│   ├── domain/geofence.py                 # canonical: EARTH_RADIUS_M, haversine_distance_m,
│   │                                      #   classify_geofence, geofences_overlap  (reused, not touched)
│   ├── application/
│   │   ├── geofence.py                    # DefaultGeofenceService.evaluate            (reused)
│   │   └── queries.py                     # LocationQueryService / ConfigQueryService  (reused)
│   └── adapters/api/serializers.py        # LocationSerializer / ConfigSerializer      (reused as-is)
├── attendance/                            # authoritative command path — untouched
│   ├── domain/attendance.py               # passes_accuracy, is_inside, resolve_location
│   ├── application/commands.py            # check_in / check_out, gates, candidates, attempts
│   └── adapters/api/                      # serializers.py (60 s freshness), maps.py (single link helper)
└── tests/
    ├── contract/locations/
    │   └── test_geofence_distance_fixture.py                # NEW — asserts fixture vs canonical haversine
    └── integration/postgres/locations/
        └── test_guidance_reads_create_no_records.py         # NEW — locations/config reads write nothing

contracts/
├── openapi.yaml                           # UNCHANGED — no new operationId
└── fixtures/
    └── geofence-distance.json             # NEW — shared, language-neutral distance fixture

frontend/
├── src/
│   ├── app/
│   │   ├── globals.css                      # imports tokens; resets/global rules only
│   │   └── (employee)/
│   │       ├── layout.tsx                   # one employee-shell mount; URL-neutral route group
│   │       └── attendance/page.tsx          # thin route + IdentityRouteBoundary
│   ├── shared/
│   │   ├── api/{client.ts,schema.ts}        # unchanged, regenerated no-op
│   │   ├── transport/authenticated-fetch.ts # unchanged — sole transport chokepoint
│   │   └── ui/
│   │       ├── theme/tokens.css             # brand/status/neutral/spacing/radius/type tokens
│   │       ├── button/{Button.tsx,index.ts} # shared interactive variants and focus behavior
│   │       ├── card/{Card.tsx,index.ts}     # shared surface/section primitive
│   │       ├── badge/{Badge.tsx,index.ts}   # text + icon/shape status primitive
│   │       ├── section-heading/{SectionHeading.tsx,index.ts} # reusable semantic section title
│   │       ├── brand/MobiFoneLogo.tsx       # sole approved local asset consumer
│   │       ├── async-state/                 # existing renderer, extended rather than copied
│   │       └── shell/
│   │           ├── AppShell.tsx             # client boundary for auth-aware shell state
│   │           ├── AppHeader.tsx            # brand, page context, back/account affordances
│   │           ├── PrimaryNavigation.tsx    # bottom nav on phone; rail on wider viewports
│   │           └── employee-navigation.ts   # implemented routes + required capabilities
│   └── features/
│       ├── locations/
│       │   └── api/location-api.ts        # reused: listLocations(), getConfig()
│       ├── guidance/                      # existing Feature 006 ownership boundary
│           ├── model/
│           │   ├── geofence.ts            # mirror of canonical geometry (fixture-pinned)
│           │   ├── use-guidance-position.ts   # bounded acquisition + permission/error/freshness
│           │   ├── nearby.ts              # rank/cap/derive inside-outside + boundary distance
│           │   └── guidance-state.ts      # browser/API state -> closed guidance view state
│           └── ui/
│               ├── GuidancePanel.tsx      # thin feature composition; no Attendance command
│               ├── GpsStatusCard.tsx      # accuracy/threshold/state/refresh presentation only
│               ├── GpsAccuracyIndicator.tsx # presentational ring/icon; never authorization logic
│               ├── LocationSummaryCard.tsx # focused/nearest identity + distance/radius/status
│               ├── NearbyLocations.tsx    # always containing + 3-row floor + View more
│               ├── NearbyLocationItem.tsx # reusable semantic row for each Location
│               ├── LocationDiagnostics.tsx # collapsed coordinates/time/radius/troubleshooting
│               ├── SpatialPanel.tsx       # disclosure + lazy import + textual fallback
│               └── spatial/               # decomposed prop-only SVG; no provider types
│                   ├── SpatialDiagram.tsx
│                   ├── markers.tsx
│                   ├── legend.tsx
│                   └── projection.ts
│       └── attendance/
│           ├── api/attendance-api.ts      # existing generated-client wrapper
│           ├── model/
│           │   ├── attendance-state.ts    # existing payload/candidate parsing
│           │   └── use-attendance-experience.ts # today/processing/outcome orchestration
│           └── ui/
│               ├── AttendancePanel.tsx    # thin ordered page composition
│               ├── AttendanceContextHeader.tsx # Location + open-session context
│               ├── PrimaryAttendanceAction.tsx # capability-aware CTA; fresh command path
│               ├── AttendanceOutcomeCard.tsx   # persistent success/rejection beside CTA
│               ├── LocationChoice.tsx     # server-returned candidates only
│               └── TodayTimeline.tsx      # existing daily/session history
└── tests/
    ├── unit/ui/                            # primitives and semantic status behavior
    ├── unit/shell/                         # logo semantics, capability filtering, responsive nav
    ├── unit/guidance/                      # state labels, disclosure, nearby, overlap, diagram
    ├── unit/attendance/                    # fresh CTA, processing, outcome, preview separation
    ├── architecture/                       # boundaries, no duplicate shell, GPS privacy, no raw colors
    └── contract/geofence-parity.test.ts    # shared fixture vs frontend geometry
```

**Structure Decision**: Web application layout, already established by Features
002–005. Keep the repository's `features/<name>/{api,model,ui}` convention and
the existing `features/guidance` name; do not create a parallel
`features/location-guidance`. The employee route group mounts the shell once
without changing public URLs. Shared UI receives only cross-screen visual and
shell behavior; Feature 006 owns location/GPS presentation; Attendance owns its
command and authoritative result. `Dialog`/`Sheet` is deliberately absent: the
clarified outcomes are inline and the repository has no second general reuse
case. Backend production code and API contracts remain unchanged.

`LocationSummaryCard`, `NearbyLocations`, and `NearbyLocationItem` expose
presentation-ready Location props and import no Attendance command type,
capability rule, or Attendance-specific threshold. This gives future Task
Evidence composition a direct reuse boundary without copying markup while its
different GPS thresholds and evidence policy remain owned by the Task feature.

The App Router layout remains server-renderable. `AppShell` is the lowest
client boundary because it consumes authenticated capability state and current
navigation state. Geolocation hooks, Attendance command orchestration, and the
interactive spatial disclosure remain client components. The prop-only SVG
renderer does not require `ssr: false`; `SpatialPanel` imports/mounts it only
after disclosure. Marker, legend, and projection responsibilities are split so
no JSX component/function exceeds the clean-code limits. No map-provider package
or provider-specific type crosses this boundary.

Runtime composition preserves one semantic/source order:

```text
(employee)/layout
└── AppShell
    ├── AppHeader
    │   ├── MobiFoneLogo
    │   └── account entry
    ├── page content
    │   └── AttendancePanel
    │       ├── AttendanceContextHeader
    │       ├── GpsStatusCard
    │       ├── PrimaryAttendanceAction
    │       ├── AttendanceOutcomeCard
    │       ├── LocationSummaryCard
    │       ├── NearbyLocations
    │       ├── SpatialPanel (collapsed → lazy local SpatialDiagram)
    │       ├── LocationDiagnostics
    │       └── TodayTimeline
    └── PrimaryNavigation
        ├── phone: bottom navigation
        └── tablet/desktop: navigation rail
```

The same components and DOM order serve every viewport. Wider layouts use CSS
grid placement only after the CTA; they do not duplicate navigation or feature
markup.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. This section is intentionally empty.
