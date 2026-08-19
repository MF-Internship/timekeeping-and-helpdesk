# Feature Specification: Location Awareness and Geofence Guidance

**Feature Branch**: `feature/006-location-geofence-guidance`

**Created**: 2026-08-19

**Updated**: 2026-08-20

**Status**: Ready for planning — GR-001 resolved by deferral (see Governance Resolution)

**Input**: User description: "Location Awareness and Geofence Guidance, extended with mobile-first
Attendance UX modernization, a MobiFone-branded application shell, reusable interface
responsibilities, progressive disclosure, an understandable GPS status visualization, clear nearby
Location and spatial guidance, complete asynchronous states, responsive behavior, and accessibility.
The supplied Field Clarity direction is inspiration rather than a pixel-perfect contract. Preview
calculations must never become authoritative Attendance authorization."

## Governance Resolution — Recorded *(GR-001 resolved by deferral; no open clarification remains)*

The feature brief requests an **interactive map view** (scope item 5). This is the only part of the
brief that cannot be specified from the authoritative documents, because those documents currently
forbid the rendering technique an interactive map requires:

| Source | Authority | Statement |
| --- | --- | --- |
| `docs/CHOT_YEU_CAU.md` §6.2.1 | Authoritative business rules | "Không nhúng iframe bản đồ, không tải SDK bản đồ bên ngoài" — external map link only, no embedded map |
| `docs/CHOT_YEU_CAU.md` §9.1 | Authoritative business rules | No external service dependency beyond S3/R2; MVP calls no external geocoding service |
| `docs/QUY_TAC_CLEAN_CODE.md` §forbidden-list item 16 | Engineering rules | "Gọi API geocoding bên ngoài, nhúng iframe/SDK bản đồ, hoặc lưu `maps_url`/`resolved_address` thành cột database" |
| `docs/RA_SOAT_YEU_CAU.md` R-42 | Decision history (records, does not create, rules) | Restates the same prohibition |
| `specs/004-attendance-core/spec.md` FR-036 | Accepted specification | "iframe and map SDK embedding are forbidden" |
| Constitution Principle I, Principle II, Engineering Constraints | Project constitution | Conflicts MUST be reported and resolved at the higher-authority source, never merged silently; network dependencies beyond the approved stack require an accepted specification change covering failure and privacy behaviour |

- **GR-001 — RESOLVED BY DEFERRAL (2026-08-19)**: A tile-based interactive map (map SDK, embedded
  iframe, or externally fetched map tiles) is **permanently out of scope for this feature**. The
  governance decision taken is *not to amend* `docs/CHOT_YEU_CAU.md` §6.2.1; the prohibition stands
  unchanged at all four authority sources listed above. This resolution is a decision, not an open
  question, and no open clarification remains in this specification.
- **Conditions for lifting the deferral (future work, not this feature)**: a later feature may
  reopen GR-001 only by first amending `docs/CHOT_YEU_CAU.md` §6.2.1, and that amendment must answer,
  for the privacy clause of this brief and CHOT §9.1/§9.4: which third party would receive employee
  position data, on what legal basis, and what the offline and failure behaviour is. Until such an
  amendment is accepted in CHOT, no artifact of this feature may add a tile, SDK, iframe, or external
  map provider. GR-001 blocks exactly one requirement — FR-028 — and nothing else.
- Under this deferral, the specification delivers the *user-visible intent* of scope item 5 —
  distinguishing current position, target Location, allowed geofence radius, and GPS accuracy — with
  a **self-contained spatial diagram** that renders only from data the client already holds and
  performs no external request (FR-025 to FR-028). This is a presentation choice inside existing
  rules, not a new business rule.
- No other part of this brief required a new business decision. Every other rule below is traceable
  to `docs/CHOT_YEU_CAU.md` or to accepted specifications 002, 003, and 004.

## Preview versus Authoritative Business Result *(mandatory framing)*

This specification uses two strictly separated terms. Every requirement below belongs to exactly one.

**PREVIEW / GUIDANCE RESULT** — an on-device, read-only, ephemeral estimate produced from one
guidance GPS snapshot and the authorized Location/Config reference data. It explains, it never
authorizes. It can be stale, it can disagree with the server, and disagreement is normal. It creates
no business record of any kind.

**AUTHORITATIVE ATTENDANCE VALIDATION** — the Feature 004 server operation. It alone validates the
fresh GPS payload, applies the accuracy gate, computes distance, resolves candidates, validates
`selected_location_id`, enforces session invariants, and writes `AttendanceAttempt`, `Attendance`,
and `AttendanceSession`. Nothing in this feature changes, replaces, precomputes, shortcuts, or
substitutes for any of it.

## Clarifications

### Session 2026-08-19

- Q: How should the nearby Location list be bounded — by a fixed number of entries, by a maximum distance, or both? → A: Count cap only, no distance limit. Every active Location containing the position is always listed, then the nearest remaining active Locations fill the list up to five entries in total; no maximum search or display distance applies.
- Q: Should the guidance panel be allowed to open an external Google Maps link built from the employee's live GPS position? → A: No. No external map link may be built from a live guidance position under any interaction. External map links stay limited to records with stored coordinates, produced through the single existing link helper, so no live employee coordinate is ever transmitted to a third party.
- Q: To how many decimal places should the guidance panel display latitude and longitude to the user? → A: Six decimal places, as a display rule only (about 0.11 m, finer than any GPS fix and any geofence radius). Stored values, distance computation, geofence evaluation, and link generation retain full canonical precision.
- Q: How should the client-side distance calculation be kept provably consistent with the canonical server-side rule it duplicates? → A: A committed shared fixture of reference position/Location pairs with expected distances and membership, asserted by both a server-side and a client-side test against the same values, the same Earth radius, and a stated tolerance. No preview endpoint is introduced and no live coordinate is transmitted.
- Q: Is the distance-to-boundary readout a required part of guidance, or an optional extra a build may omit? → A: Required when the position is outside the nearest Location, computed as `max(distance_m - radius_m, 0)`; the inside remaining margin stays optional. Both are user-experience derived values, not business invariants, and neither alters the canonical `distance_m <= radius_m` acceptance rule.

### Session 2026-08-20

- Q: How many nearby Location rows should the mobile default view show before “View more”? → A: Show every containing Location, then enough nearest outside Locations to show at least three rows; “View more” reveals the remaining computed entries.
- Q: How should the headline and primary action change between Check-In and Check-Out states? → A: Keep the page title “Chấm công”; use “Sẵn sàng bắt đầu ca”/“Check In” when no session is open and “Đang trong ca làm việc”/“Check Out” when a session is open; while processing, preserve the layout and label the active action “Đang Check In…” or “Đang Check Out…”.
- Q: How should Attendance navigation and layout adapt between phones, tablets, and desktop? → A: Use a single-column layout with bottom navigation at 320–430 px; use an authorization-aware navigation rail and at most two content regions on tablets and desktop, with a centered bounded desktop layout and unchanged reading order and primary-action priority.
- Q: Where should a Check-In or Check-Out result appear, and how long should it remain? → A: Show an inline status card adjacent to the primary CTA until the next Attendance action or navigation away; success confirms the completed action and updated session state, while rejection shows the authoritative server reason, an appropriate next step, and a retry path without a transient toast or blocking dialog.

## User Scenarios & Testing *(mandatory)*

### User Story 6 - Complete Attendance confidently on a phone (Priority: P1, cross-cutting)

A field employee standing at a physical site opens Attendance on a phone and immediately understands
the target or nearest Location, whether the next action is Check In or Check Out, whether the current
GPS reading is usable, and which primary action to take. Technical diagnostics remain available
without competing with the task.

**Why this priority**: This cross-cutting story makes the existing P1 guidance and Attendance
journeys usable in field conditions. Its stable identifier remains Story 6 so accepted downstream
references to Stories 1–5 do not silently change.

**Independent Test**: On each supported viewport class, present the full set of normal and failure
states and confirm the employee can locate the current Location, readiness status, GPS accuracy and
threshold, and primary Attendance action without opening diagnostics; then confirm the same shell,
navigation, status meanings, and interaction semantics remain usable with touch, keyboard, and
assistive technology.

