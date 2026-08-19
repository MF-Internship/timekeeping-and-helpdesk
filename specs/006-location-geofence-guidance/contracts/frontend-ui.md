# Frontend UI Contract: Shell, Guidance, and Attendance Composition

**Feature**: 006 | **Date**: 2026-08-20 | **Scope**: presentation and ownership only

This contract defines the frontend boundaries added by the Feature 006 UX
modernization. It changes no HTTP operation, permission, database entity, or
canonical Attendance rule.

## 1. Dependency direction

```text
shared UI primitives
        ↓
employee application shell
        ↓
Feature 006 guidance presentation
        ↓
Attendance page composition
```

- `shared/ui` accepts semantic presentation props and owns no GPS, geofence,
  Attendance, role, or API decision.
- `features/guidance` may consume existing Location/Config reads and browser
  geolocation, but it exports presentation-ready state and never imports the
  Attendance command model.
- `features/attendance` owns today state, punch acquisition, command processing,
  server outcomes, server candidates, and session history. It may compose
  guidance UI but never consumes its GPS snapshot as a punch payload.
- The route mounts one shell. Page and feature components do not reproduce
  header or primary-navigation markup.

## 2. Shared primitive contract

| Primitive | Required semantics | Explicit exclusions |
|---|---|---|
| Button | native button/link semantics, primary/secondary/quiet/destructive presentation, loading/disabled behavior, accessible name, visible focus | no Attendance permission or command logic |
| Card | labelled surface/section with consistent padding/border/radius | no feature data fetching |
| Badge | text plus semantic icon/shape for neutral/ready/warning/critical states | color-only meaning forbidden |
| SectionHeading | heading level supplied by composition; optional description/action | no fixed page hierarchy |
| AsyncState | existing loading/empty/error behavior extended consistently | no duplicate feature-specific generic error primitive |

No general Dialog or Sheet is introduced by Feature 006. Attendance outcomes
are inline, and the existing generated-password dialog remains identity-owned.

All new visual values resolve through shared CSS custom properties. Feature CSS
contains no raw hexadecimal brand/status colors.

## 3. Application shell contract

The shell receives page context plus authenticated account/capability state and
renders:

- one local approved `MobiFoneLogo` instance in the header;
- page title and optional back action;
- avatar/account entry limited to implemented account actions;
- one content container;
- one navigation registry rendered as bottom navigation from 320–430 px and as
  a rail on tablet/desktop;
- top/bottom safe-area accommodation.

### Navigation filtering

An item renders only when both conditions hold:

1. its local route is implemented; and
2. the authenticated account holds the required capability.

Canonical order after filtering is Tasks → Attendance → Reports → Account.
Today only Attendance has an implemented employee destination. Missing entries
are omitted, never disabled placeholders. `aria-current="page"` identifies the
active destination. This filtering is not authorization; route and backend
guards remain required.

## 4. Brand asset contract

No approved MobiFone asset currently exists in the repository. Once supplied:

- store exactly one approved file at the agreed local brand asset path;
- consume it only through `MobiFoneLogo`;
- declare intrinsic width/height and preserve aspect ratio with contain behavior;
- use meaningful alternative text (`MobiFone` in the application header);
- size and clear space through shared responsive tokens;
- never fetch a remote logo, duplicate the file, or inline repeated base64 data.

Logo acceptance remains blocked until provenance and the intended header variant
are confirmed.

## 5. Guidance presentation contract

### GPS status

Input is presentation data, not raw authority:

```text
accuracyM?: number
thresholdM?: number
state: idle | ready | weak | refreshing | stale | unavailable
label: string
supportingText: string
cue: semantic icon/shape key
onRefresh?: user action
```

The optional indicator/ring renders these values. It does not calculate
Attendance eligibility. Numeric value, textual meaning, and a non-color cue are
always present when evaluated.

### Nearby Location disclosure

- Computed list: all containing Locations, then nearest outside entries up to
  five total; all containing may exceed five.
- Collapsed list: all containing Locations, then nearest outside entries until
  at least three rows show.
- “View more” reveals the remainder of the computed list.
- Collapse never hides a containing Location.
- Every row distinguishes code/name, nearest, containing/outside, and current
  visual focus.
- Nearest is the default visual focus only. It never becomes the server's
  `selected_location_id`.
- `LocationSummaryCard`, `NearbyLocations`, and `NearbyLocationItem` consume
  presentation-ready Location props and import no Attendance command type,
  capability rule, or Attendance-specific accuracy threshold.
- A future Task Evidence composition may reuse these Location presentations
  directly, but supplies its own calculated status and retains its distinct GPS
  thresholds and evidence policy. Presentation reuse never unifies Attendance
  and Task business semantics.

### Diagnostics and spatial view

Coordinates, acquisition time, exact diagnostics, and troubleshooting live in
an accessible disclosure. The self-contained spatial SVG lives behind a
separate disclosure after the primary CTA and textual Location summary. It
mounts only when opened, performs no external request, and exposes no provider
type. Text/list/radio information remains the canonical alternative.

## 6. Attendance presentation contract

| Server/session state | Headline | CTA |
|---|---|---|
| no open session | `Sẵn sàng bắt đầu ca` | `Check In` |
| open session | `Đang trong ca làm việc` | `Check Out` |
| processing Check In | unchanged context | `Đang Check In…`, duplicate submit disabled |
| processing Check Out | unchanged context | `Đang Check Out…`, duplicate submit disabled |

The page title remains `Chấm công`.

- Success renders a persistent inline status adjacent to the CTA, names the
  completed action, and shows the refreshed session state.
- Rejection renders a persistent inline authoritative reason, appropriate next
  step, and retry path.
- Either result remains until the next Attendance action or navigation away.
- Transient toast-only and blocking-dialog outcomes are prohibited.
- Server-returned overlap candidates remain Attendance-owned and separate from
  the preview's visual target state.

## 7. Required state semantics

Distinct presentation and recovery are required for idle, reference loading,
requesting, refreshing, ready, weak GPS, outside radius, overlap, stale preview,
permission denied, GPS unavailable, timeout, unknown acquisition failure,
reference failure, Attendance processing, Attendance success, and Attendance
rejection. Device failures never use Attendance error wording.

Live regions announce meaningful transitions once. The ticking sample age is
not inside a live region. Loading/processing exposes `aria-busy`; focus is
preserved through updates.

## 8. Responsive and accessibility acceptance

- One DOM and focus order across breakpoints; CSS may form at most two regions
  after the primary action on wider screens.
- No horizontal overflow at 320, 375, 390, or 430 px.
- Tablet/desktop content is centered and bounded; controls do not stretch to
  the viewport width.
- Touch targets are at least 44 by 44 CSS pixels.
- Keyboard operation, visible focus, accessible names, sufficient contrast,
  color-independent status, reduced motion, and textual spatial alternatives
  are mandatory.
- Tests assert roles, names, state, order, disclosure, and outcomes; they do not
  assert pixel equality with the unavailable reference image.
