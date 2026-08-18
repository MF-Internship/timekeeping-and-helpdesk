# Feature Specification: Attendance Check-In and Check-Out Core

**Feature Branch**: `feature/004-attendance-core`

**Created**: 2026-08-18

**Status**: Ready for Planning

**Input**: User description: "HELPDESK attendance Check-In and Check-Out with multiple sessions per work date, fresh GPS, independent attendance quality and geofence gates, candidate resolution, exact AttendanceAttempt semantics, database-enforced single open session, self attendance read model, derived punch_index, and PostgreSQL race-condition acceptance tests."

## Clarifications

### Session 2026-08-18

- Q: Should AttendanceAttempt nearest-location diagnostics consider all 76 Locations, including inactive ones, while attendance candidates remain limited to active Locations? → A: Yes. Nearest diagnostics use all 76 canonical Locations; candidates, auto-selection, and selection revalidation remain active-only.
- Q: When multiple canonical Locations have exactly the same nearest distance, which single Location should AttendanceAttempt store? → A: Store the Location with the lexicographically smallest canonical `code`; this diagnostic tie-break never resolves geofence candidates.
- Q: If AttendanceAttempt persistence fails after the business transaction has ended, how must the API respond? → A: Preserve the original business response or exception, do not retry or roll back the business result, and emit only sanitized failure telemetry.
- Q: Which AuditLog actions must successful routine attendance punches create? → A: Check In creates `attendance.check_in.created` and Check Out creates `attendance.check_out.created` in the business transaction; rejected punches create no AuditLog, and routine punches create no OutboxEvent.
- Q: How are unexpected infrastructure failures handled after the AttendanceAttempt boundary? → A: Preserve the canonical 5xx response, create no AttendanceAttempt, never relabel the failure as one of the seven closed business outcomes, and emit only sanitized telemetry. The exact-one guarantee applies to classified business outcomes, subject to the already-approved observational-writer failure exception.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start and finish a work session (Priority: P1)

An authenticated HELPDESK employee records a Check In at an allowed active Location and later records a Check Out at any allowed active Location. The system preserves the two punches as one work session and presents the employee's current attendance state.

**Why this priority**: A trustworthy Check In/Check Out pair is the minimum usable attendance capability and the basis for payable work duration.

**Independent Test**: With one active Location containing each submitted GPS point, perform Check In and Check Out as a HELPDESK employee and verify two attendance records, one closed session, the expected locations and duration, and one accepted attempt per punch.

**Acceptance Scenarios**:

1. **Given** a HELPDESK employee has no open session and submits a fresh, accurate GPS sample inside exactly one active Location, **When** the employee checks in, **Then** an `IN` Attendance is accepted, that Location is selected automatically, one open AttendanceSession is created, exactly one `attendance.check_in.created` AuditLog commits with the business state, no OutboxEvent is created, and exactly one `ACCEPTED` AttendanceAttempt points to the new Attendance.
2. **Given** a HELPDESK employee has one open session and submits a valid GPS sample inside exactly one active Location, **When** the employee checks out, **Then** an `OUT` Attendance is accepted, the open session is closed by that Attendance, its duration is derived from the server-recorded Check Out and Check In times, exactly one `attendance.check_out.created` AuditLog commits with the business state, no OutboxEvent is created, and exactly one `ACCEPTED` AttendanceAttempt points to the new Attendance.
3. **Given** a HELPDESK employee has an open session, **When** the employee checks in again, **Then** the request is rejected with `409 SESSION_ALREADY_OPEN`, no Attendance is created, and exactly one `SESSION_ALREADY_OPEN` AttendanceAttempt is recorded.
4. **Given** a HELPDESK employee has no open session, **When** the employee checks out, **Then** the request is rejected with `409 NO_OPEN_SESSION`, no Attendance is created, and exactly one `NO_OPEN_SESSION` AttendanceAttempt is recorded.
5. **Given** a MANAGER attempts either attendance action, **When** authorization is evaluated, **Then** the request is rejected with `403 PERMISSION_DENIED` and neither Attendance nor AttendanceAttempt is created.

---

### User Story 2 - Work multiple sessions in one date (Priority: P1)

A HELPDESK employee can take an unpaid break or work separate shifts by ending one session and starting another on the same local work date, while the system keeps a strict alternating punch history.