**Acceptance Scenarios**:

1. **Given** a field employee opens Attendance on a supported smartphone, **When** the initial view
   is ready, **Then** the target or nearest Location, Attendance state, GPS status, and primary Check
   In or Check Out action appear in that order of emphasis before optional diagnostics or the spatial
   view.
2. **Given** a successful current reading, **When** the GPS status is presented, **Then** the employee
   can identify the numeric accuracy, required threshold, and ready or not-ready meaning from text
   and a non-color cue, and the primary Attendance action remains visually dominant.
3. **Given** an idle, requesting, refreshing, stale, weak-GPS, outside-geofence, overlapping,
   permission-denied, unavailable, timeout, reference-data-failure, or Attendance-rejection state,
   **When** that state occurs, **Then** the screen presents a specific and understandable state rather
   than an empty normal layout, preserves stable space where practical, and exposes the relevant
   recovery or next action.
4. **Given** the employee wants technical detail, **When** they open the detail disclosure, **Then**
   latitude, longitude, acquisition time, exact distance, configured radius, additional nearby
   Locations, and diagnostic explanation are available without changing the Attendance decision or
   obscuring the primary action when the detail is closed.
5. **Given** the employee navigates among available mobile destinations, **When** the application
   shell is shown, **Then** MobiFone identity, page context, account access, safe-area spacing, and
   responsive primary navigation use consistent labels, ordering, and interaction behavior.
6. **Given** the same Attendance state on phone, tablet, and desktop, **When** the viewport changes,
   **Then** information priority and functionality remain intact, content stays comfortably bounded
   on wide screens, and no interaction depends on a single screenshot width.
7. **Given** a keyboard or assistive-technology user, **When** they navigate and operate Attendance,
   **Then** every action has an understandable accessible name, status changes are announced where
   appropriate, focus order follows the visual task order, and the map or spatial view is never the
   only source of Location information.

---

### User Story 1 - Understand whether my current position will be accepted (Priority: P1)

A HELPDESK employee opens the location guidance panel before punching. They press an explicit
control to obtain their position, and then see their coordinates, how accurate the reading is, when
it was taken, which registered Location is nearest, how far away it is, that Location's configured
radius, and whether the reading currently sits inside or outside that radius — plus, separately,
whether the accuracy is good enough for Attendance at all.

