# Feature Specification: In-App Notifications and Web Push

**Feature Branch**: `feature/009-notifications`

**Created**: 2026-08-21

**Status**: Ready for validation

**Input**: User description: "Feature 009: In-App Notifications and Web Push"

## Clarifications

### Session 2026-08-21

- Q: Which notification events are in scope? -> A: Exactly the five R-97/CHOT events only: newly assigned Task, Task approaching assigned_date, overdue Task, open AttendanceSession near end of shift, and multi-assignee Task completed by another assignee.
- Q: Is push authoritative? -> A: No. In-app Notification persistence is the complete source; Web Push is explicit opt-in and best-effort.
- Q: What manual verification remains? -> A: Real browser/device push permission and delivery are deferred because CI uses controlled fake transports.

## User Scenarios & Testing

### User Story 1 - Receive Authoritative In-App Notifications (Priority: P1)

Helpdesk users see a complete in-app inbox for only the approved events that currently apply to them.

**Why this priority**: In-app persistence is the canonical notification source and must work even when push is disabled or unavailable.

**Independent Test**: Trigger all five approved events with Web Push disabled and verify recipient-specific inbox rows, unread counts, dedupe, and no rows for excluded users/events.

**Acceptance Scenarios**:

1. **Given** a Task is assigned to a Helpdesk user, **When** the assignment commits, **Then** exactly one unread in-app Notification is stored for that assignee.
2. **Given** a Task reminder job repeats, **When** the same upcoming or overdue occurrence is evaluated again, **Then** no duplicate Notification is created.
3. **Given** a stale assignment/session state, **When** a scheduled notification is revalidated, **Then** delivery is suppressed and the inbox remains authority-preserving.

### User Story 2 - Manage Read State (Priority: P1)

Recipients explicitly mark their own notifications as read without changing ownership or source state.

**Why this priority**: Unread counts are a core inbox workflow and must be scoped to the authenticated recipient.

**Independent Test**: Use two users and repeated/concurrent read calls to prove only the owner row changes once and unread count is updated from server state.

**Acceptance Scenarios**:

1. **Given** an unread Notification, **When** the owner marks it read, **Then** `read_at` is set once using server time and later repeats are idempotent.
2. **Given** a foreign or malformed notification reference, **When** a user attempts to mark it read, **Then** the API does not disclose ownership or mutate any row.

### User Story 3 - Opt In and Revoke Web Push (Priority: P2)

Users explicitly opt in to browser Web Push and can revoke a subscription without losing the in-app inbox.

**Why this priority**: Push improves timeliness but remains secondary to the authoritative in-app source.

**Independent Test**: Register, deliver through a fake provider, revoke, and verify later deliveries are suppressed while inbox rows remain intact.

**Acceptance Scenarios**:

1. **Given** push is enabled and the browser supports Push API, **When** the user grants permission, **Then** the server stores only protected subscription material and returns an opaque subscription identifier.
2. **Given** push permission is denied or unsupported, **When** the inbox is opened, **Then** in-app notifications still work and no subscription is created.

### User Story 4 - Respect Quiet Hours, TTL and Suppression (Priority: P2)

Push delivery observes quiet hours, TTL, retry, lease, dedupe, and stale-state suppression rules.

**Why this priority**: Best-effort push must not leak stale or sensitive work context and must avoid duplicate/provider races.

**Independent Test**: Controlled clocks around 21:00, 07:00, and 24-hour expiry plus competing workers prove due time, expiry, and suppression behavior.

**Acceptance Scenarios**:

1. **Given** a push becomes due during 21:00-07:00 Asia/Ho_Chi_Minh, **When** delivery is planned, **Then** it is delayed until 07:00 and retains a 24-hour TTL boundary.
2. **Given** a Task is completed or an AttendanceSession is checked out before delivery, **When** push is revalidated, **Then** the delivery is suppressed.

### User Story 5 - Open Authorization-Safe Deep Links (Priority: P2)

Recipients resolve opaque notification references to current authorized destinations only after backend ownership and object-scope checks.

**Why this priority**: Notification links must never bypass RBAC, ownership, account state, or object-scope rules.

**Independent Test**: Resolve a valid reference, then remove assignment/permission/account eligibility and verify the same reference becomes non-disclosing.

**Acceptance Scenarios**:

1. **Given** a valid notification reference for an assigned Task, **When** the owner opens it, **Then** the backend returns a minimal Task destination after current authorization checks.
2. **Given** a copied or stale reference, **When** another user opens it, **Then** no target detail is disclosed and no read/source state changes.

### Edge Cases

- Repeated scheduled jobs must not duplicate in-app notifications.
- Push payloads must be generic and contain no Task, employee, GPS, photo, map, URL, token, or private evidence data.
- Logout, account switch, inactive account, explicit revocation, source completion, unassignment, and Check Out must suppress eligible pending/leased push deliveries.
- Account lock and password-reset events are explicitly out of scope and must not create notifications.

## Requirements

### Functional Requirements

- **FR-001**: System MUST persist in-app Notifications as the complete notification source.
- **FR-002**: System MUST support exactly the five CHOT/R-97 notification events and no others.
- **FR-003**: System MUST apply canonical recipient, schedule, dedupe, collapse, and repeated-job semantics for the five events.
- **FR-004**: System MUST expose an authenticated owner-scoped notification list with unread count and no sensitive owner fields.
- **FR-005**: System MUST expose owner-scoped explicit mark-read behavior that is idempotent and server-time owned.
- **FR-006**: System MUST support explicit opt-in PushSubscription registration and revocation.
- **FR-007**: System MUST suppress or revoke push delivery for logout, account switch, inactive account, stale subscriptions, stale target state, and explicit user revocation.
- **FR-008**: System MUST enforce quiet hours 21:00-07:00 Asia/Ho_Chi_Minh and 24-hour push TTL.
- **FR-009**: System MUST use generic Web Push payloads and authorization-safe deep links.
- **FR-010**: System MUST preserve the canonical authorization pipeline and never trust frontend authorization.
- **FR-011**: System MUST defer real browser/device push evidence when a real HTTPS browser/provider environment is unavailable.

### Key Entities

- **Notification**: Authoritative in-app row with recipient, event type, target identity, title, dedupe key, created time, and optional read time.
- **PushSubscription**: Protected self-owned browser subscription material, active/revoked lifecycle, and opaque public identifier.
- **PushDelivery**: Best-effort delivery work item for a Notification and subscription with due, lease, retry, suppression, and terminal state.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All five approved event families create correct in-app notifications for eligible recipients with zero duplicates under repeated jobs.
- **SC-002**: Read/unread state remains correct under repeated and concurrent read attempts.
- **SC-003**: Push opt-in/revoke works without exposing subscription material or making push a source of truth.
- **SC-004**: Quiet-hour, TTL, retry, and stale-state suppression tests pass with controlled clocks.
- **SC-005**: Deep-link resolution denies stale, foreign, inactive, or unauthorized references without target disclosure.

## Assumptions

- Existing Feature 008 implementation is the completed implementation slice for this Feature 009 business scope.
- Real Web Push provider/browser delivery requires staging HTTPS and browser permission and is tracked in `docs/DEFERRED_WORK.md`.
