# Feature 012: Reliable Outbox Relay

**Branch**: `feature/012-outbox-relay`  
**Status**: Specified  
**Authority**: `docs/CHOT_YEU_CAU.md` §9.5, `docs/RA_SOAT_YEU_CAU.md` R-105

## User Scenarios

### US1 — Concurrent workers publish without duplicate claims

Multiple relay workers claim due `PENDING` events using PostgreSQL row locks with `SKIP LOCKED`, and each event is leased by at most one worker at a time.

### US2 — Failed publication retries safely

Transient transport failures persist attempt count, sanitized error, and bounded exponential retry timing without aborting the rest of the batch.

### US3 — Exhausted events become visible dead letters

After `max_attempts`, an event remains in PostgreSQL as `DEAD_LETTER` with a sanitized diagnostic and a safe alert.

### US4 — Consumers dedupe transactionally

Consumers record `(consumer, event_id)` inside their own work transaction so rollback removes the dedupe marker.

## Functional Requirements

- **FR-001**: Relay progress MUST be persisted on `OutboxEvent`: `attempt_count`, `next_attempt_at`, `lease_expires_at`, `leased_by`, and `last_error`.
- **FR-002**: Claim MUST use `select_for_update(skip_locked=True)` and a persisted lease.
- **FR-003**: Claim transactions MUST NOT wrap transport calls.
- **FR-004**: Expired leases MUST be automatically reclaimable.
- **FR-005**: Retry delay MUST be `min(base * 2 ** (attempt - 1), max)`.
- **FR-006**: One failed event MUST NOT abort remaining claimed events.
- **FR-007**: Exhausted events MUST remain in PostgreSQL as `DEAD_LETTER`; they MUST NOT be deleted.
- **FR-008**: Stored errors, logs, and alerts MUST sanitize URL/token/credential/GPS-like values.
- **FR-009**: Consumer dedupe MUST use `UNIQUE(consumer, event_id)` and participate in the caller transaction.
- **FR-010**: The management command MUST be a thin shim.
- **FR-011**: Relay configuration MUST reject invalid/zero values and unknown transport names.

## Success Criteria

- **SC-001**: PostgreSQL thread tests prove two workers claim disjoint event sets.
- **SC-002**: Lease-expiry tests prove dead-worker rows are reclaimable.
- **SC-003**: Retry/dead-letter tests prove capped backoff, sanitized errors, and retained rows.
- **SC-004**: Consumer rollback tests prove dedupe is transactionally safe.

## Out of Scope

- A real external broker/provider adapter and production delivery evidence are deferred until infrastructure is provided.
- Retention pruning and operational health aggregation belong to Feature 013.