**Why this priority**: This is the whole point of the feature. Every other story extends or protects
it. Delivered alone, it already removes the most common support question ("why was my check-in
rejected?").

**Independent Test**: Open the guidance panel with location permission granted, acquire a position,
and confirm every listed value is shown, that the inside/outside verdict changes exactly at
`distance_m = radius_m`, and that the accuracy verdict changes exactly at
`accuracy_m = Config.max_attendance_accuracy_m` independently of position.

**Acceptance Scenarios**:

1. **(A)** **Given** an accurate reading (`accuracy_m <= max_attendance_accuracy_m`) whose distance
   is within exactly one active Location's radius, **When** guidance is displayed, **Then** it names
   that Location by `code` and name, shows `distance_m`, `radius_m`, and an "inside" status, and
   states that the reading currently meets the accuracy requirement.
2. **(B)** **Given** an accurate reading outside every nearby active Location's radius, **When**
   guidance is displayed, **Then** it shows an "outside all nearby Locations" status, identifies the
   nearest Location, and shows the approximate remaining distance to that Location's boundary,
   labelled as an estimate for guidance only.
3. **(D)** **Given** a reading whose `accuracy_m` exceeds `Config.max_attendance_accuracy_m`,
   **When** guidance is displayed, **Then** it states that Attendance will reject this reading as
   weak GPS regardless of where the user is standing, **And** it still reports the position status
   separately without merging accuracy into the distance or radius.
4. **(H)** **Given** a displayed snapshot with poor accuracy, **When** the user presses "Refresh
   location" and a better sample arrives, **Then** the displayed accuracy, coordinates, acquisition
   time, distances, and statuses all update from the new sample and the previous snapshot is
   discarded.
5. **(I)** **Given** a displayed snapshot with good accuracy, **When** the user refreshes and a
   worse sample arrives, **Then** guidance shows the worse reading honestly, including a status that
   the reading is now insufficient for Attendance, and never keeps the older, better snapshot to
   flatter the result.
6. **Given** any snapshot, **When** it becomes older than the Attendance freshness window, **Then**
   guidance visibly marks it stale and states that a punch will take a new reading.

---

### User Story 2 - Recover when the device cannot give a position (Priority: P1)

An employee whose browser blocks location, whose device has no geolocation capability, or whose
device fails to obtain a fix within the timeout sees a clear, specific explanation and concrete
device-side steps, rather than a spinner or a generic failure.

**Why this priority**: Without this, the primary story silently fails for a large share of real
users, and the resulting support load is exactly what this feature exists to reduce.

**Independent Test**: Simulate each of permission denied, geolocation unavailable, and acquisition
timeout, and confirm three distinguishable messages, no infinite loading state, and a working retry.

**Acceptance Scenarios**:

1. **(E)** **Given** the user denies the browser location permission, **When** acquisition is
   attempted, **Then** guidance states that permission was denied, explains that the browser or OS
   setting must be changed by the user, offers an explicit retry, **And** does not re-prompt
   automatically or repeatedly.
2. **(F)** **Given** the browser or device exposes no geolocation capability, **When** the panel is
   opened, **Then** guidance states that this device cannot provide a position, **And** the
   Location reference information that does not depend on a position remains readable.
3. **(G)** **Given** permission is granted but no fix arrives within the acquisition timeout,
   **When** the timeout elapses, **Then** guidance reports an acquisition timeout distinctly from a
   permission denial, keeps no partial or fabricated position, and offers "Refresh location".
4. **Given** any acquisition failure, **When** the message is shown, **Then** the remediation advice
   covers only device-side actions and never suggests that any workaround relaxes a server rule.

---

### User Story 3 - Tell overlapping Locations apart and choose what to look at (Priority: P2)

At a site where two or more registered geofences overlap, the employee sees every Location whose
geofence contains their position, can tell them apart, and can switch which one the guidance view
is focused on — without that choice committing anything.

**Why this priority**: The canonical dataset contains known coincident and overlapping pairs
(`HCM000079` ↔ `HCM010005` at 0 m, `HCM030015` ↔ `HCM030000` at 4.8 m, `HCM010018` ↔ `HCM010000` at
47.1 m). Without this story, those sites produce a confusing preview and an unexplained
`LOCATION_CHOICE_REQUIRED` at punch time.

**Independent Test**: Place a position inside two overlapping Locations and confirm both are listed
individually with distinguishing `code`, that switching the focused Location changes only the
display, and that a subsequent punch still follows the Attendance Core candidate contract.

**Acceptance Scenarios**:

1. **(C)** **Given** an accurate reading inside two or more overlapping active Locations, **When**
   guidance is displayed, **Then** every containing Location is listed separately with its own
   `code`, name, address, `distance_m`, and `radius_m`, **And** the status states that multiple
   geofences contain the position, **And** overlap is presented as normal data, never as an error.
2. **Given** two Locations sharing identical coordinates and address, **When** they are listed,
   **Then** each entry shows `code` together with name, because address and distance alone cannot
   distinguish them.
3. **(J)** **Given** a focused target Location, **When** the user selects a different listed
   Location, **Then** the diagram, distance, radius, and boundary readout switch to that Location,
   **And** nothing is submitted, persisted, or pre-selected for a future punch.
4. **(P)** **Given** the user focused one of several containing Locations in the preview, **When**
   they then perform a punch, **Then** the request follows the Attendance Core contract unchanged —
   the server still returns `409 LOCATION_CHOICE_REQUIRED` from its own recomputed candidate set,
   and the user's selection is validated against that server-returned set.

---

### User Story 4 - Trust the server, not the preview (Priority: P2)

An employee whose preview said one thing and whose punch result said another understands that the
punch result is the real one, and that the difference is expected because they moved or the signal
changed.

**Why this priority**: A preview that is mistaken for authorization is worse than no preview. This
story is the guardrail that makes the rest of the feature safe to ship.

**Independent Test**: Produce a preview, move across a geofence boundary, punch, and confirm that
the punch used a freshly acquired sample, that the server verdict is what is displayed as the
outcome, and that opening or refreshing the preview left no record behind.

**Acceptance Scenarios**:

1. **(M)** **Given** guidance showed "inside", **When** the user moves outside and then presses
   Check In, **Then** a fresh sample is acquired for the request, the server rejects it with
   `422 OUTSIDE_RADIUS`, and the rejection is presented as the authoritative outcome.
2. **(N)** **Given** guidance showed "outside", **When** the user moves inside and presses Check In,
   **Then** the punch is accepted, **And** the earlier preview never blocked or disabled the action.
3. **(O)** **Given** the user opens the guidance panel and refreshes the position several times,
   **When** the database is inspected, **Then** no `AttendanceAttempt`, `Attendance`,
   `AttendanceSession`, `AuditLog`, or `OutboxEvent` row exists for those actions.
4. **Given** any guidance conclusion, **When** a punch is submitted, **Then** the request payload
   carries a newly acquired sample and never the stored preview snapshot.

---

### User Story 5 - See the situation spatially (Priority: P3)

The employee sees a simple picture of where they are relative to the target Location's geofence,
with the accuracy of their reading shown as a visually distinct, clearly diagnostic overlay.

**Why this priority**: Valuable for comprehension but not required for correctness; the numeric
readouts in Stories 1–3 already deliver the decision-relevant information. Its richest form is also
gated by GR-001.

**Independent Test**: Render the diagram for a known position and target, and confirm the geofence
circle scales to `Location.radius_m`, the accuracy overlay scales to `accuracy_m`, both are visually
distinguishable, and no network request leaves the page while rendering.

**Acceptance Scenarios**:

1. **(K)** **Given** a position and a focused target Location, **When** the spatial view renders,
   **Then** it shows a current-position marker, a target-Location marker, and a geofence circle
   whose radius equals `Location.radius_m`, with a stated scale and both markers visible.
2. **(L)** **Given** the snapshot reports `accuracy_m`, **When** the spatial view renders, **Then**
   an accuracy overlay of radius `accuracy_m` is drawn around the current position, visually
   distinct from the geofence circle and labelled as diagnostic only.
3. **Given** any `accuracy_m`, **When** the accuracy overlay is drawn, **Then** the geofence circle
   keeps radius exactly `Location.radius_m` — it is never expanded, shrunk, or offset by accuracy.
4. **Given** the spatial view renders, **When** network activity is observed, **Then** no external
   host is contacted for tiles, imagery, fonts, geocoding, or a map SDK.
5. **Given** other nearby Locations exist, **When** the spatial view renders, **Then** they may be
   shown as secondary markers, and selecting one makes it the focused target (Story 3).

### Edge Cases

- The device returns a non-finite or out-of-range coordinate or a negative accuracy: the sample is
  rejected as unusable before any distance is computed, and no partial guidance is shown.
- The device returns `accuracy_m` larger than every nearby radius: guidance still reports position
  status and accuracy status independently, and never converts the large accuracy into an
  inside/outside verdict of its own.
- The nearest Location is inactive: it is excluded from guidance, because an inactive Location can
  never become an Attendance candidate and showing it would predict an acceptance that cannot happen.
- Two Locations tie on distance — differing by no more than the FR-043a fixture tolerance: the one
  with the lexicographically smallest `code` is labelled nearest, for display stability only; the tie
  collapses nothing and selects nothing.
- The authorized directory contains no active Location at all: guidance states that no active
  registered Location is available, still shows the position and accuracy readouts, and does not
  report this as a position or accuracy failure (FR-013a).
- The position is outside the nearest active Location but inside a farther one: both readouts are
  shown against their own Location and the farther Location's containing status is not suppressed
  (FR-018).
- A refresh is requested while an acquisition is still in flight: the newer request supersedes the
  older, exactly one acquisition remains outstanding, and a superseded result is discarded even if it
  arrives first (FR-004).
- The device reports a failure that is none of permission denied, unavailable, or timeout: it is
  reported as an unknown acquisition failure with retry, never silently reclassified and never shown
  as an Attendance error code (FR-008a, FR-008b).
- The user's position is inside a Location whose `radius_m` is smaller than
  `max_attendance_accuracy_m`: guidance reports the position status truthfully; it does not warn on
  the Manager's behalf and does not alter the radius.
- The user leaves the screen or hides the tab mid-acquisition: acquisition stops immediately and no
  further fixes are taken.
- The Location directory or Config cannot be loaded: guidance reports that reference data is
  unavailable and shows the raw position only, marked unevaluated, rather than computing against
  stale or guessed values or substituting a default radius or threshold (FR-021a).
- The user has no `attendance.check_in.self` capability (LEADER, MANAGER): guidance still explains
  their position but presents no punch affordance.
- The snapshot is older than the freshness window when the user finally punches: the punch acquires
  a new sample; the stale snapshot is never submitted.
- The smallest supported phone has a display cutout or home indicator: header and bottom navigation
  remain operable within safe areas and do not cover the primary action or content.
- Text is enlarged or translated copy wraps to additional lines: controls and status cards grow
  without clipping, overlap, or loss of their accessible name.
- Motion reduction is requested: decorative transitions stop or simplify without hiding state
  changes or delaying access to controls.
- A visual status color cannot be perceived: the same meaning remains available through status text,
  iconography or shape, and numeric values.
- The approved local MobiFone logo asset is unavailable: no remote or improvised substitute is used;
  the shell remains structurally usable and implementation is not accepted until the approved asset
  dependency is satisfied.

## Requirements *(mandatory)*

### Functional Requirements

#### Guidance position acquisition

- **FR-001**: The system MUST request device geolocation only after an explicit user action, MUST
  NOT request permission on page load, and MUST NOT request it as a side effect of navigation.
  Authority: `docs/CHOT_YEU_CAU.md` §5.1, "GPS foreground có giới hạn, không phải tracking", which
  permits bounded foreground acquisition after an explicit action and permits displaying values
  derived on the device from the acquired position.
- **FR-002**: Acquisition MUST request a high-accuracy, non-cached sample and MUST stop as soon as a
  usable sample is obtained, the user cancels, the user navigates away, the document becomes hidden,
  or the acquisition timeout elapses. Continuous or background acquisition MUST NOT occur.
- **FR-003**: While acquiring, the system MUST show an acquiring state; on success it MUST show
  `accuracy_m` and MUST make latitude, longitude, and the time the displayed sample was acquired
  available in secondary details. The acquiring state MUST always terminate — into a displayed
  position, or into one of the four failure outcomes of FR-008a — within the acquisition timeout of
  FR-008. An acquiring state that can persist indefinitely is a defect, not an accepted outcome.
- **FR-003a**: Latitude and longitude MUST be displayed rounded to six decimal places, for both the
  guidance position and any registered Location coordinates shown beside it. This is a display rule
  only. The values used for distance computation, geofence evaluation, the spatial view, and any
  external link built from stored coordinates MUST retain their full canonical precision, and a rounded
  value MUST NEVER be substituted for a canonical one.
- **FR-003b**: `accuracy_m` MUST be understood, and explained to the user, as the device-reported
  horizontal radius in metres of the 95% confidence circle around the reported latitude and
  longitude, as supplied by the platform geolocation provider. Guidance MUST NOT reinterpret,
  rescale, or substitute its own confidence level for that value, MUST NOT present it as a guaranteed
  error bound, and MUST NOT derive any position claim from it beyond the quality gate of FR-017.
- **FR-004**: The system MUST provide an explicit "Refresh location" action that acquires a new
  sample and replaces the previous snapshot entirely; the previous snapshot MUST NOT be retained or
  preferred because it was better. If a refresh is requested while an acquisition is already in
  flight, the newer request MUST supersede the in-flight one, exactly one acquisition MUST remain
  outstanding at any moment, and a superseded result MUST be discarded even if it arrives first.
- **FR-005**: The system MUST display the snapshot's age and MUST mark it visibly stale when that age
  is strictly greater than the Attendance freshness window of 60 seconds; an age of exactly 60 seconds
  is not yet stale. The stale state MUST state that a punch will take a new reading. Age MUST be
  computed on the device as elapsed time since that same device acquired the sample, and MUST NOT be
  computed by comparing a device timestamp against a server timestamp. Because the server evaluates
  the punch payload's own freshness independently and authoritatively, this displayed age is advisory
  and MUST NOT be presented as the value the server will apply. A stale snapshot MUST remain readable
  as guidance and MUST NOT be silently refreshed. It MUST use a textual “stale preview” status, the
  acquisition time or elapsed age, an explanation that the displayed values are advisory, and an
  explicit “Refresh location” action; color alone is insufficient. Staleness MUST NOT disable or
  hide Check In or Check Out.
- **FR-006**: Permission denial MUST be reported as such, with device-side remediation and an
  explicit retry, and MUST NOT trigger automatic re-prompting.
- **FR-007**: Absence of geolocation capability MUST be reported distinctly, and position-independent
  reference information MUST remain readable.
- **FR-008**: Acquisition MUST be bounded by a timeout of 15 seconds. A timeout MUST be reported
  distinctly from permission denial and from absence of geolocation capability, MUST retain no partial
  or inferred position, and MUST offer retry.
- **FR-008a**: The guidance acquisition-failure vocabulary MUST be closed at exactly four outcomes:
  permission denied (FR-006), geolocation unavailable (FR-007), timeout (FR-008), and an unknown
  acquisition failure. The unknown outcome MUST be reported as an acquisition failure with retry, MUST
  NOT be silently reclassified as one of the other three, and MUST NOT be presented as a position
  result.
- **FR-008b**: Device geolocation failures and Attendance business errors MUST be presented as two
  separate vocabularies. A geolocation outcome MUST NOT be rendered using, mapped onto, or worded as
  `OUTSIDE_RADIUS`, `WEAK_GPS`, `LOCATION_CHOICE_REQUIRED`, or any other Attendance error code;
  and an Attendance error code MUST NOT be rendered as a device geolocation failure. Conflating the
  two vocabularies is forbidden and MUST be verifiable.
- **FR-009**: A sample MUST be rejected as unusable, before any distance or status is computed, unless
  latitude is finite within `[-90, 90]`, longitude is finite within `[-180, 180]`, and `accuracy_m`
  is finite and non-negative.

#### Nearby registered Locations

- **FR-010**: Guidance MUST evaluate only active Locations, because only active Locations can become
  Attendance candidates; inactive Locations MUST NOT appear in the guidance list and MUST NOT be
  labelled nearest.
- **FR-011**: Each listed Location MUST show `code` together with name, its registered address,
  `distance_m` from the current position, its configured `radius_m`, and whether the position is
  inside or outside that geofence. `code` is mandatory alongside name because the canonical dataset
  contains Locations sharing both address and coordinates.
- **FR-012**: The nearest Location MUST be identified as the smallest measured distance among active
  Locations. A tie MUST be treated as present when two measured distances differ by no more than the
  shared fixture tolerance stated in FR-043a, so that the rule is decidable in floating-point terms
  rather than relying on exact equality; a tie MUST then resolve to the lexicographically smallest
  `code`. This tie-break is a display convention only and MUST NOT select, collapse, or commit
  anything.
- **FR-013**: The list MUST include every active Location whose geofence contains the position, then
  MUST fill the remaining places with the closest remaining active Locations until the list holds
  five entries in total. When more than one Location qualifies, every qualifying Location MUST appear
  as its own entry. If more than five active Locations contain the position, all of them MUST still be
  listed and the list MUST exceed five rather than drop a containing Location. The list MUST be
  ordered by ascending `distance_m`, ties ordered by lexicographically smallest `code`; containing
  Locations MUST NOT be promoted ahead of a closer non-containing Location. Coincident coordinates and
  overlapping geofences MUST be presented as valid data, never as errors or duplicates to be merged.
- **FR-013a**: A maximum search or display distance MUST NOT be applied. The nearest active Location
  MUST always be identified and listed however far away it is, so that a position far from every
  registered site still receives directional guidance instead of an empty list. When the authorized
  directory contains no active Location at all, guidance MUST state that no active registered Location
  is available, MUST NOT report this as a position or accuracy failure, and MUST still display the
  position readout and the accuracy readout.
- **FR-014**: Distance MUST be great-circle distance between the snapshot and the Location's
  registered coordinates, expressed in metres, computed by the same haversine rule and the same Earth
  radius constant as canonical server validation. Neither the rule nor its constant may be restated in
  modified form by this feature; both are fixed by Feature 003 and pinned by the shared fixture of
  FR-043a.

#### Geofence status guidance

- **FR-015**: Apparent membership MUST be derived solely as `distance_m <= radius_m` → inside,
  otherwise outside. The guidance vocabulary MUST contain exactly these two membership values; an
  `UNCERTAIN` state or any third membership value MUST NOT be introduced.
- **FR-016**: `accuracy_m` MUST NEVER be added to or subtracted from a distance or a radius anywhere
  in this feature. `distance - accuracy <= radius`, `distance + accuracy <= radius`, and every
  equivalent expansion or shrinking of the geofence are forbidden in computation and in wording.
- **FR-017**: The measurement-quality readout and the position readout MUST be presented as two
  independent gates. When `accuracy_m > Config.max_attendance_accuracy_m`, guidance MUST state that
  Attendance will reject the reading as weak GPS irrespective of position, AND MUST still report the
  position status separately rather than suppressing or overriding it.
- **FR-018**: When the position is outside the nearest active Location, a distance-to-boundary value
  MUST be displayed for that Location, computed as `max(distance_m - radius_m, 0)`. When the position
  is inside a Location, the remaining margin `radius_m - distance_m` MAY be displayed for that
  Location. When the position is outside the nearest active Location but inside a farther one, both
  readouts MUST be shown against their own Location, MUST NOT be merged into a single figure, and the
  containing status of the farther Location MUST NOT be suppressed because the nearest Location does
  not contain the position. Both readouts are user-experience values derived for presentation and
  neither is defined by the authoritative business rules. Each MUST be labelled as an approximate
  guidance value. The system MUST NOT combine either readout with `accuracy_m`, MUST NOT use either as
  a business acceptance rule, and MUST NOT describe either as one. The canonical acceptance rule
  remains `distance_m <= radius_m` evaluated by the server, unchanged by the existence of this
  readout.
- **FR-019**: Guidance status wording MUST cover: inside exactly one registered Location; inside
  multiple overlapping registered Locations; outside all nearby registered Locations; and GPS
  accuracy insufficient for Attendance evaluation.

#### Diagnostics and remediation

- **FR-020**: Guidance MUST show current `accuracy_m` against the configured
  `Config.max_attendance_accuracy_m`, read through the existing configuration read contract, and MUST
  NOT hardcode the threshold or any radius.
- **FR-021**: Weak-accuracy remediation MUST offer only device-side actions — enable precise or
  high-accuracy location, enable device location services, move to a more open area, enable Wi-Fi or
  mobile data if it assists the device provider, wait briefly, use Refresh location. It MUST NOT
  state or imply that any action relaxes, bypasses, or overrides a server-side rule, and MUST NOT
  offer manual coordinate entry, position override, radius change, or threshold change.

- **FR-021a**: When the authorized Location directory or the singleton configuration cannot be
  loaded, guidance MUST report the reference data as unavailable, MUST NOT display a nearest Location,
  a distance, a membership status, or an accuracy verdict derived from a missing threshold, MUST NOT
  substitute a default radius or a default accuracy threshold, and MUST offer a retry. The position
  readout itself MAY remain displayed, clearly marked as unevaluated.

#### Target Location behaviour

- **FR-022**: When the user has made no explicit selection, the nearest Location MUST be the default
  focused target. The user MUST be able to switch focus to any other listed Location.
- **FR-023**: The focused target is display state only. It MUST NOT be transmitted as
  `selected_location_id`, MUST NOT pre-commit an Attendance Location, and MUST NOT survive as an
  implicit choice into a later punch.
- **FR-024**: When multiple Locations contain the position, each MUST remain individually
  distinguishable and individually selectable in the preview; the preview MUST NOT collapse them.

#### Spatial visualization

- **FR-025**: The system MUST provide a spatial view that renders entirely from data already held by
  the client and performs no request to any external host — no map tiles, no map SDK, no embedded
  map iframe, no geocoding call — in conformance with CHOT §6.2.1, QUY_TAC forbidden-list item 16,
  and Feature 004 FR-036.
- **FR-026**: The spatial view MUST visually distinguish four things: the current position, the
  focused target Location, the allowed geofence radius (a circle of exactly `Location.radius_m`), and
  the GPS accuracy overlay (radius `accuracy_m`). The accuracy overlay is diagnostic only and MUST
  NOT alter, expand, shrink, or offset the geofence circle.
- **FR-027**: The spatial view MUST scale so that the current position and the focused target are
  both visible, MUST state its scale so distances are not misread, and MAY show other nearby
  Locations as secondary markers that can be focused.
- **FR-028**: A tile-based or SDK-based interactive map is deferred under GR-001 (resolved by
  deferral) and MUST NOT be implemented by this feature. Lifting the deferral requires an accepted
  amendment to `docs/CHOT_YEU_CAU.md` §6.2.1 first; this is the only requirement GR-001 blocks.

#### External map link

- **FR-029**: Where an external map link is offered, the rule of `specs/004-attendance-core/spec.md`
  FR-036 applies unchanged and is **referenced, not restated**: the link is produced only by the
  single existing helper `backend/attendance/adapters/api/maps.py::attendance_maps_url` from the
  relevant record's own stored coordinates, preserving the stored decimal representation with no
  rounding for URL generation, opening in a new context with `noopener`/`noreferrer`, and adding no
  geocoding, no iframe, and no map SDK. This feature MUST NOT define a second copy of that rule and
  MUST NOT diverge from it; a change to link behaviour is a change to Feature 004 FR-036 and to
  `docs/CHOT_YEU_CAU.md` §6.2.1, not to this requirement.
- **FR-029a**: This feature MUST NOT offer any external map link built from the live guidance
  position, in any form, whether or not the user acts explicitly and whether or not the external
  service is disclosed. External map links remain limited to records that carry stored coordinates,
  exactly as the authoritative rules already define them; a live position is not such a record, and
  building a link from it would both transmit the employee's current coordinates to a third party
  and require a second copy of the link helper outside its single canonical home.
- **FR-030**: Live guidance coordinates MUST NOT appear in this application's own paths, query
  strings, or fragments.

#### Privacy and absence of persistence

- **FR-031**: Opening, viewing, or refreshing guidance MUST create no `Attendance`, no
  `AttendanceSession`, no `AttendanceAttempt`, no `AuditLog`, no `OutboxEvent`, and no other
  persisted row.
- **FR-032**: Live guidance coordinates MUST be held only in volatile client memory for the lifetime
  of the view and MUST NOT be written to local storage, session storage, cookies, or any client-side
  database, and MUST NOT be restored after navigation or reload.
- **FR-033**: Live guidance coordinates and accuracy MUST NOT appear in application logs, telemetry,
  metric names or label values, error reports, or notification payloads, consistent with CHOT §9.4
  and §9.6.
- **FR-034**: Guidance MUST compute its result on the user's device from the authorized Location
  directory and configuration, and MUST NOT transmit live guidance coordinates to the backend. This
  removes the exposure surface addressed by FR-030 and FR-033 at its source and avoids adding a new
  endpoint. Authority: `docs/CHOT_YEU_CAU.md` §5.1 permits per-Location distance, apparent
  inside/outside state, and remaining distance to the boundary to be computed and displayed entirely
  on the device as a read-time presentation concern, subject to the same clause's constraints — no
  storage, no transmission of the live position, no external service, no gating of a punch, and no
  change to the canonical `distance_m <= radius_m` acceptance rule, which only the server decides.
- **FR-035**: This feature MUST introduce no new persisted entity, no schema change, and no
  migration.

#### Authorization

- **FR-036**: Viewing one's own guidance position MUST require authentication only. This feature MUST
  NOT introduce a new permission, role, capability, or permission-implication pair, and MUST NOT
  grant any Attendance or Task capability.
- **FR-037**: Location and configuration reference data MUST be obtained only through the existing
  `location.view` and `config.view` contracts, which are already granted to LEADER, MANAGER, and
  HELPDESK. LEADER and MANAGER access MUST remain exactly as the canonical role model defines it.
- **FR-037a**: Guidance MUST NOT present a Check In or Check Out affordance to a user lacking the
  corresponding self-attendance capability. This is a capability-visibility rule read from the
  canonical RBAC model and evaluated independently of any guidance conclusion. It does not conflict
  with FR-040: FR-040 forbids gating the control on the preview's own position or accuracy verdict,
  while this requirement governs whether the control exists for that account at all.
- **FR-038**: Guidance MUST consume only the minimum Location attributes it needs — `code`, name,
  address, registered coordinates, `radius_m`, and active state — from the existing directory
  response, and MUST NOT require a new field or a new endpoint.

#### Preview versus authoritative validation

- **FR-039**: Every guidance conclusion MUST be labelled as a preview. A punch MUST acquire its own
  fresh sample at the moment of the operation, and that acquisition MUST begin only after the punch
  has been initiated by the user, so the submitted sample is strictly newer than any preview
  snapshot; the guidance snapshot MUST NOT be reused as the punch payload or as proof of location.
- **FR-040**: Guidance MUST NOT enable, disable, hide, or otherwise gate the Check In or Check Out
  control based on its own conclusion. An "outside" preview MUST NOT prevent the user from
  submitting a punch, because the server is the only authority on acceptance. This prohibition
  concerns the guidance verdict only; the capability-visibility rule of FR-037a is a separate
  canonical rule and continues to apply.
- **FR-041**: When the server outcome differs from the preview, the server outcome MUST be presented
  as the authoritative result and the divergence MUST be explained as expected, not as an error in
  either layer.
- **FR-042**: If Attendance returns `409 LOCATION_CHOICE_REQUIRED`, this feature MUST present the
  candidate set exactly as returned by that response. It MUST NOT substitute, supplement, filter, or
  reorder those candidates using its own nearby list or its own distance computation, and MUST NOT
  pre-select one on the user's behalf. The user's selection MUST be resubmitted through the Attendance
  Core contract and MUST be revalidated against the server's recomputed candidate set.

#### Reuse boundary and verification

- **FR-043**: Presentation components MUST be built so a future Task Evidence feature can reuse them,
  but this feature MUST NOT implement Task Evidence behaviour, MUST NOT read `task_gps_good_accuracy_m`
  or `task_gps_low_accuracy_m`, and MUST NOT unify Attendance and Task GPS policies. Attendance
  guidance reads `max_attendance_accuracy_m` only.
- **FR-043a**: Because guidance computes distance on the device while the canonical rule lives on the
  server, the two implementations MUST be held to one shared set of reference values: a committed
  fixture of position-and-Location pairs with their expected distances and expected membership, using
  the same Earth radius as canonical validation. Both the server-side and the client-side calculation
  MUST be asserted against that same fixture, within an absolute tolerance of 0.001 metres (one
  millimetre) recorded with the fixture and changeable only as a governance-level change to
  Location/GPS domain semantics, so
  that a divergence on either side fails a test rather than surfacing as guidance that silently
  disagrees with a punch result. The fixture MUST include the three known overlapping Location pairs
  and positions exactly on a geofence boundary.
- **FR-044**: Verification MUST prove, at minimum: that opening and refreshing guidance writes no row
  of any kind; that no guidance coordinate reaches storage, logs, telemetry, or a URL; that the
  spatial view issues no external request; that the quality gate and the radius gate are evaluated
  independently at their exact boundaries; that inactive Locations are excluded; that overlapping and
  coincident Locations are listed individually with `code`; that the client and server distance
  calculations agree on the shared fixture required by FR-043a; that the acquiring state always
  terminates; that the four acquisition-failure outcomes of FR-008a are each reported distinctly and
  none is ever rendered as an Attendance error code; that a refresh issued during an in-flight
  acquisition leaves exactly one outstanding acquisition; that an unavailable directory or
  configuration produces no defaulted threshold or radius; and that a punch after a preview carries a
  newly acquired sample.

#### Mobile-first hierarchy and progressive disclosure

- **FR-045**: The Attendance experience MUST prioritize, in order: current, selected, or nearest
  Location; current Check In or Check Out state; GPS quality and readiness; the primary Attendance
  action; nearby Location summary; troubleshooting; detailed diagnostics; and the spatial view.
  Presentation MAY combine adjacent items when their relative emphasis remains unambiguous.
- **FR-046**: The primary Check In or Check Out action MUST remain easy to find, visually dominant,
  and positioned before technical GPS diagnostics and the spatial view. It MUST remain subject to
  the capability rule in FR-037a and MUST NOT be gated by the preview, as required by FR-040. The
  page title MUST remain “Chấm công”. When no session is open, the state headline and CTA MUST
  communicate “Sẵn sàng bắt đầu ca” and “Check In”; when a session is open, they MUST communicate
  “Đang trong ca làm việc” and “Check Out”. While the command is processing, the layout MUST remain
  stable and the active CTA MUST communicate “Đang Check In…” or “Đang Check Out…” as applicable.
- **FR-047**: The default view MUST show the selected or nearest Location, ready or not-ready state,
  current `accuracy_m`, required Attendance accuracy threshold, distance, and primary Attendance
  action. Latitude, longitude, acquisition timestamp, configured radius, precise distance,
  additional nearby Locations, and diagnostic explanations MUST be available through a clearly
  labelled secondary or expandable detail area rather than receiving equal default emphasis.
- **FR-048**: Each nearby Location entry MUST be scannable as one coherent item and preserve the
  information required by FR-011. Nearest, containing, focused-target, and outside statuses MUST be
  independently identifiable; when several statuses apply, their presentation MUST NOT imply that
  nearest, containing, and selected are the same concept. On the default mobile view, every
  containing Location MUST be visible, followed by enough nearest outside Locations to show at least
  three rows in total. When the computed list has more rows, a clearly labelled “View more” control
  MUST reveal all remaining entries produced by FR-013; collapsing the list MUST never hide a
  containing Location.
- **FR-049**: The spatial view governed by FR-025 to FR-028 MUST support rather than dominate the
  Attendance task. On constrained screens it MUST appear after the primary Attendance action and be
  collapsed or otherwise secondary by default. Its legend MUST distinguish the allowed Location
  radius from GPS accuracy uncertainty in both words and visual treatment.

#### GPS status and observable interface states

- **FR-050**: The system MUST provide one reusable GPS status presentation that communicates the
  current `accuracy_m`, the required Attendance threshold, and ready or not-ready meaning using a
  numeric value, status text, and a non-color visual cue. It MUST also distinguish requesting,
  refreshing, and stale states where applicable.
- **FR-051**: Any ring or other graphical accuracy indicator MUST be presentational only. It MUST
  consume an already determined guidance state, MUST NOT calculate or become the source of Attendance
  authorization, and MUST remain accompanied by an equivalent textual interpretation.
- **FR-052**: The Attendance and location-guidance experience MUST explicitly represent idle,
  requesting location, success, refreshing, weak GPS, outside geofence, overlapping candidates,
  permission denied, geolocation unavailable, timeout, reference-data or guidance failure, and
  authoritative Attendance business rejection. Device acquisition failures and Attendance business
  rejections MUST remain separate vocabularies as required by FR-008b.
- **FR-053**: Loading, refresh, success, and failure transitions MUST avoid unnecessary displacement
  of the primary action and surrounding information. A failed acquisition or reference-data load
  MUST never appear as an empty normal screen, and every recoverable state MUST expose a clear retry,
  refresh, selection, settings, or continue action appropriate to that state. An Attendance success
  or rejection MUST appear in an inline status card adjacent to the primary CTA and remain until the
  next Attendance action or navigation away. Success MUST identify the completed action and updated
  session state. Rejection MUST identify the authoritative server reason, an appropriate next step,
  and a retry path. Neither outcome MAY rely on a transient toast or a blocking dialog.

The required visual behavior for each operational state is:

| State | Required default presentation and action |
| --- | --- |
| Idle | No implied GPS verdict; explain why location is needed and offer the explicit acquisition action. |
| Requesting location | Keep the status and primary-action regions stable, identify that permission or a fix is being requested, and provide no fabricated reading. |
| GPS ready | Show the numeric accuracy, required threshold, positive textual readiness, and a non-color ready cue. |
| GPS weak | Show the numeric comparison, a distinct signal-quality warning, device-side remediation, and Refresh; do not replace it with an outside-radius message or gate the Attendance CTA. |
| Outside radius | Identify the focused Location, outside status, distance, radius, and distance to boundary; keep signal quality separate and do not gate the Attendance CTA. |
| Overlapping Locations | Present overlap as normal informational state, keep every containing Location visible and individually focusable by code and name, and explain that authoritative selection occurs only after the server requests it. |
| Permission denied | State that permission was denied, provide browser or device settings guidance and an explicit retry, and do not automatically re-prompt. |
| GPS unavailable | State that the device or browser cannot provide location, retain position-independent Location information, and do not word it as permission denial or timeout. |
| Loading reference data | Identify the reference-data load separately from GPS acquisition and reserve the result region to avoid an empty normal screen. |
| Refreshing | Replace the prior preview claim with a labelled refreshing state in the same reserved region; do not silently retain the older reading as if current. |
| Stale preview | Keep values readable with the stale treatment required by FR-005, explain that a punch takes a new reading, and offer Refresh without gating the CTA. |
| Attendance processing | Preserve layout, disable duplicate submission, and use the action-specific processing label required by FR-046. |
| Attendance success | Show the persistent inline confirmation and updated session state required by FR-053. |
| Attendance rejection | Show the persistent inline authoritative reason, next step, and retry path required by FR-053; do not render it as a device GPS acquisition error. |

#### Application shell and MobiFone identity

- **FR-054**: Mobile employee screens MUST use a consistent application shell providing an
  application header, MobiFone identity, page title and back action where context requires it,
  account access, a bounded content region, responsive primary navigation, and safe-area handling.
  Phones MUST use bottom navigation; tablets and desktop MUST use an equivalent navigation rail.
  These shell responsibilities MUST come from a shared source rather than copied page-specific
  structures.
- **FR-055**: The shell MUST use the approved local MobiFone logo asset, preserve its aspect ratio,
  avoid stretching or cropping, provide meaningful alternative text, and preserve clear space around
  it. It MUST NOT embed or fetch an arbitrary remote logo URL.
- **FR-056**: Available mobile destinations MUST use the canonical labels and order Tasks,
  Attendance, Reports, and Account. A destination that is unavailable or not permitted MUST be
  handled consistently across screens and MUST NOT cause remaining destinations to change label or
  relative order. Navigation structure MUST NOT be independently duplicated by each page. A
  navigation item MUST be rendered only when its destination is implemented and the authenticated
  account has the route's required capability; the visual reference MUST NOT create placeholder
  destinations or imply unsupported permissions. Account access MAY expose only authenticated
  account actions that already exist.
- **FR-057**: The visual language MUST use MobiFone blue for primary brand and action emphasis, red
  for overdue, error, or critical meaning, green for success or ready meaning, and neutral
  backgrounds and surfaces. These meanings MUST be defined once for reuse and MUST NOT be recreated
  as unrelated raw color choices within individual feature views.
- **FR-058**: Cards and controls MUST use clear boundaries, restrained depth effects, comfortable
  rounding, and spacing suitable for mobile interaction. Decorative treatment MUST not compete with
  the information hierarchy or imply status that is not present in text.

#### Responsive and accessible operation

- **FR-059**: The experience MUST be optimized first for smartphones and remain fully usable on
  larger phones, tablets, and desktop browsers. At 320–375 px and approximately 390–430 px, content
  MUST remain a single column; the larger phone range MAY use more breathing room but MUST NOT change
  task order. Tablets and desktop MAY use at most two content regions only when the primary hierarchy
  and reading order remain unchanged. Desktop content MUST be centered at a readable bounded width
  rather than stretched across all available space, and no behavior MAY depend on one fixed
  screenshot width.
- **FR-060**: Every interactive control MUST have a comfortably usable touch target, an
  understandable accessible name, a visible keyboard focus state, and a logical focus order that
  follows the task hierarchy. All actions MUST remain operable by keyboard on desktop.
- **FR-061**: Text and status indicators MUST maintain sufficient contrast, and color MUST never be
  the only representation of readiness, error, selection, nearest status, containment, or overlap.
  Status meaning MUST also be conveyed by text and, where useful, icon, shape, or numeric value.
- **FR-062**: Requesting, refreshing, success, stale, and failure changes MUST be exposed so
  assistive technologies can understand material status updates without disruptive repetition. The
  experience MUST respect reduced-motion preferences for decorative animation.
- **FR-063**: Location names, addresses, distances, radii, and statuses MUST remain available in
  text. The spatial view MUST never be the only means of understanding a Location or the user's
  relationship to it.

#### Reusable presentation architecture

- **FR-064**: Shared interface responsibilities that recur across screens — primary action, card,
  status badge, application header, bottom navigation, loading, empty, error, dialog or sheet, and
  section heading — MUST each have one reusable product behavior rather than separate nearly
  identical page-specific versions. Repository inspection found no current application shell,
  application header, bottom navigation, or general Button, Card, Badge, Dialog or Sheet primitive;
  the existing shared asynchronous-state renderer MUST be reused or deliberately extended rather
  than duplicated. A Dialog or Sheet MUST NOT be generalized solely for this feature because the
  clarified Attendance outcomes are inline and no second reuse case is established.
- **FR-065**: Attendance location guidance MUST be composed from separable presentation
  responsibilities for Location summary, nearby Location list and item, GPS status and accuracy,
  geofence status, refresh, primary Attendance action, permission, loading and error states, and the
  optional spatial panel and legend. Shared UI owns the application shell, header, responsive
  navigation, and genuinely repeated visual primitives. Feature 006 owns GPS status, Location
  summary, nearby Location presentation, geofence guidance, permission/acquisition states, refresh,
  progressive details, and the spatial panel and legend. Attendance owns the Check In or Check Out
  headline and primary action, processing and authoritative outcome, server-returned candidate
  selection, daily summary, and session timeline. Final names and placement are planning decisions
  that MUST follow the repository's existing conventions. Location summary, nearby Location list,
  and nearby Location item presentation MUST accept presentation-ready Location props, MUST NOT
  import Attendance command types, capability rules, or Attendance-specific accuracy thresholds,
  and MUST remain directly reusable by a future Task Evidence composition without copying their
  markup. Task Evidence retains its own canonical GPS thresholds and evidence policy; reuse of these
  presentation responsibilities MUST NOT unify Attendance and Task business semantics.
- **FR-066**: Browser and service state MUST be translated into a feature-level view state before it
  reaches reusable presentation responsibilities. Presentation MUST consume calculated or
  server-returned status and MUST NOT silently become a second source of canonical Attendance
  validation or business rejection decisions. The existing Attendance and guidance acquisition,
  reference-data, candidate, and server-authority behavior MUST be refactored behind this composition;
  implementation MUST NOT retain the current panels as monoliths and add a second parallel wrapper
  that duplicates their state or markup.
- **FR-067**: The Field Clarity reference and supplied MobiFone direction MUST guide hierarchy,
  density, navigation, operational wording, and action prominence, but MUST NOT override this
  specification, accessibility, governance, or the server-authority boundary and MUST NOT be treated
  as a pixel-perfect acceptance image.

### Key Entities

All entities in this feature are ephemeral view state. None is persisted, and none corresponds to a
database table.

- **Guidance Position Snapshot**: one accepted device reading — latitude, longitude, `accuracy_m`,
  acquisition time, and derived age. Lives in volatile memory, replaced wholly by a refresh,
  discarded when the view is left.
- **Nearby Location View**: one active Location as presented for guidance — `code`, name, registered
  address, `radius_m`, measured `distance_m`, apparent membership, and approximate boundary distance.
  Derived from the authorized directory; carries no new attribute.
- **Guidance Status**: the human-readable summary derived from the snapshot and the Nearby Location
  Views — accuracy sufficiency and position membership, held as two independent statements.
- **Focused Target**: which Nearby Location View the spatial view and readouts are centred on.
  Display state; never an Attendance selection.
- **Attendance Experience State**: the presentation-ready combination of Attendance state, guidance
  state, GPS quality, current Location emphasis, primary action, asynchronous status, and recovery
  action. It consumes canonical results and does not make business decisions.
- **Application Shell Context**: current destination, page context, available navigation, account
  shortcut, and safe-area presentation state shared across employee screens; it contains no new
  authorization rule.
- **Referenced existing entities** (read-only, unchanged): `Location` and `Config` from Feature 003;
  `Attendance`, `AttendanceSession`, and `AttendanceAttempt` from Feature 004, none of which this
  feature writes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

A **representative user trial** is one observation session in which a single participant, drawn from
the population of employees who record Attendance on their own device, opens the guidance view once
under a scripted position and reference-data condition and is asked to read the guidance aloud. The
sample of ten trials MUST cover at least three distinct participants and at least three distinct
device or browser combinations, and each trial counts as a success only when every value the
criterion names is stated correctly. The same definition applies to every success criterion below
that counts trials.

- **SC-001**: From an accurate reading, a user can state their nearest registered Location, their
  distance to it, its radius, and whether they are inside it, within 15 seconds of the position being
  displayed, in at least 9 of 10 representative user trials as defined above.
- **SC-002**: For a reading whose accuracy exceeds the configured Attendance threshold, at least 9 of
  10 representative user trials as defined above correctly state that the punch will be rejected for signal quality rather
  than for being in the wrong place.
- **SC-003**: 100% of guidance sessions — opening, viewing, and any number of refreshes — produce
  zero `Attendance`, `AttendanceSession`, `AttendanceAttempt`, `AuditLog`, and `OutboxEvent` rows.
- **SC-004**: 100% of guidance sessions produce zero occurrences of a live guidance coordinate in
  client storage, application logs, telemetry, metric labels, notification payloads, application
  URLs, or any URL constructed for an external service, verified by automated inspection.
- **SC-005**: The spatial view completes rendering with zero requests to any host outside the
  application origin, verified by automated inspection.
- **SC-006**: Boundary tests confirm the inside/outside verdict flips exactly at
  `distance_m = radius_m` and the accuracy verdict flips exactly at
  `accuracy_m = Config.max_attendance_accuracy_m`, with neither boundary shifted by any value of the
  other variable. Independence MUST be exercised with `accuracy_m` sampled at zero, just below the
  threshold, exactly at the threshold, just above the threshold, and above every configured
  `radius_m`; and with `distance_m` sampled just inside, exactly on, and just outside each geofence
  boundary present in the shared fixture of FR-043a.
- **SC-007**: At the three known overlapping Location pairs, 100% of previews list each Location
  separately with its distinguishing `code`, and 0% report the overlap as an error.
- **SC-008**: 100% of punches performed after a preview carry a sample acquired after the punch was
  initiated, and 0% reuse the preview snapshot.
- **SC-009**: Every canonical Attendance rule referenced by this feature — the two-value membership
  vocabulary, the independence of the two gates, candidate resolution, and session invariants —
  is delivered with an empty change set across this feature's entire change history. "Empty change
  set" means no addition, removal, or reword of those statements in the authoritative Location
  domain rules, the authoritative Attendance command rules, or the published API contract; changes
  confined to guidance-only presentation sources are not in scope for this criterion.
- **SC-010**: In at least 9 of 10 representative smartphone trials, an employee can identify the
  selected or nearest Location, the next Attendance action, current GPS accuracy, required threshold,
  and ready or not-ready meaning within 10 seconds without opening technical details.
- **SC-011**: In 100% of tested idle, requesting, success, refreshing, stale, weak-GPS,
  outside-geofence, overlap, permission-denied, unavailable, timeout, reference-data-failure, and
  Attendance-rejection cases, the interface shows the correct named state and a valid next action or
  explicit terminal explanation; none appears as an empty normal screen.
- **SC-012**: Across every employee screen included in this feature, 100% of shared shell elements
  use the same MobiFone identity treatment and the same destination labels, ordering, active-state
  meaning, account access, and safe-area behavior.
- **SC-013**: Across the supported phone, tablet, and desktop viewport matrix, 100% of primary
  Attendance actions remain visible, readable, and operable without horizontal scrolling, clipped
  content, or overlap with the application shell; wide layouts preserve a readable bounded content
  width.
- **SC-014**: Accessibility verification finds zero primary or recovery actions without an
  understandable accessible name, zero status meanings conveyed by color alone, zero keyboard traps,
  and zero cases where the spatial view is the sole source of Location information.
- **SC-015**: In moderated testing, at least 9 of 10 participants can distinguish the allowed
  Location radius from GPS accuracy uncertainty using the legend and textual alternatives, including
  when color cues are removed.
- **SC-016**: Architecture review finds one shared product responsibility for each recurring shell,
  navigation, primary action, card, badge, loading, empty, error, dialog or sheet, and section-heading
  pattern used by this feature, with zero nearly identical page-specific copies introduced.

## Assumptions

- The project constitution supplies non-negotiable global governance. Within the business and
  implementation authority chain required by Constitution Principle I, sources are ordered as
  `docs/CHOT_YEU_CAU.md` (§3, §4, §4.1–§4.3, §5.1, §6.2.1, §8, §9.1, §9.4, §9.6, §10) →
  `docs/QUY_TAC_CLEAN_CODE.md` → the product requirements document → accepted specifications 002,
  003, and 004 → current implementation.
  `docs/RA_SOAT_YEU_CAU.md` is decision history and introduces no rule here.
- The existing `GET /api/v1/locations/` directory and `GET /api/v1/config/` singleton read already
  expose everything this feature needs — `code`, name, address, coordinates, `radius_m`, active
  state, and `max_attendance_accuracy_m` — to all three roles under `location.view` and
  `config.view`. No new or widened contract is assumed.
- The canonical Location set is closed at 76 records, small enough that guidance can rank all active
  Locations on the device without a server round trip; this is what makes FR-034 practical. The
  assumption holds while the active set stays at or below 500 records. Beyond that, on-device ranking
  must be re-examined as a new decision, and it MUST NOT be resolved by transmitting live guidance
  coordinates to the server, which FR-034 forbids regardless of directory size.
- "Nearby" is a display convenience with no business meaning: every containing Location plus the
  closest remaining active Locations. The count is fixed at five by the 2026-08-19 clarification and
  is binding on implementation and tests through FR-013. It is a product decision rather than a
  governance one, so a later clarification may revise it without amending the authority chain — but
  an implementer MUST NOT change it silently.
- Guidance intentionally mirrors Attendance candidate semantics (active Locations only) rather than
  the server's observability nearest-Location diagnostic, which by R-119 also considers inactive
  rows. That diagnostic remains server-side and is not surfaced here.
- The existing bounded-foreground acquisition behaviour already implemented for the Attendance screen
  — high accuracy, no cached age, stops on hidden tab, cancel, timeout, or submission — satisfies
  CHOT §5.1 and is the acquisition model reused here; this feature neither loosens nor tightens it.
- The "does not track in the background" requirement of this brief and CHOT §5.1's permitted bounded
  foreground acquisition are compatible statements about the same behaviour, not a conflict.
- Reverse geocoding is not used; displayed addresses are the registered `Location.address` only.
- The detailed visual direction in the 2026-08-20 feature brief is sufficient to specify the desired
  experience. The named `field-clarity.html` file and reference screenshot were not present in the
  workspace during specification; if supplied later, they remain inspirational and cannot introduce
  requirements that conflict with this specification or project governance.
- An approved local MobiFone logo asset is a delivery dependency. No matching asset was present in
  the application assets during specification, so planning must identify or obtain the approved file
  before logo acceptance; an arbitrary remote or recreated substitute is not assumed.
- Tasks, Attendance, Reports, and Account are the canonical employee navigation labels requested by
  this feature. This feature standardizes their shell treatment but does not invent business content,
  permissions, or workflows for a destination that is otherwise outside Feature 006.
- Global authorization ordering, transaction, audit, observability, and PostgreSQL verification rules
  are governed by the constitution and are not weakened by this specification.

- Requirement identifiers in this specification are stable and permanent. Each `FR-###` and `SC-###`
  is assigned once and MUST NOT be renumbered. A suffixed identifier — `FR-003a`, `FR-003b`,
  `FR-008a`, `FR-008b`, `FR-013a`, `FR-021a`, `FR-029a`, `FR-037a`, `FR-043a` — marks a requirement
  inserted after its neighbours were already cited elsewhere, and carries exactly the same weight as
  an unsuffixed one. A requirement that is withdrawn is marked withdrawn in place rather than
  deleted, so no citation in `plan.md`, `research.md`, `data-model.md`, `tasks.md`, or the checklists
  can silently retarget a different rule.

## Dependencies

- Feature 002 — authentication, account state gating, and the canonical RBAC capability model.
- Feature 003 — the 76-Location canonical directory, the singleton `Config`, validated GPS input
  rules, the haversine distance rule, and the two-value `LocationValidationResult` vocabulary.
- Feature 004 — the authoritative Check In and Check Out operations, the candidate contract including
  `409 LOCATION_CHOICE_REQUIRED`, the 60-second freshness window, and the existing foreground
  acquisition behaviour.
- Reference-data readiness (Feature 003 FR-044) — guidance is meaningless without exactly one
  complete `Config` and all 76 canonical Locations. When that reference data cannot be loaded,
  FR-021a governs the behaviour; guidance MUST NOT fall back to a default radius or a default
  accuracy threshold.
- Product-approved local MobiFone logo artwork suitable for the application shell. Approval and
  provenance are external to Feature 006; acceptance cannot be met with a remote replacement.
- The supported browser, viewport, contrast, keyboard, and assistive-technology test matrix used by
  the product's accessibility and responsive-quality gates.

## Out of Scope

- Background employee location tracking, continuous GPS collection, route history, movement history,
  automatic geofence entry/exit events, turn-by-turn navigation, and any form of employee
  surveillance.
- Storing guidance GPS snapshots, guidance history, or any derived location trail.
- Changing the canonical Attendance geofence mathematics, the accuracy gate, the candidate resolution
  rules, or the session invariants.
- Changing Task evidence rules or unifying Attendance and Task GPS policies.
- Changing Location seed data, Location identity, or Location radius through the guidance flow.
- Creating a Location, deleting a Location, or editing configuration from this feature.
- A tile-based or SDK-based interactive map, deferred by GR-001 (resolved by deferral; lifting it
  requires an accepted amendment to `docs/CHOT_YEU_CAU.md` §6.2.1 first).
- An external map link built from the live guidance position, in any interaction form. External map
  links remain limited to records with stored coordinates.
- Reverse geocoding and any other external service dependency.
- Pixel-perfect reproduction of the Field Clarity reference, fixed-width screenshot matching, or
  preservation of an existing weak layout solely for visual compatibility.
- New Attendance eligibility, geofence, authorization, navigation-permission, Task, Report, or
  Account business rules. The shell may expose only destinations supported by their owning features.
