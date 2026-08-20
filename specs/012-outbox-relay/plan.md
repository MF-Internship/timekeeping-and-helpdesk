# Implementation Plan: Reliable Outbox Relay

## Technical Context

Feature 011 provides `OutboxEvent` append. Feature 012 adds relay state, a relay application service, a Django repository, a transport port, safe alerts, a consumer dedupe model, and a thin command under `operations`.

## Design

- Extend `audit.OutboxEvent` with persisted relay state.
- Add `audit.ProcessedEvent` for consumer idempotency.
- Implement `DjangoOutboxRelayRepository` for short claim transactions and conditional finalization.
- Implement `OutboxRelayService` so transport calls happen after claim returns.
- Provide closed transport registry values: `disabled` and `logging`.
- Keep command logic under `operations/management/commands/relay_outbox.py` as delegation only.

## Verification

- Unit: backoff, config validation, sanitization, batch isolation.
- PostgreSQL: concurrent `SKIP LOCKED` claims, lease reclaim, success/failure/dead-letter, dedupe rollback.
- Static: command thinness.

## Deferred

Real external transport delivery requires provider credentials and environment routing; tracked as `DW-F012-01`.
