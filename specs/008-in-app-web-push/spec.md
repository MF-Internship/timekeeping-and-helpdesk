# Feature Specification: In-App Notifications and Web Push

**Feature Branch**: `008-in-app-web-push`

**Created**: 2026-08-21

**Status**: Draft

**Input**: User description: "In-app notifications and opt-in web push for exactly five Task and Attendance events, with unread/read state, quiet hours, TTL, dedupe, suppression, subscription revocation, generic lock-screen content, and authorization-safe deep links."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Receive a Complete In-App Inbox (Priority: P1)

An authenticated user can open an inbox containing every notification addressed to them for the five supported events, regardless of whether web push is supported, enabled, delayed, duplicated, or lost.

**Why this priority**: The in-app inbox is the authoritative source and delivers the feature's core value without depending on browser push delivery.

**Independent Test**: Generate each supported event for eligible recipients while push is disabled, then verify that only the intended recipients can list and open their persisted notifications.

**Acceptance Scenarios**:

1. **Given** an active assignee is newly added to a Task, **when** the assignment commits, **then** that assignee receives one in-app `TASK_ASSIGNED` notification.
2. **Given** an assignee's incomplete Task has an `assigned_date` tomorrow, **when** local server time reaches 17:00 today, **then** that assignee receives one in-app `TASK_UPCOMING` notification.
3. **Given** an assignee's Task remains incomplete after its `assigned_date`, **when** local server time reaches 08:00, **then** that assignee receives at most one `TASK_OVERDUE` notification for that Task and local date.
4. **Given** a HELPDESK user still owns an open Attendance session, **when** local server time reaches 30 minutes before configured shift end, **then** that user receives one `ATTENDANCE_SESSION_OPEN_NEAR_SHIFT_END` notification.
5. **Given** one assignee completes a Task that has multiple assignees, **when** completion commits, **then** every other current assignee receives one `MULTI_ASSIGNEE_TASK_COMPLETED` notification and the completing user receives none.

---

### User Story 2 - Track Read and Unread State (Priority: P1)

An authenticated user can distinguish unread from read notifications and mark one of their own notifications as read without affecting any other user's inbox.

**Why this priority**: Read state makes the authoritative inbox usable and prevents users from repeatedly treating handled information as new.

**Independent Test**: Create notifications for two users, mark one notification as read as its owner, and verify counts, timestamps, idempotency, and cross-user denial.

**Acceptance Scenarios**:

1. **Given** a newly persisted notification, **when** its recipient opens the inbox, **then** it is reported as unread.
2. **Given** an unread notification owned by the caller, **when** the caller marks it read, **then** it records server-authoritative read time and no longer contributes to the unread count.
3. **Given** an already-read notification, **when** its owner marks it read again, **then** the operation succeeds without changing the original read time or creating another side effect.
4. **Given** a notification belonging to another user, **when** the caller lists, reads, marks, or follows it, **then** no notification content or target access is disclosed.

---

### User Story 3 - Opt In to Best-Effort Web Push (Priority: P2)

An authenticated user can explicitly opt a browser into web push, receive privacy-safe reminders when delivery policy permits, and unsubscribe that browser later.

**Why this priority**: Push improves timeliness but remains an optional projection of the complete in-app source.

**Independent Test**: With in-app persistence working, register one browser subscription, exercise allowed and failed push delivery, unsubscribe it, and verify inbox contents remain complete throughout.

**Acceptance Scenarios**:

1. **Given** a compatible browser and explicit user consent, **when** the active user opts in, **then** the browser subscription is registered only for that user without exposing its endpoint in responses, logs, audit, or notification content.
2. **Given** a registered active subscription and an eligible notification outside quiet hours, **when** delivery is attempted, **then** push contains only generic lock-screen-safe content and a non-authorizing navigation reference.
3. **Given** push is denied, unsupported, expired, delayed, duplicated, or unavailable, **when** a supported event occurs, **then** the complete in-app notification still exists and business state is unchanged.
4. **Given** a user unsubscribes a browser, logs out, switches account, or becomes inactive, **when** revocation is processed, **then** affected subscriptions cannot receive later push deliveries.

---

### User Story 4 - Respect Delivery Timing and Current State (Priority: P2)

Users receive timely push only while a notification remains relevant, without quiet-hours interruption or repeat alerts for the same occurrence.

**Why this priority**: Delivery policy prevents disruptive, stale, or duplicate alerts while preserving the inbox record.

**Independent Test**: Use a controlled Asia/Ho_Chi_Minh clock to exercise both quiet-hour boundaries, TTL expiry, repeated scheduling, and state changes before delivery.

**Acceptance Scenarios**:

1. **Given** an eligible event occurs from 21:00 inclusive through 07:00 exclusive, **when** its notification is persisted, **then** the inbox record is immediately available and push is deferred until 07:00.
2. **Given** a deferred push reaches 07:00, **when** the account, recipient scope, subscription, and target state are still eligible, **then** delivery may be attempted once under the stable collapse/dedupe key.
3. **Given** a Task is completed before its upcoming or overdue push, an Attendance session is checked out before its reminder, an assignment is removed before a deferred push, or the account/subscription is no longer active, **when** delivery is revalidated, **then** the stale push is suppressed.
4. **Given** a push is older than 24 hours, **when** a delivery attempt would occur, **then** it is discarded without removing or changing the in-app notification.

---

### User Story 5 - Follow a Safe Notification (Priority: P2)

An authenticated recipient can follow a notification to its current target only if they still have the required action permission and object scope at navigation time.

**Why this priority**: A notification is a hint, never an authorization grant, and stale links must not create an insecure direct-object-reference path.

**Independent Test**: Create a valid notification, then remove assignment, permission, or account eligibility before navigation and verify access is denied without target disclosure.

**Acceptance Scenarios**:

1. **Given** the recipient still has permission and object scope, **when** they follow a notification, **then** they reach the current authorized Task or Attendance experience.
2. **Given** the recipient has lost assignment, permission, object scope, or active-account status, **when** they follow an old in-app or push reference, **then** the server rechecks authorization and denies access using the canonical non-disclosing error behavior.
3. **Given** a copied push reference is opened under another account, **when** navigation is attempted, **then** neither notification nor target data is disclosed.

### Edge Cases

- At exactly 21:00 local time push is deferred; at exactly 07:00 it is outside quiet hours and may be delivered after revalidation.
- A Task reassigned and later assigned back uses assignment-version identity so the new assignment occurrence can notify once without colliding with the earlier occurrence.
- Concurrent event handling or scheduler retries for the same occurrence produce one in-app notification because the stable dedupe key identifies that occurrence.
- A Task with one assignee does not produce the multi-assignee-completed event; removed assignees are not recipients.
- A Task completed at the same time as an upcoming/overdue scan is revalidated against committed current state; no reminder is produced or pushed for a completed Task.
- A Check Out racing the near-shift-end scan suppresses the reminder when the session is no longer open.
- A shift end whose reminder time falls in quiet hours creates the in-app record at the scheduled reminder time but defers push to 07:00 and rechecks that the session remains open.
- Multiple subscriptions may belong to one user; endpoint identity cannot create duplicate active subscriptions, and revoking one browser does not revoke another except during logout, account switch, or account deactivation where all affected subscriptions are revoked.
- Browser permission denial or subscription-storage failure is shown honestly and does not claim opt-in succeeded.
- Opening a notification does not implicitly mark it read unless the user performs the approved read action; a push receipt or click never changes authoritative read state by itself.

## Requirements *(mandatory)*

### Functional Requirements

#### Supported Event Vocabulary and Recipients

- **FR-001**: The feature MUST support exactly these five notification event types and MUST reject or omit any other notification business event: `TASK_ASSIGNED`, `TASK_UPCOMING`, `TASK_OVERDUE`, `ATTENDANCE_SESSION_OPEN_NEAR_SHIFT_END`, and `MULTI_ASSIGNEE_TASK_COMPLETED`.
- **FR-002**: `TASK_ASSIGNED` MUST address only an active assignee newly added to a Task and MUST be eligible immediately after the assignment is committed; its occurrence identity MUST include Task, assignee, and assignment version.
- **FR-003**: `TASK_UPCOMING` MUST address each current active assignee of a Task not in `COMPLETED` state at 17:00 Asia/Ho_Chi_Minh on the calendar day before `assigned_date`.
- **FR-004**: `TASK_OVERDUE` MUST address each current active assignee of a Task not in `COMPLETED` state at 08:00 Asia/Ho_Chi_Minh on every calendar day after `assigned_date`, at most once per Task, recipient, and local date.
- **FR-005**: `ATTENDANCE_SESSION_OPEN_NEAR_SHIFT_END` MUST address the active HELPDESK owner of a session that remains open at configured `shift_end - 30 minutes`, and MUST be suppressed if Check Out has closed the session.
- **FR-006**: `MULTI_ASSIGNEE_TASK_COMPLETED` MUST occur only when a current assignee completes a Task having at least two current assignees, MUST address every other current active assignee after completion commits, MUST exclude `completed_by`, and MUST NOT occur for a single-assignee Task, Manager override, or any completion by a non-assignee.
- **FR-007**: The feature MUST NOT create email, SMS, account-lock, password-change, or password-reset notifications.

