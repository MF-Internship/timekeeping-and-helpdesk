# Phase 1 Data Model: Location Awareness and Geofence Guidance

**Feature**: 006 | **Branch**: `feature/006-location-geofence-guidance` | **Date**: 2026-08-20

## Persistence statement

**Feature 006 introduces no persistent model and requires no business-data
migration.**

- No new table, column, index, constraint, enum or sequence.
- No Django migration in any app under `backend/`.
- No backfill, no data transformation, no destructive operation.
- No client-side persistence: no `localStorage`, `sessionStorage`, cookie,
  IndexedDB or Cache Storage entry (FR-032).

Every entity below is **ephemeral client view state**, held in React component
memory and discarded on unmount, navigation or logout.

## Read-only inputs (existing, unchanged)

These are consumed as-is from existing endpoints. Feature 006 adds no field to
either (FR-038).

### `LocationSummary` — from `locations_list` (`GET /api/v1/locations/`)

| Field | Wire type | Used for |
|---|---|---|
| `id` | integer | identity, focus target, candidate correlation |
| `code` | string | display; stable presentation tie-break |
| `name` | string | display |
| `address` | string \| null | display |
| `kind` | enum | display / optional grouping |
| `latitude` | decimal string | distance computation |
| `longitude` | decimal string | distance computation |
| `radius_m` | decimal string | geofence classification, diagram circle |
| `is_active` | boolean | filter — only `true` enters the nearby computation |

Guidance requests `is_active: true`. Inactive Locations are never shown as
geofence candidates, matching the Attendance candidate rule
(`backend/attendance/application/commands.py::_candidate_matches`). The
observation-only "nearest over all 76 including inactive" rule (R-118/R-119)
belongs to `AttendanceAttempt` and is deliberately **not** mirrored here — the
preview describes where a punch could succeed, not what the server would record
as a diagnostic label.

### `GuidanceConfig` — from `config_retrieve` (`GET /api/v1/config/`)

| Field | Wire type | Used for |
|---|---|---|
| `max_attendance_accuracy_m` | decimal string | GPS quality diagnostic only — **never** subtracted from `radius_m` |

`task_gps_*` thresholds are never read in this flow (QUY_TAC §10 item 26).

## Ephemeral entities

### 1. Guidance Position Snapshot

One acquired browser fix. Replaced wholesale on refresh; never appended to a
history.

| Field | Type | Notes |
|---|---|---|
| `latitude` | string | full precision retained; six-decimal rounding is display-only (FR-003a) |
| `longitude` | string | as above |
| `accuracy_m` | string | device-reported horizontal accuracy |
| `capturedAt` | ISO 8601 string | from `position.timestamp` |

Derived, not stored:

| Derived | Rule |
|---|---|
| `ageSeconds` | `now - capturedAt`, recomputed on a 1 Hz tick |
| `isStale` | `ageSeconds > 60` — **displayed only**, never used to block an action |
| `qualityMeetsThreshold` | `accuracy_m <= max_attendance_accuracy_m` — an independent quality gate |

Lifecycle: `undefined` → set on successful acquisition → replaced on refresh →
discarded on unmount. Never serialized, never logged, never placed in a URL,
never sent to the backend (FR-031–FR-034).

### 2. Nearby Location View

One row per active Location retained after ranking. Pure projection of
`LocationSummary` + `GuidancePositionSnapshot`.

| Field | Type | Rule |
|---|---|---|
| `locationId` | number | from `id` |
| `code`, `name`, `address` | string | display |
| `radiusM` | number | from `radius_m` |
| `distanceM` | number | canonical haversine, `EARTH_RADIUS_M = 6_371_008.8` |
| `status` | `"INSIDE_GEOFENCE" \| "OUTSIDE_GEOFENCE"` | `distanceM <= radiusM` → INSIDE. Closed at two values; no `UNCERTAIN` |
| `distanceToBoundaryM` | number | `max(distanceM - radiusM, 0)` — required when OUTSIDE (FR-018) |
| `insideMarginM` | number | `max(radiusM - distanceM, 0)` — optional display when INSIDE |

