# Data Model: Audit and Transactional Outbox

## AuditLog

Canonical immutable evidence row:

- `id`
- `actor`
- `action`
- `target_type`
- `target_id`
- `before`
- `after`
- `recorded_at`

No request/correlation columns are allowed.

## OutboxEvent

R-104 persisted event envelope:

- `event_id`
- `event_type`
- `schema_version`
- `aggregate_type`
- `aggregate_id`
- `aggregate_version`
- `payload`
- `created_at`
- `request_id`
- `correlation_id`
- `publish_state`
- `published_at`
- `lease_expires_at`

Constraints:

- unique `event_id`
- unique `(aggregate_type, aggregate_id, aggregate_version)`
- positive `schema_version`
- positive `aggregate_version`
- closed publish-state vocabulary