#### Authoritative Inbox and Read State

- **FR-008**: A persisted `Notification` inbox record MUST be the authoritative complete source for every eligible supported occurrence; push availability or outcome MUST never determine whether that record exists.
- **FR-009**: Each notification MUST identify its recipient, closed event type, target object type and identifier, stable unique dedupe key, in-app title, server creation time, optional server read time, and an authorization-safe navigation reference.
- **FR-010**: An authenticated caller MUST be able to list only their own notifications in newest-first order, including enough state to distinguish read from unread and obtain an unread count; the request MUST NOT accept a client-supplied recipient/user identifier.
- **FR-011**: An authenticated recipient MUST be able to mark only their own notification read. The first transition MUST set server-authoritative `read_at`; repetitions MUST preserve that timestamp and create no duplicate side effect.
- **FR-012**: Notification listing, read mutation, and target navigation MUST enforce authentication, centralized action permission, input validation where applicable, recipient/object scope, current target authorization, then state rules in the constitution-mandated order.

#### Push Subscription Lifecycle and Privacy

- **FR-013**: Web push MUST be opt-in per browser subscription and MUST remain optional; unsupported browsers, denied consent, delivery failure, or no subscription MUST leave the in-app feature fully usable.
- **FR-014**: Subscription registration and revocation MUST operate only on `request.user`, MUST NOT accept `user_id`, and MUST prevent one user from viewing, replacing, or revoking another user's subscription.
- **FR-015**: A browser subscription endpoint MUST be treated as an operational secret: plaintext endpoint and encrypted subscription material MUST NOT appear in API responses, application logs, audit payloads, outbox payloads, telemetry, schemas, or examples.
- **FR-016**: The system MUST keep at most one active record for the same browser subscription identity, associate it with exactly one user, and make repeated registration safe without creating duplicate active delivery targets.
- **FR-017**: Logout and account switch MUST revoke all push subscriptions affected by the departing account, and account deactivation MUST revoke all subscriptions belonging to the inactive account before any later delivery attempt can succeed.
- **FR-018**: Unsubscribe MUST revoke the caller-owned subscription even when the external browser unsubscribe step is already missing or expired; repeated revocation MUST be safe.
- **FR-019**: Push content visible on a lock screen MUST be generic and MUST NOT contain Task names or descriptions, person names, notes, GPS coordinates, addresses, photo data or URLs, object-storage keys, subscription details, tokens, or other sensitive business content.
- **FR-020**: A push MUST carry only the minimum generic event hint and a non-authorizing opaque navigation reference; detailed content MUST be fetched after authentication and current authorization checks.

#### Scheduling, Quiet Hours, TTL, Dedupe, and Suppression

- **FR-021**: All scheduling and boundary decisions MUST use server-authoritative time in `Asia/Ho_Chi_Minh`.
- **FR-022**: Quiet hours MUST be the half-open local interval `[21:00, 07:00)` spanning midnight. Eligible events during this interval MUST be persisted in-app immediately and their push attempt deferred to 07:00.
- **FR-023**: Every push MUST expire 24 hours after its notification occurrence; expired push MUST be discarded while its in-app record remains unchanged.
- **FR-024**: Every supported occurrence MUST have one stable dedupe key used to prevent duplicate in-app rows and one stable collapse/dedupe identity for best-effort push retries.
- **FR-025**: Dedupe enforcement MUST remain correct under concurrent handlers, repeated schedule scans, retry, and redelivery; a pre-check alone is insufficient to claim uniqueness.
- **FR-026**: Immediately before push enqueue/delivery, the system MUST revalidate active-account status, active caller-owned subscription, intended recipient, current object scope, current target state, quiet-hours eligibility, and TTL. A failed check MUST suppress push without deleting or falsifying the inbox history.
- **FR-027**: Task upcoming/overdue delivery MUST be suppressed when the Task is completed or the user is no longer a current eligible assignee; open-session delivery MUST be suppressed after Check Out; assignment-related deferred delivery MUST be suppressed after assignment removal; multi-assignee completion MUST never be delivered to `completed_by`.
- **FR-028**: Push loss, delay, duplication, provider rejection, or suppression MUST NOT mutate Task, Attendance, account, assignment, or Notification read state and MUST NOT cause the originating business transaction to fail.

#### Safe Navigation and Scope Boundaries