**Why this priority**: Multiple same-day sessions are an explicit core business rule; a one-IN/one-OUT daily model would incorrectly block legitimate work.

**Independent Test**: On one Asia/Ho_Chi_Minh work date, perform `IN → OUT → IN → OUT` and verify four Attendance records, two closed sessions, the summed duration, and one shared `punch_index` sequence of `1 → 2 → 3 → 4`.

**Acceptance Scenarios**:

1. **Given** a HELPDESK employee completed one session earlier on the same work date, **When** the employee checks in and out again with valid location evidence, **Then** both punches succeed and create a second distinct AttendanceSession.
2. **Given** multiple Attendance records exist for one employee and work date, **When** the self attendance view is read, **Then** punches are ordered by `recorded_at` and receive a single one-based `punch_index` sequence spanning both `IN` and `OUT` kinds.
3. **Given** two closed sessions exist on one work date, **When** the daily total is read, **Then** it equals the sum of both session durations rather than the elapsed time between the first Check In and last Check Out.
4. **Given** an employee checks in at Location A and later checks out at Location B, **When** both samples independently pass attendance GPS policy, **Then** the session closes successfully and exposes A and B as separate Check In and Check Out locations.

---

### User Story 3 - Validate fresh and trustworthy location evidence (Priority: P1)

A HELPDESK employee can record attendance only with a current GPS sample whose accuracy meets the attendance threshold and whose measured point lies within an active Location's configured radius.

**Why this priority**: Attendance affects payroll and must reject stale, weak, invalid, or out-of-boundary evidence without distorting the configured geofence.

**Independent Test**: Exercise GPS numeric boundaries, sample age, accuracy threshold, and radius boundary independently and verify the expected accepted or rejected result and side effects.

**Acceptance Scenarios**:

1. **Given** `captured_at` is more than 60 seconds before server receipt, **When** Check In or Check Out is submitted, **Then** the sample is rejected before attendance business processing, no Attendance is created, and no AttendanceAttempt is recorded.
2. **Given** `accuracy_m` exceeds `max_attendance_accuracy_m`, **When** a post-boundary attendance request is processed, **Then** it is rejected with `422 WEAK_GPS`, no geofence candidates are resolved, and exactly one `WEAK_GPS` AttendanceAttempt is recorded.
3. **Given** accuracy passes but the measured distance is greater than every active Location's radius, **When** the request is processed, **Then** it is rejected with `422 OUTSIDE_RADIUS` and exactly one `OUTSIDE_RADIUS` AttendanceAttempt is recorded.
4. **Given** `distance_m = 40`, `accuracy_m = 20`, `radius_m = 50`, and the attendance threshold is `25`, **When** the sample is evaluated, **Then** it passes because quality and radius are independent and accuracy is not added to or subtracted from radius.
5. **Given** `distance_m = 60`, `accuracy_m = 5`, and `radius_m = 50`, **When** the sample is evaluated, **Then** it is outside despite high accuracy.
6. **Given** latitude, longitude, or accuracy is non-finite or outside its valid numeric range, **When** the payload is submitted, **Then** it is rejected before distance calculation and creates neither Attendance nor AttendanceAttempt.

---

### User Story 4 - Resolve overlapping Location candidates (Priority: P1)

A HELPDESK employee receives deterministic guidance when the GPS point belongs to zero, one, or multiple active Locations and can confirm an ambiguous choice safely.

**Why this priority**: Legitimate overlapping geofences exist, and silently selecting one would corrupt location attribution.

**Independent Test**: Submit samples producing zero, one, and two inside candidates; for the two-candidate case, resubmit with both a valid and invalid selection and verify recomputation and persistence behavior.

**Acceptance Scenarios**:

1. **Given** exactly one active Location contains the sample, **When** an attendance action is otherwise valid, **Then** the Location is selected automatically with `AUTO_SINGLE` resolution.
2. **Given** two or more active Locations contain the sample and no selection is supplied, **When** an attendance action is processed, **Then** it returns `409 LOCATION_CHOICE_REQUIRED` with the current candidates, creates no Attendance, and records exactly one `LOCATION_CHOICE_REQUIRED` AttendanceAttempt.
3. **Given** multiple candidates were previously returned and the employee resubmits with `selected_location_id`, **When** the request is processed, **Then** candidates are recalculated from the newly submitted sample and the selection is accepted only if it remains inside the recalculated set.
4. **Given** a supplied `selected_location_id` is absent from the recalculated candidate set, **When** the request is processed, **Then** it returns `422 INVALID_LOCATION_CHOICE` with the latest candidates, creates no Attendance, and records exactly one `INVALID_LOCATION_CHOICE` AttendanceAttempt.
5. **Given** multiple candidates are recalculated and the supplied selection is valid, **When** the action completes, **Then** the selected Location is stored with `USER_SELECTED` resolution and the accepted attempt points to the created Attendance.