Computed-list selection and ordering rules (FR-013, FR-013a):

1. Only `is_active === true` Locations are eligible.
2. Sort ascending by `distanceM`, then by `code` (presentation stability only —
   this is **not** the R-119 observation tie-break and has no business effect).
3. **Every** entry with `status === INSIDE_GEOFENCE` is retained, regardless of
   the cap.
4. Fill up to five entries total with the nearest OUTSIDE entries.
5. **No maximum-distance filter** — a far Location still appears if fewer than
   five are nearer.

Collapsed presentation is a separate derived view (FR-048): every containing
entry remains visible, then the nearest outside entries are added until at
least three rows show. `isExpanded = true` reveals every remaining computed
entry. Collapsing never removes a containing row. This disclosure state does
not change ranking, focus, or candidate selection.

Invariants: accuracy is never subtracted from `radiusM`; overlapping and
coincident geofences are valid and all containing entries are listed; the view
never designates a winner among multiple INSIDE entries (QUY_TAC §10 item 7).

### 3. Guidance Status

The acquisition state machine driving `PositionStatus`.

| Field | Type |
|---|---|
| `status` | `"idle" \| "prompting" \| "acquiring" \| "ready" \| "error"` |
| `permission` | `"unknown" \| "prompt" \| "granted" \| "denied"` |
| `error` | `{ kind: "PERMISSION_DENIED" \| "UNAVAILABLE" \| "TIMEOUT" \| "UNKNOWN" } \| undefined` |

Reference data has its own disjoint state:

| Field | Type |
|---|---|
| `referenceStatus` | `"idle" \| "loading" \| "ready" \| "unavailable"` |

A presentation mapper combines acquisition, reference, freshness, accuracy and
membership into exactly one visible state:

`idle | reference_loading | requesting | refreshing | ready | weak | outside |
overlap | stale | permission_denied | gps_unavailable | timeout | unknown_error |
reference_failure`.

The mapper supplies labels, numeric readouts, non-color cue, recovery action,
and live-announcement text. Presentation components consume this state and do
not calculate Attendance eligibility.

Transitions:

```text
idle --user activates--> prompting --permission granted--> acquiring
acquiring --first fix--> ready            (watch cleared before resolving)
acquiring --error/timeout--> error        (watch cleared before rejecting)
ready|error --user refresh--> acquiring   (previous watch cleared first)
any --tab hidden | unmount--> acquisition stopped
```

This vocabulary is disjoint from the Attendance rejection codes; the two are
never merged into one union or one rendering path (research.md §10).

### 4. Focused Target

| Field | Type | Notes |
|---|---|---|
| `focusedLocationId` | `number \| undefined` | explicit user override; drives focused readouts and diagram |
| `defaultFocusedLocationId` | `number \| undefined` | derived from the first/nearest computed entry when no override exists |

Effective focus is `focusedLocationId ?? defaultFocusedLocationId`. The default
nearest target is automatic orientation only, not an Attendance winner. Focus
is not `selected_location_id`, does not pre-authorize anything, and is never
forwarded into a punch payload. When the server returns
`LOCATION_CHOICE_REQUIRED`, the candidate list and the resulting
`selected_location_id` come from `details.location_candidates`, not from this
field.

### 5. Spatial Diagram View (derived, transient)

Computed for render only; nothing is stored.

| Element | Source |
|---|---|
| user marker | Guidance Position Snapshot |
| accuracy circle | `accuracy_m`, styled distinctly from the geofence circle |
| target marker | focused `LocationSummary` |
| geofence circle | exactly `radius_m` at the diagram scale — never adjusted |
| scale / fit | chosen so user, target and the full geofence circle are visible; metre scale bar printed |

Projection is a local equirectangular approximation used **only** to place
pixels. Every distance rendered as text comes from the canonical haversine
mirror. All geometry is drawn from client-held data; the component issues no
network request of any kind (FR-028).

### 6. Nearby Disclosure State