- **FR-029**: Listing or opening a notification MUST recheck recipient ownership, and following its target MUST independently recheck current account state, action permission, and object scope; possession of a notification or push reference MUST confer no access.
- **FR-030**: Stale, revoked, cross-account, unauthorized, malformed, or nonexistent notification navigation MUST use canonical non-disclosing error semantics and MUST produce no business, audit, outbox, delivery, or read-state side effect unless an approved successful read action is explicitly requested.
- **FR-031**: The notification module MUST consume Task, assignment, completion, Attendance-session, account-state, and logout facts through approved application boundaries; it MUST NOT become a second source of truth for those business states.
- **FR-032**: The feature MUST use the approved API namespace and error envelope, keep wire fields in `snake_case`, preserve private/no-store response handling, and keep generated contracts and client artifacts synchronized.

### Key Entities

- **Notification**: The authoritative recipient-owned inbox record for one supported event occurrence, including event and target identity, a globally unique stable dedupe key, safe in-app title, creation time, optional read time, and safe navigation reference.
- **PushSubscription**: One user's opt-in browser delivery target, represented by a non-reversible endpoint identity, encrypted subscription material, browser-family metadata, active/revoked state, last-use time, and creation time. Plaintext endpoint data is secret and never returned.
- **PushDelivery**: A durable best-effort plan to project one Notification to one active subscription, carrying only state, timing, expiry, attempt/lease metadata, a stable collapse identity, and a non-sensitive failure code. It stores no push payload or subscription endpoint and never replaces the Notification.
- **Notification Event Type**: The closed five-value vocabulary in FR-001; each value defines recipient selection, occurrence identity, schedule, and current-state suppression rule.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In controlled acceptance runs covering all five event types with push disabled, 100% of eligible recipients receive exactly one in-app notification and 0% of ineligible users receive one.
- **SC-002**: In controlled read-state tests, 100% of new notifications appear unread, the first approved read action changes only the caller-owned item, and repeated actions preserve the original read time.
- **SC-003**: Across quiet-hour boundary tests at 20:59, 21:00, 06:59, and 07:00 Asia/Ho_Chi_Minh, 100% of inbox records remain immediately available while no push is attempted inside quiet hours.
- **SC-004**: Across concurrent duplicate-event and repeated-scan tests for all five event types, each logical recipient occurrence yields exactly one persisted inbox record.
- **SC-005**: Across stale-state cases for completed Tasks, removed assignees, closed Attendance sessions, inactive accounts, revoked subscriptions, and expired 24-hour deliveries, 100% of invalid push attempts are suppressed.
- **SC-006**: Automated privacy inspection finds zero Task/person names, notes, GPS, addresses, photos, sensitive URLs, object keys, tokens, or subscription endpoints in push content, contracts, examples, logs, audit, outbox, and telemetry.
- **SC-007**: In cross-account and stale-deep-link tests, 100% of unauthorized navigation attempts disclose no notification or target data and create no forbidden side effect.
- **SC-008**: Users can opt in or revoke a browser subscription in one interaction, and the displayed state matches the authoritative result in 100% of supported-browser acceptance cases.
- **SC-009**: Push transport failure in controlled acceptance tests causes zero loss of in-app records and zero rollback or alteration of originating Task, Attendance, account, or assignment behavior.
- **SC-010**: Under normal service operation, every eligible notification becomes visible in the recipient inbox within 60 seconds after its source occurrence commits or its scheduled evaluation time is reached.

## Assumptions

- Authority follows `docs/CHOT_YEU_CAU.md` §9.1.1, `docs/QUY_TAC_CLEAN_CODE.md`, decisions R-97 and R-144–R-147, the project constitution, then lower-authority artifacts.
- Existing authentication, account-state enforcement, Task assignment/completion, Attendance sessions, configured shift end, canonical errors, and centralized permissions are dependencies and remain their owning modules' sources of truth.
- `assigned_date` is a local calendar date and `COMPLETED` is the canonical terminal Task state already owned by Task management.
- Inbox retention beyond the feature's delivery TTL follows the project's general data-retention policy; the 24-hour TTL applies only to push delivery and never deletes authoritative Notification history.
- In-app presentation may resolve currently authorized details after authentication; persisted push content and lock-screen payload remain generic.
- Push is browser-based web push only. Native mobile push, email, SMS, account-security alerts, WebSocket/SSE live updates, and notification preferences beyond explicit browser opt-in are outside scope.

## Out of Scope

- Email, SMS, native mobile push, and third-party chat notifications.
- Notifications for login, logout, account lock/unlock, password creation, password change, or password reset.
- User-defined schedules, per-event preference controls, or configurable quiet hours for MVP.
- New Task, Attendance, identity, reporting, or job-health business behavior beyond consuming their approved state and events.
- Treating push receipt, click, provider response, or browser state as authoritative proof that a user read a notification.