---

### User Story 5 - Review today's own attendance (Priority: P2)

A HELPDESK employee views today's sessions, punch order, daily total, and whether a session is currently open so the interface can present the appropriate next action.

**Why this priority**: Immediate self-service feedback helps employees catch mistakes and understand whether they should Check In or Check Out.

**Independent Test**: Seed a day with two closed sessions and one defined punch timeline, read the authenticated employee's attendance, and verify session projection, total duration, open-session state, and derived punch indexes without accepting another user identifier.

**Acceptance Scenarios**:

1. **Given** an authenticated HELPDESK employee has attendance today, **When** the self view is requested, **Then** it returns only that employee's sessions for the Asia/Ho_Chi_Minh current work date, their punch records, total duration of closed sessions, and `has_open_session`.
2. **Given** the latest session is open, **When** the self view is requested, **Then** `has_open_session` is true and the session has no Check Out or duration.
3. **Given** all sessions are closed, **When** the self view is requested, **Then** `has_open_session` is false and the total ignores breaks between sessions.
4. **Given** persisted punch data is unchanged, **When** it is read repeatedly, **Then** `punch_index` is derived consistently and no persisted punch-index field is required or modified.

### Edge Cases

- A GPS point exactly on a Location radius boundary is inside; an accuracy exactly equal to the attendance threshold passes.
- Inactive Locations are excluded from candidate resolution, auto-selection, and selected-location revalidation, but remain eligible for nearest-only AttendanceAttempt diagnostics across the closed 76-Location set.
- Coincident Location coordinates remain separate candidates and nearest distance never auto-selects among them. Separately, the singular nearest-only AttendanceAttempt diagnostic resolves an exact distance tie by lexicographically smallest canonical Location `code`.
- If a user moves between the initial ambiguous response and resubmission, the latest recomputed candidates control the decision.
- If a selected-location resubmission has no recomputed candidates, `OUTSIDE_RADIUS` wins before selection validation; it is not relabeled `INVALID_LOCATION_CHOICE`.
- Check Out location may differ from Check In location, and leaving a geofence never auto-closes an open session.
- Every Check In and Check Out, including the second pair in a day, repeats freshness, quality, radius, and candidate validation.
- A server UTC timestamp near midnight derives the work date in Asia/Ho_Chi_Minh; changing client `captured_at` cannot change `recorded_at` or `work_date`.
- A session's work date remains the Check In work date; cross-day shifts and manual attendance adjustment are outside this feature.
- When two Check In requests race, only one may open a session; the loser receives `SESSION_ALREADY_OPEN` and still leaves one rejected attempt after its business transaction rolls back.
- A session marked closed by the established end-of-day process is not considered open even if it has no Check Out record.
- A process failure after the attendance transaction finishes but before observational attempt persistence may lose the attempt; this explicitly accepted limitation must not weaken Attendance or AttendanceSession atomicity.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST expose self Check In and self Check Out actions to authenticated HELPDESK users with the respective `attendance.check_in.self` and `attendance.check_out.self` permissions.
- **FR-002**: MANAGER and LEADER users MUST NOT Check In or Check Out; an authorization rejection MUST create neither Attendance nor AttendanceAttempt.
- **FR-003**: The self actions MUST take the actor from authenticated context and MUST reject client-supplied `user_id` rather than ignoring it.
- **FR-004**: The system MUST derive `kind` from the invoked action (`IN` for Check In, `OUT` for Check Out) and MUST reject client-supplied `kind` rather than ignoring it.
- **FR-005**: The server MUST own `recorded_at` in UTC and MUST derive `work_date` by converting that time to Asia/Ho_Chi_Minh; client `captured_at` MUST NOT determine attendance time, work date, or session duration.
- **FR-006**: Client-owned attendance input MUST be limited to `latitude`, `longitude`, `accuracy_m`, optional `captured_at`, and optional `selected_location_id`; attempts to submit other server-owned attendance fields MUST fail before the AttendanceAttempt boundary.
- **FR-007**: If `captured_at` is supplied, the system MUST reject a GPS sample older than 60 seconds at server receipt; the client workflow MUST request a fresh sample with no cached-age allowance and MUST NOT reuse or background-submit samples.
- **FR-008**: Latitude, longitude, and accuracy MUST be finite numbers; latitude MUST be within `[-90, 90]`, longitude within `[-180, 180]`, and accuracy MUST be non-negative before any geometry evaluation.
- **FR-009**: Attendance MUST use only `Config.max_attendance_accuracy_m` as its quality threshold and MUST reject `accuracy_m` above that value with `WEAK_GPS` before candidate classification.
- **FR-010**: The quality gate (`accuracy_m <= threshold`) and radius gate (`distance_m <= radius_m`) MUST be evaluated independently; accuracy MUST never be added to or subtracted from a Location radius.
- **FR-011**: Candidate resolution MUST evaluate every active Location and MUST include each Location whose measured distance is at or inside its own radius.
- **FR-012**: With no candidate, the system MUST reject the action with `422 OUTSIDE_RADIUS`; `OUTSIDE_GEOFENCE` MUST remain a validation-result value and MUST NOT be used as the API error code.
- **FR-013**: With exactly one candidate, the system MUST select it automatically and record `AUTO_SINGLE` as the resolution method.
- **FR-014**: With multiple candidates and no selection, the system MUST reject with `409 LOCATION_CHOICE_REQUIRED`, return the current candidate list, and create no Attendance.
- **FR-015**: For any supplied `selected_location_id`, the system MUST recompute candidates from the current request. If the set is empty, FR-012 MUST return `422 OUTSIDE_RADIUS`; if the set is non-empty and the selected Location is absent, the system MUST return `422 INVALID_LOCATION_CHOICE` plus the latest candidate list.
- **FR-016**: A valid selection from multiple recomputed candidates MUST be stored with `USER_SELECTED` resolution; Attendance MUST never use `GPS_ONLY` resolution.
- **FR-017**: Check In MUST succeed only when the user has no open AttendanceSession; otherwise it MUST return `409 SESSION_ALREADY_OPEN` without creating Attendance.
- **FR-018**: Check Out MUST succeed only when the user has exactly one open AttendanceSession; otherwise it MUST return `409 NO_OPEN_SESSION` without creating Attendance.
- **FR-019**: An open session MUST mean `check_out` is absent and `closed_by_job` is false, consistently across writes and reads.
- **FR-020**: A successful Check In MUST atomically create one `IN` Attendance and one open AttendanceSession; a successful Check Out MUST atomically create one `OUT` Attendance and close the current open session.
- **FR-021**: The transaction containing Attendance and AttendanceSession changes MUST also contain governed anomaly reconciliation and exactly one immutable AuditLog for the accepted punch; Check In MUST use `attendance.check_in.created`, Check Out MUST use `attendance.check_out.created`, `target_type` MUST be `Attendance`, `target_id` MUST be the new Attendance id, `before` MUST be `{}`, and `after` MUST contain exactly `attendance_id`, `kind`, `work_date`, `location_id`, and `session_id`. Any failure MUST roll back the entire business state. Rejected punches MUST create no AuditLog. Audit payloads MUST exclude coordinates, accuracy, device metadata, request IP, and maps URLs. Routine self punches MUST create no OutboxEvent.
- **FR-022**: The database MUST enforce at most one open AttendanceSession per user with a partial uniqueness rule over the canonical open-session condition; a service pre-check alone is insufficient.
- **FR-023**: The system MUST NOT enforce uniqueness on Attendance by `(user, work_date, kind)` and MUST support an alternating `IN → OUT → IN → OUT …` sequence with multiple sessions per work date.
- **FR-024**: Each Check Out MUST close the user's current open session. `duration_minutes` MUST be calculated from the exact server timestamp delta and quantized once to six decimal minute places using `ROUND_HALF_UP`; open and job-closed sessions MUST keep it absent.
- **FR-025**: Session Check In and Check Out Locations MAY differ; movement outside geofences MUST NOT close a session, reduce duration, or continuously track the employee.
- **FR-026**: Every request that passes authentication, action authorization, account-state gates, and server-owned-field/input validation, reaches session-state evaluation, and ends in one of the seven classified business outcomes MUST make exactly one post-transaction AttendanceAttempt persistence attempt, including successful requests. When observational persistence is available, this MUST produce exactly one AttendanceAttempt; an AttendanceAttempt write failure MUST NOT alter or mask the original business response or exception. Unexpected infrastructure failures MUST retain canonical 5xx handling and MUST create no AttendanceAttempt.
- **FR-027**: Requests rejected before that boundary—including missing or invalid authentication, inactive account, missing permission, MANAGER/LEADER actor, required-password-change state, malformed GPS, stale GPS, or a client-supplied server-owned field—MUST produce no AttendanceAttempt.
- **FR-028**: AttendanceAttempt outcomes MUST be the closed set `ACCEPTED`, `WEAK_GPS`, `OUTSIDE_RADIUS`, `LOCATION_CHOICE_REQUIRED`, `INVALID_LOCATION_CHOICE`, `NO_OPEN_SESSION`, and `SESSION_ALREADY_OPEN`.
- **FR-029**: An `ACCEPTED` attempt MUST reference the Attendance created by the request; every non-accepted attempt MUST have no Attendance reference.
- **FR-030**: Every classified post-boundary attempt MUST preserve the submitted coordinates, accuracy, server-derived kind/work date/time, and nearest Location and nearest distance when available. After locking Config, nearest diagnostics and candidate matching MUST use one loaded snapshot of exactly 76 canonical Locations: nearest MUST evaluate the full snapshot, including inactive rows and without applying radius membership, while candidates, auto-selection, and selected-location revalidation MUST filter active rows from that same snapshot. An exact minimum-distance tie MUST select the Location with the lexicographically smallest canonical `code`; this diagnostic tie-break MUST NOT collapse or auto-select candidates. The attempt MUST preserve the candidate count when candidate matching runs, leave that count absent when an earlier session or quality gate prevents matching, and MUST NOT persist the full candidate list.
- **FR-031**: Nearest-location observation MUST NOT reorder session, quality, or geofence business gates or allow a rejected request to proceed. The derived `nearest_is_approximate` value MUST be true exactly for `WEAK_GPS`; any downstream attempt/report projection that exposes nearest diagnostics MUST expose this value, while the employee action UI remains outside that diagnostic interface.
- **FR-032**: AttendanceAttempt MUST be persisted after the Attendance business transaction ends on accepted and expected business-rejection paths, so a rejected attempt survives business rollback and a database race loser is observable. Unexpected infrastructure exceptions MUST bypass attempt persistence and retain canonical 5xx handling. The system MUST NOT automatically retry a failed AttendanceAttempt write or roll back an already completed business result; writer or infrastructure telemetry MUST be sanitized and contain no coordinates, device metadata, or request IP.
- **FR-033**: The attendance domain MUST expose a report-neutral failure-rate classification in which `LOCATION_CHOICE_REQUIRED` is excluded from both numerator and denominator and the rejection set is exactly the other five non-accepted outcomes. This feature MUST test that classification but MUST NOT add a management report endpoint or screen.
- **FR-034**: The self attendance read model MUST use the authenticated employee, return today's Asia/Ho_Chi_Minh sessions and punches, expose separate Check In/Out times, Location identifiers, and authorized `maps_url` values derived from each punch's captured coordinates, total duration of closed sessions, and `has_open_session`, and MUST NOT accept a client-selected `user_id`.
- **FR-035**: `punch_index` MUST be derived at read time as a one-based sequence across all `IN` and `OUT` Attendance records for the same user and work date ordered by `recorded_at`; it MUST NOT be persisted.
- **FR-036**: The successful Check In/Out result MUST include the Attendance, its session projection, Location and validation result, server time and work date, and derived `punch_index` needed to render the updated timeline. `resolved_address` MUST project `Location.address`. A single backend helper MUST derive `maps_url` from the Attendance's stored captured latitude/longitude—not Location coordinates—using URL encoding while preserving the database decimal representation exactly, with no rounding, interpolation, client-supplied URL, reverse geocoding, or network call. Frontend links MUST use `target="_blank"` and `rel="noopener noreferrer"`; iframe and map SDK embedding are forbidden.
- **FR-037**: PostgreSQL acceptance tests MUST prove the partial open-session uniqueness rule, the absence of daily kind uniqueness, attempt survival after business rollback, and concurrent double-tap behavior using real competing transactions or requests.
- **FR-038**: Under two concurrent Check In requests for one user, exactly one MUST create the open session and accepted Attendance; the other MUST return `SESSION_ALREADY_OPEN`, leaving exactly one open session and one attempt for each request.
- **FR-039**: AttendanceAttempt MUST have PostgreSQL indexes on `(user, work_date, recorded_at, id)`, `(work_date, outcome)`, and `(nearest_location, outcome)`; migration tests MUST inspect all three definitions.
- **FR-040**: Attendance routes and UI MUST remain disabled until the established reference-data readiness check confirms exactly one complete Config and all 76 canonical Locations; a failed check MUST mutate no Attendance, Config, or Location data.
- **FR-041**: Two concurrent Check Out requests for one open session MUST serialize on the open-session row: exactly one creates the OUT Attendance and closes the session, while the other returns `NO_OPEN_SESSION`; each post-boundary request MUST retain its corresponding attempt when observational persistence is available.

