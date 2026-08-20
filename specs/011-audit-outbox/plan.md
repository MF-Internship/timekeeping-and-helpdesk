# Implementation Plan: Audit and Transactional Outbox

## Technical Context

Existing Django modules already provide `audit` domain records, recording ports, persistence adapter, models, ambient correlation, and shared payload validation. Feature 011 formalizes and verifies that implementation against CHOT §9.4/R-104.

## Design

- Keep `AuditLog` as an immutable evidence model with the canonical eight fields.
- Keep `OutboxEvent` as the persisted PostgreSQL source of committed events through `PENDING`, `PUBLISHED`, and `DEAD_LETTER` states.
- Keep `DjangoAuditRecorder` as a thin persistence adapter; it performs validation and inserts rows inside the caller's transaction.
- Keep request/correlation capture adapter-owned through `core.correlation.get_correlation()`.
- Add/maintain static enforcement that `append_*` methods do not own transactions.
- Use real PostgreSQL tests for rollback and constraints.

## Risk Controls

- No schema expansion of `AuditLog`.
- No `transaction.atomic()`/`on_commit()` in append ports.
- No secret-bearing payloads persisted.
- No cross-module state reads from business modules outside approved ports.

## Verification

- Unit: audit records, payload validation, recording adapter static contract.
- PostgreSQL: rollback, constraints, aggregate version uniqueness.
- Architecture: module boundaries.
