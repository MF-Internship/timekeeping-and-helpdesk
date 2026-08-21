# Contract: Reliable Outbox Relay

No public HTTP API is added.

Internal relay contract:

- `claim_batch(worker_id, config)` leases due rows and returns committed claim records.
- `transport.publish(message)` runs after the claim transaction.
- `mark_published(message)` succeeds only for the same lease identity.
- `mark_failed(message, reason, config)` persists retry or dead-letter state only for the same lease identity.
- `mark_processed(consumer, event_id)` returns `true` once per consumer/event in the caller transaction.