### Key Entities

- **Attendance**: An immutable accepted punch for one authenticated user, with server-owned `kind`, `recorded_at`, and `work_date`; submitted GPS evidence; resolved active Location; measured distance; `INSIDE_GEOFENCE` validation; and resolution method. It has no daily uniqueness by kind.
- **AttendanceSession**: One work interval paired from a Check In Attendance to an optional Check Out Attendance. It owns the Check In work date, derived duration when user-closed, and job-closure state. At most one session is open per user.
- **AttendanceAttempt**: Observational history for exactly one classified post-boundary Check In/Out request, successful or expected-business rejected. It records one of seven closed outcomes, submitted location evidence, nearest-location diagnostics, candidate count, and an Attendance link only on acceptance; it is deliberately outside the business transaction and is not created for unexpected infrastructure failures.
- **Location**: An active geofence candidate with identity, point, and radius. Overlapping and coincident Locations remain distinct valid candidates.
- **Config**: The authoritative attendance accuracy threshold and local work-schedule configuration consumed by this feature; attendance never substitutes task GPS thresholds.
- **Self Attendance Read Model**: A projection of the authenticated user's local work date containing ordered punches, derived punch indexes, sessions, total closed-session duration, and open-session state.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of the Definition of Done scenarios pass, including first Check In, duplicate rejection, Check Out, no-session rejection, `IN → OUT → IN → OUT`, weak GPS, outside radius, all candidate-count paths, invalid selection, attempt logging, pre-boundary non-logging, and self-read behavior.
- **SC-002**: In 100 repeated concurrent double-tap trials, exactly one Check In succeeds, exactly one receives `SESSION_ALREADY_OPEN`, no user ends with more than one open session, and both post-boundary requests retain their correct attempts.
- **SC-003**: For all boundary fixtures, acceptance is determined by `accuracy_m <= threshold` and `distance_m <= radius_m` independently, with zero cases where accuracy changes the effective radius.
- **SC-004**: With observational persistence operating normally, every classified post-boundary acceptance or expected-business rejection path produces exactly one observable AttendanceAttempt; every tested pre-boundary rejection and unexpected infrastructure 5xx changes the attempt count by zero. A forced post-transaction attempt-write failure preserves the original business response or exception, performs no automatic retry, and emits sanitized telemetry without coordinates, device metadata, or request IP.
- **SC-005**: A four-punch same-day journey returns punch indexes `1, 2, 3, 4`, produces exactly two sessions, and reports daily work duration equal to the sum of the two closed sessions.
- **SC-006**: 100% of successful attendance actions use server UTC for `recorded_at`, derive the expected Asia/Ho_Chi_Minh `work_date`, and ignore client capture time for payroll timing.
- **SC-007**: In a documented pre-release usability test with at least 20 representative HELPDESK participants, at least 19 must complete an unambiguous Check In or Check Out on the first submission and resolve a multiple-Location prompt without assistance; the evidence record MUST state participant count, scenario, success count, and observed blockers without storing GPS coordinates.
- **SC-008**: In a documented pre-release acceptance run—not a CI wall-clock gate—across 100 measured command-plus-today-read trials against PostgreSQL with 50 users, exactly 76 canonical Locations, and 20 same-day sessions for the acting user, at least 95 trials MUST complete within 2 seconds. Frontend tests MUST separately prove with fake timers that a completed read is rendered without an artificial delay.

