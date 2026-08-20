# Contract: Audit and Outbox Events

Feature 011 introduces no public HTTP API.

The internal contract is the CHOT §9.4/R-104 persistence contract:

- `append_audit_entry(entry)` appends a privacy-safe `AuditLog` row in the caller transaction.
- `append_outbox_event(event)` appends a privacy-safe `PENDING` `OutboxEvent` row in the caller transaction.
- Both operations raise before persistence when payload validation fails.
- Neither operation owns commit, rollback, retry, publication, or transport delivery.
