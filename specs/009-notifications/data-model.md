# Data Model: In-App Notifications and Web Push

## Notification

Authoritative in-app notification row. Key fields: recipient, public reference, event type, target type/id, title, dedupe key, created time, and read time.

## PushSubscription

Self-owned browser subscription row. Key fields: user, opaque public id, endpoint hash, encrypted subscription material, active flag, and revocation time.

## PushDelivery

Best-effort delivery row. Key fields: notification, subscription, state, due time, expiry, lease owner/time, attempt metadata, and sanitized failure detail.

## Invariants

- Notification event type is a closed five-value vocabulary.
- Notification dedupe key is unique.
- Push payload is generic and contains no sensitive preview data.
- Push delivery never replaces or mutates in-app notification truth.