## Assumptions

- The authority order is `docs/CHOT_YEU_CAU.md`, `docs/QUY_TAC_CLEAN_CODE.md`, the stakeholder PRD, then current implementation; this specification follows CHOT §§4, 5, 7, 8, 9, and 10 and the project constitution.
- Authentication, account-state checks, canonical error envelopes, RBAC action evaluation, Config, and active Location reference data are supplied by Features 001–003.
- `captured_at` remains optional for compatibility; when supplied it is validated for the 60-second freshness limit, while clients are required to obtain and submit a fresh foreground sample.
- The end-of-day missing-Check-Out process remains an external CHOT dependency. This feature implements the already-governed first-IN/latest-OUT anomaly reconciliation required by each accepted punch, but does not add anomaly values, job scheduling, notifications, manager reports, exports, or manual adjustments.
- The MVP supports no overnight session. AttendanceSession always retains the Check In work date, and an established end-of-day process handles stale open sessions without inventing a Check Out time.
- Device metadata and request IP may be retained as approved audit/risk context but are not used as fraud-proof identity or as substitutes for GPS.

## Scope Boundaries

- Included: HELPDESK self Check In/Out, every-punch GPS validation and candidate resolution, Attendance/AttendanceAttempt/AttendanceSession persistence, governed punch anomaly reconciliation and AuditLog evidence, concurrency invariants, self attendance read projection, derived punch indexing, and the report-neutral attempt failure classification required by FR-033.
- Excluded: MANAGER or LEADER attendance, attendance on behalf of another user, manual adjustment, overnight shifts, continuous/background location tracking, automatic closure on geofence exit, assigned employee Locations, reverse geocoding, task-completion workflows, management report endpoints/screens/exports, new anomaly values, and new job behavior.

