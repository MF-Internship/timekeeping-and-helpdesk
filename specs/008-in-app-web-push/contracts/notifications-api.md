# API Contract: Notifications and Push Subscriptions

All routes are under the single `/api/v1/` prefix, require the existing active authenticated account/password gate, return canonical errors, use snake_case, and set `Cache-Control: private, no-store`. DRF generates the committed OpenAPI; this document defines behavior and is not a hand-edited schema substitute.

## Shared projections

### Notification

```text
public_id: UUID
event_type: one of exactly five approved values
title: safe in-app string
created_at: RFC 3339 server timestamp
read_at: RFC 3339 server timestamp | null
is_unread: boolean derived from read_at
```

It does not expose recipient/user ID, target object ID, dedupe key, delivery rows, push content, subscription data, GPS, address, photo, Task/person names from the target, or provider state.

### PushSubscriptionResult

```text
id: UUID (opaque public_id)
is_active: true
created_at: RFC 3339 server timestamp
```

It never returns endpoint, endpoint hash, `p256dh`, `auth`, ciphertext, VAPID private data, user ID, last provider response, or failure details.

## GET `/notifications/`

**Action**: `notification.view.self`

**Input**: No `user_id` or recipient filter. Unknown query fields are rejected.

**200 response**:

```text
items: Notification[] (newest created_at/id first)
unread_count: nonnegative integer computed for request.user
```

The endpoint returns only the caller's rows. Empty inbox is `200` with `[]` and zero. It creates no AuditLog, OutboxEvent, PushDelivery, read transition, or target read.

## PATCH `/notifications/{public_id}/read`

**Action/order**: authentication/account → `notification.update.self` → empty-body DTO/server-owned-field rejection → owner scope → conditional read transition.

**Input**: Empty JSON object or no body. Any field, including `user_id`, `recipient`, `read_at`, event, target, dedupe, title, or timestamp, returns `400 SERVER_OWNED_FIELD` after permission.

**200 response**: Notification projection with the first server `read_at`.

Repeated owner calls return the same timestamp and create no extra side effect. Foreign, malformed, or nonexistent references follow canonical non-disclosing not-found behavior and do not mutate anything.

## GET `/notifications/{public_id}/target`

**Action/order**: authentication/account → `notification.view.self` → owner scope → owning target action permission → current target object scope/state → minimal response.

**200 response union**:

```text
destination: "TASK"
target_id: positive integer
```

or

```text
destination: "ATTENDANCE"
target_id: null
```

The Task ID is returned only after the existing Task read boundary authorizes the caller; the frontend may use it only to focus the already-authorized Task experience. Attendance routes to the caller's current self experience. The endpoint never marks read. Lost assignment/permission/account status, copied cross-account reference, stale/deleted target, malformed UUID, or nonexistent Notification returns canonical non-disclosing denial with zero mutation/audit/outbox/delivery side effect.

## POST `/push-subscriptions/`

**Action/order**: authentication/account → `push_subscription.manage.self` → DTO/server-owned-field validation → endpoint-origin/key validation → atomic owner-bound upsert.

**Request**:

```text
endpoint: nonblank HTTPS URL on an approved exact origin
p256dh: nonblank URL-safe base64 browser key
auth: nonblank URL-safe base64 browser key
```

`user_id`, `id`, endpoint hash, ciphertext, user-agent family, state, timestamps, delivery metadata, and any unknown field are rejected as server-owned/invalid. The raw body is never logged.

**200 response**: PushSubscriptionResult. Registration is idempotent: repeating the same active subscription for the same user returns the same logical active binding; binding an endpoint previously revoked for another account produces one current owner under the active-endpoint constraint.

**Failures**:

- Invalid syntax/key/origin: canonical `400 VALIDATION_FAILED`, no stored material.
- Push disabled/unavailable typed configuration: canonical `503 SERVICE_UNAVAILABLE`; inbox remains functional.
- Database/concurrency conflict not resolved by the atomic upsert: canonical safe error, no partial ownership.

## DELETE `/push-subscriptions/{id}/`

**Action/order**: authentication/account → `push_subscription.manage.self` → reference validation → owner scope → revoke subscription and suppress pending deliveries.

**204 response**: No body. Repeating owner revoke is safe. Foreign/malformed/nonexistent references use canonical non-disclosing behavior. It never accepts `user_id` or exposes subscription material.

Logout/account switch/account inactive invoke the same server revocation application port independently of this endpoint.

## Generic push payload

The encrypted Web Push data has exactly this logical shape:

```text
version: 1
kind: one of the five generic event hints
reference: opaque Notification UUID
```

The service worker supplies constant localized title/body and constructs only the same-origin allowlisted `/notifications/open/{reference}` path. Neither payload nor notification options contain Task/person names, descriptions, notes, IDs other than opaque Notification UUID, GPS, accuracy, address, map/photo/storage URLs, object keys, token/cookie, subscription endpoint/key, dedupe key, or provider response.

## Error and authorization precedence tests

- Unauthenticated/invalid/inactive/forced-change behavior remains the existing canonical gate.
- A caller missing an R-144 action receives `403 PERMISSION_DENIED` before malformed body errors.
- A permitted caller sending server-owned fields receives `400 SERVER_OWNED_FIELD` before object mutation.
- Owner scope and target scope are independent; Notification ownership never authorizes a target.
- Every denied/rejected path asserts no Notification read change, subscription change, delivery, AuditLog, OutboxEvent, Task, Attendance, or User side effect.
