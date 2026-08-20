# Data Model: Reliable Outbox Relay

## OutboxEvent additions

- `attempt_count`: persisted attempt budget consumed on claim.
- `next_attempt_at`: due time for retry; null means immediately due.
- `lease_expires_at`: persisted lease expiry.
- `leased_by`: non-secret worker identity.
- `last_error`: sanitized, bounded diagnostic.

## ProcessedEvent

- `consumer`
- `event_id`
- `processed_at`

Constraint: unique `(consumer, event_id)`.