| Field | Type | Rule |
|---|---|---|
| `isExpanded` | boolean | `false` initially; reset on new guidance acquisition |
| `collapsedEntries` | `NearbyLocationView[]` | all containing plus nearest outside until at least three |
| `visibleEntries` | `NearbyLocationView[]` | collapsed or full computed list based on `isExpanded` |
| `hiddenCount` | number | full computed count minus collapsed count |

Transitions: collapsed → expanded by “View more”; expanded → collapsed by
“View less”; a new position resets to collapsed. No transition hides a
containing Location.

### 7. GPS Status Presentation

| Field | Type | Notes |
|---|---|---|
| `accuracyM` | `number \| undefined` | numeric display input |
| `thresholdM` | `number \| undefined` | configured Attendance threshold, never hardcoded |
| `state` | `"idle" \| "ready" \| "weak" \| "refreshing" \| "stale" \| "unavailable"` | presentation vocabulary |
| `label` | string | human-readable status |
| `supportingText` | string | threshold, age, or recovery explanation |
| `cue` | semantic icon/shape key | accompanies text and color |

The optional ring consumes these values. It never derives server authorization
and has no callback other than the owning refresh action.

### 8. Attendance Experience State

| Field | Type | Rule |
|---|---|---|
| `todayStatus` | `"loading" \| "ready" \| "error"` | existing today-read lifecycle |
| `hasOpenSession` | `boolean \| undefined` | server-returned current state |
| `action` | `"CHECK_IN" \| "CHECK_OUT" \| undefined` | derived from `hasOpenSession` |
| `headline` | string | clarified action-specific Vietnamese headline |
| `ctaLabel` | string | Check In / Check Out / processing label |
| `processing` | boolean | prevents duplicate submission |
| `outcome` | `AttendanceOutcomePresentation \| undefined` | persistent until next action/navigation |
| `candidates` | server candidate array | only from authoritative rejection details |

The Attendance state owns command orchestration but never reads or submits the
guidance snapshot.

### 9. Attendance Outcome Presentation

| Field | Type | Notes |
|---|---|---|
| `kind` | `"success" \| "rejection"` | disjoint from device acquisition errors |
| `action` | `"CHECK_IN" \| "CHECK_OUT"` | identifies completed or attempted command |
| `message` | string | success confirmation or canonical server reason |
| `nextStep` | `string \| undefined` | recovery or follow-up guidance |
| `retryAvailable` | boolean | whether the command may be retried |
| `sessionState` | `string \| undefined` | updated open/closed session summary on success |

### 10. Application Shell Context

| Field | Type | Rule |
|---|---|---|
| `pageTitle` | string | stable page context |
| `backTarget` | route \| undefined | only where hierarchy requires it |
| `accountLabel` | string | authenticated full name or username |
| `accountInitials` | string | avatar text alternative and visual fallback |
| `navigationItems` | `NavigationItem[]` | implemented destinations filtered by capability |
| `navigationMode` | `"bottom" \| "rail"` | responsive presentation only |

Navigation Item fields are `key`, canonical label, route, order, required
capability, and active state. Filtering is presentation only; route and backend
authorization remain authoritative. Missing Tasks, Reports, and Account routes
produce no item.

## Entity relationships

```text
GuidanceConfig ──┐
                 ├──> Nearby Location View[] ──> Nearby Disclosure State
LocationSummary[]┘         ▲                    │
                           │                    ├──> Focused Target ──> Spatial Diagram View
        Guidance Position Snapshot ────────────┘                 ▲
                           │                                     │
                    Guidance Status ──> GPS Status Presentation ─┘

Attendance API state ──> Attendance Experience State ──> Attendance Outcome Presentation
Authenticated account + route registry ──> Application Shell Context
```

No guidance relationship crosses into the Attendance write path. The redesigned
page reads the existing Attendance today projection and invokes the existing
Attendance-owned commands; Feature 006 adds no persisted entity or write rule.
Opening, refreshing, focusing, expanding or collapsing guidance still reads or
writes none of `Attendance`, `AttendanceSession`, `AttendanceAttempt`,
`TaskUpdate` or `AuditLog` (FR-031).