## Definition of Done

- [x] First valid Check In creates Attendance, an open session, and an accepted attempt.
- [x] A second Check In while open is rejected with `SESSION_ALREADY_OPEN` and logs the correct attempt.
- [x] Valid Check Out closes the open session and logs an accepted attempt.
- [x] Check Out without an open session is rejected with `NO_OPEN_SESSION` and logs the correct attempt.
- [x] `IN → OUT → IN → OUT` succeeds on one work date with two sessions and derived indexes `1 → 2 → 3 → 4`.
- [x] Weak attendance GPS is rejected before geofence classification with `WEAK_GPS`.
- [x] A point outside every active radius is rejected with `OUTSIDE_RADIUS`.
- [x] Exactly one Location candidate is auto-selected with `AUTO_SINGLE`.
- [x] Multiple Location candidates without a selection return `LOCATION_CHOICE_REQUIRED` and the candidates.
- [x] A selected Location outside the recomputed candidates is rejected with `INVALID_LOCATION_CHOICE`.
- [x] A selected-location resubmission with zero recomputed candidates returns `OUTSIDE_RADIUS`, not `INVALID_LOCATION_CHOICE`.
- [x] Every classified post-boundary business outcome logs exactly one correctly populated AttendanceAttempt, including `ACCEPTED`; unexpected infrastructure 5xx logs none and is never relabeled.
- [x] Every accepted punch atomically creates its canonical Check In/Out AuditLog with a sanitized payload and no OutboxEvent; rejected punches create neither.
- [x] Authentication, authorization, account-state, server-owned-field, malformed GPS, and stale-GPS rejections before the business boundary log no AttendanceAttempt.
- [x] The PostgreSQL partial unique constraint for one open session per user is schema-inspected and behavior-tested.
- [x] All three governed AttendanceAttempt indexes are inspected in PostgreSQL.
- [x] A PostgreSQL concurrent double-tap test proves one winner, one `SESSION_ALREADY_OPEN` loser, one open session, and two correctly retained attempts.
- [x] A PostgreSQL concurrent Check Out test proves one accepted close, one `NO_OPEN_SESSION`, one closed session, and two correctly retained attempts.
- [x] Maps links use stored captured decimals exactly, are authorization-scoped, open with `_blank`/`noopener noreferrer`, and use no iframe/SDK/reverse geocoder.
- [x] Deployment evidence proves reference readiness succeeds before Attendance routes/UI are enabled and failure is read-only.
- [ ] The pre-release 100-trial latency acceptance meets SC-008 outside CI and the documented usability exercise meets SC-007.
