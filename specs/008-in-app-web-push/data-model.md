# Data Model: In-App Notifications and Web Push

## Canonical enums

### NotificationEventType — exactly five

- `TASK_ASSIGNED`
- `TASK_UPCOMING`
- `TASK_OVERDUE`
- `ATTENDANCE_SESSION_OPEN_NEAR_SHIFT_END`
- `MULTI_ASSIGNEE_TASK_COMPLETED`

### NotificationTargetType

- `TASK`
- `ATTENDANCE_SESSION`

### PushDeliveryState

- `PENDING`: waiting for `not_before`/retry time.
- `LEASED`: claimed by one worker until `lease_expires_at`.
- `DELIVERED`: provider accepted the attempt; this is not proof the user read it.
- `SUPPRESSED`: current account/subscription/recipient/scope/target state is ineligible.
- `EXPIRED`: 24-hour TTL elapsed before delivery.

### PushFailureCode

Closed technical vocabulary only, such as `TRANSIENT_PROVIDER_FAILURE`, `SUBSCRIPTION_GONE`, `ORIGIN_REJECTED`, `CONFIGURATION_UNAVAILABLE`, and `TRANSPORT_TIMEOUT`. No provider body, URL, endpoint, token, or exception text is persisted.

## Task expansion

Add `Task.assignment_version`:

- Positive bigint, server-owned.
- Python default and database default `1`; `NOT NULL`.
- Increment exactly once while holding the Task row lock whenever the normalized assignee set truly changes.
- Creation notifications use version 1. Remove/re-add later uses the later version.
- Content/status/no-op assignee updates do not increment it.
- It is not an HTTP optimistic version and is not accepted in any request DTO.

## Notification

The authoritative inbox record for one logical recipient occurrence.

| Field | Shape | Rule |
|---|---|---|
| `id` | bigint PK | Internal ordering only |
| `public_id` | UUID | Server-generated, immutable, unique; opaque navigation reference |
| `recipient` | FK User, PROTECT | Exactly one owner; current account checked on access |
| `event_type` | varchar | One of exactly five enum values; DB check |
| `target_type` | varchar | `TASK` or `ATTENDANCE_SESSION`; DB check |
| `target_id` | positive bigint | Server-owned source identity; never grants access |
| `dedupe_key` | varchar | Stable server key, globally unique, nonblank |
| `title` | varchar | Safe in-app event title, nonblank; not copied into push |
| `occurred_at` | timestamptz | Server occurrence time |
| `created_at` | timestamptz | Server persistence time/default |
| `read_at` | nullable timestamptz | First server read transition only; `read_at >= created_at` |

Constraints and indexes:

- Unique `public_id` and `dedupe_key`.
- Check closed event/target vocabularies, positive target ID, nonblank key/title, read-time shape.
- Index `(recipient_id, created_at DESC, id DESC)` for inbox.
- Partial index `(recipient_id, created_at DESC, id DESC) WHERE read_at IS NULL` for unread count/list.
- Optional target lookup index `(target_type, target_id, recipient_id)` for suppression.

Occurrence keys are versioned strings generated in one domain function:

- Task assigned: event + Task ID + recipient ID + assignment version.
- Upcoming: event + Task ID + recipient ID + assigned date.
- Overdue: event + Task ID + recipient ID + occurrence local date.
- Open session: event + AttendanceSession ID + recipient ID.
- Multi completion: event + Task ID + recipient ID.

The database insert uses named-conflict handling for `dedupe_key`; other integrity failures propagate and roll back the caller.

## PushSubscription

One opt-in browser subscription bound to one user.

| Field | Shape | Rule |
|---|---|---|
| `id` | bigint PK | Internal |
| `public_id` | UUID | Returned to owner for revoke; unique |
| `user` | FK User, PROTECT | Exactly one current owner |
| `endpoint_hash` | fixed 64-char hex | SHA-256 of normalized endpoint; plaintext never stored separately |
| `encrypted_subscription` | binary/text ciphertext | Authenticated encryption of endpoint + `p256dh` + `auth`; never serialized/logged |
| `user_agent_family` | closed/sanitized short text | Derived from request header, not client body |
| `is_active` | boolean | Server-owned, DB default true, non-null |
| `revoked_at` | nullable timestamptz | Required iff inactive |
| `last_used_at` | nullable timestamptz | Updated after accepted delivery, never client-owned |
| `created_at` | timestamptz | Server default |

Constraints and indexes:

