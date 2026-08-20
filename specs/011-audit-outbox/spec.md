# Feature 011: Audit and Transactional Outbox

**Branch**: `feature/011-audit-outbox`  
**Status**: Specified  
**Authority**: `docs/CHOT_YEU_CAU.md` §9.4, `docs/RA_SOAT_YEU_CAU.md` R-104, `docs/QUY_TAC_CLEAN_CODE.md`

## User Scenarios

### US1 — Mutations append immutable audit evidence

When a governed business mutation succeeds, the application appends exactly the approved `AuditLog` row for that action with the canonical eight-column shape and privacy-safe before/after payloads.

### US2 — Publishers append committed outbox events

When an approved publisher emits an event, the application appends an `OutboxEvent` using the R-104 envelope, ambient request/correlation context, and a `PENDING` publish state.

### US3 — Caller rollback removes evidence

When the caller business transaction rolls back after audit/outbox append, the business state, `AuditLog`, and `OutboxEvent` all roll back together.

## Functional Requirements

- **FR-001**: `AuditLog` MUST keep the canonical fields `{id, actor, action, target_type, target_id, before, after, recorded_at}` and MUST NOT gain request/correlation columns.
- **FR-002**: `OutboxEvent` MUST contain the R-104 envelope fields and constraints, including unique `event_id`, aggregate identity/version, ambient `request_id`/`correlation_id`, payload, and publish state.
- **FR-003**: `append_audit_entry` and `append_outbox_event` MUST join the caller transaction and MUST NOT call `transaction.atomic()` or `transaction.on_commit()` internally.
- **FR-004**: Shared payload validation MUST run at the port boundary before persistence for both audit and outbox payloads.
- **FR-005**: Payload validation MUST reject exact forbidden keys and any URL-like string value while reporting only the payload path, not the secret value.
- **FR-006**: Empty request/correlation context is valid outside an HTTP request and MUST NOT block event append.
- **FR-007**: Cross-module business state access MUST remain through approved application ports/composition adapters only.

## Success Criteria

- **SC-001**: PostgreSQL rollback tests prove business state, audit, and outbox rows do not survive caller rollback.
- **SC-002**: Static tests fail if either append port opens its own transaction or registers `on_commit`.
- **SC-003**: Model contract tests pin the canonical `AuditLog` and `OutboxEvent` envelope.
- **SC-004**: Payload tests reject protected data without leaking protected values.

## Out of Scope

- Reliable relay, persisted retry attempts, consumer deduplication, alerting, and dead-letter operations belong to Feature 012.
- New audit read APIs are not introduced.
