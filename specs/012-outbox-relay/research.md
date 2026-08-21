# Research: Reliable Outbox Relay

## Claiming

Decision: claim due `PENDING` rows with `select_for_update(skip_locked=True)` in a short transaction and persist `leased_by`/`lease_expires_at`.  
Rationale: two live workers get disjoint sets and crashed workers are recoverable by lease expiry.

## Attempt accounting

Decision: increment `attempt_count` during claim.  
Rationale: R-105 requires the retry budget to be consumed once work is taken so a hung transport cannot retry forever.

## Transport registry

Decision: closed registry with `disabled` and `logging` local adapters.  
Rationale: the repository has no approved external broker configuration yet; invalid names fail closed and real provider evidence is deferred.

## Consumer dedupe

Decision: `ProcessedEvent` stores `(consumer, event_id)` and uses PostgreSQL `ON CONFLICT DO NOTHING`.  
Rationale: caller rollback removes the marker, while duplicate delivery does not break the caller transaction.