- Unique `public_id`.
- Partial unique active endpoint identity: `UNIQUE(endpoint_hash) WHERE is_active`.
- Check 64 lowercase hex hash; active/revoked timestamp shape.
- Index `(user_id, is_active, id)` and endpoint hash lookup.
- Upsert locks conflicting endpoint identities in deterministic order, deactivates prior active ownership if account switched, and returns one active row for the current owner.

## PushDelivery

Durable best-effort scheduling/lease record for one Notification × subscription.

| Field | Shape | Rule |
|---|---|---|
| `id` | bigint PK | Claim order tiebreaker |
| `notification` | FK Notification, PROTECT | Inbox row remains authoritative |
| `subscription` | FK PushSubscription, PROTECT | Delivery target identity; material remains encrypted on parent |
| `state` | varchar | Closed five-value state, DB default `PENDING` |
| `not_before` | timestamptz | Immediate occurrence time or next 07:00 local quiet release |
| `expires_at` | timestamptz | Exactly occurrence + 24 hours |
| `collapse_key` | short ASCII | Stable event occurrence key acceptable to push Topic constraints |
| `attempt_count` | nonnegative integer | DB default 0 |
| `next_attempt_at` | timestamptz | Due retry time, never beyond expiry |
| `lease_expires_at` | nullable timestamptz | Required only while leased |
| `leased_by` | short nullable identifier | Non-secret worker identity, leased only |
| `attempted_at` | nullable timestamptz | Last attempted time |
| `failure_code` | nullable varchar | Closed non-sensitive code only |
| `created_at` | timestamptz | Server default |

Constraints and indexes:

- Unique `(notification_id, subscription_id)`.
- `not_before < expires_at`; `next_attempt_at <= expires_at`; nonnegative attempts.
- State shape: PENDING has no lease; LEASED has lease and worker; terminal states have no lease; DELIVERED has attempted time; SUPPRESSED/EXPIRED require no provider detail.
- Index `(state, next_attempt_at, expires_at, id)` for due work.
- Index `(subscription_id, state, id)` and `(notification_id, state, id)` for revocation/suppression.

## Relationships

```text
User 1 ── * Notification 1 ── * PushDelivery * ── 1 PushSubscription * ── 1 User
                  │
                  └── opaque reference to Task or AttendanceSession

Task 1 ── * TaskAssignee
  └── assignment_version identifies assignee-set occurrences
```

No FK from Notification to Task/AttendanceSession is introduced because the target type is polymorphic and the owning module remains authoritative. Target reads and suppression always go through typed application ports and current authorization.

## State transitions

### Notification read

```text
UNREAD (read_at = null) ── owner read action ──> READ (read_at = server time)
READ ── repeated owner read action ──> READ (original read_at preserved)
```

### Subscription

```text
absent/revoked ── owner opt-in ──> active
active ── repeat same-owner opt-in ──> active (same logical target)
active ── unsubscribe/logout/account switch/inactive/provider-gone ──> revoked
revoked ── revoke again ──> revoked (no side effect)
```

### Delivery

```text
PENDING ── due + valid claim ──> LEASED
PENDING/LEASED ── stale/revoked/inactive ──> SUPPRESSED
PENDING/LEASED ── TTL reached ──> EXPIRED
LEASED ── provider accepted ──> DELIVERED
LEASED ── transient failure before TTL ──> PENDING(next_attempt_at)
LEASED ── permanent invalid subscription ──> SUPPRESSED (+ revoke subscription)
LEASED ── lease timeout ──> reclaimable LEASED by conditional claim
```

Provider acceptance never transitions Notification read state.

## Transaction and lock order

1. Source mutations lock User/Task/AttendanceSession according to the owning use case.
2. They persist source state, then invoke injected notification/suppression/revocation port inside the same UoW.
3. Adapter locks/updates Notification, PushSubscription, then PushDelivery rows in stable ID order; it never opens/commits its own outer transaction.
4. Scheduled scan locks and revalidates source through its fact port before inserting notification rows.
5. Delivery reads a candidate ID, locks/revalidates source first, then conditionally leases the candidate. It commits before decrypting/calling the provider.
6. Finalization locks only the leased delivery/subscription and matches `leased_by`/lease token before updating.

This order must be covered by PostgreSQL race tests; a read-before-write precheck is not cited as correctness.

## Migration compatibility

- Expand Task first with database default 1; old application processes can insert/update without knowing the field.
- Create Notification in `0001_notification`, then PushSubscription/PushDelivery in `0002_push_delivery`; both are expand-only and leave one linear leaf.
- Deploy migrations before application/scheduler activation.
- The previous application version ignores new tables/field. New code tolerates no Notification rows and push disabled.
- No contract-phase migration is included.
