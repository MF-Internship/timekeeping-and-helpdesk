# Tasks: Audit and Transactional Outbox

- [X] T001 Create Feature 011 Spec Kit artifacts tied to CHOT §9.4/R-104.
- [X] T002 Confirm `AuditLog` canonical shape is pinned by tests.
- [X] T003 Confirm `OutboxEvent` R-104 envelope and DB constraints are pinned by tests.
- [X] T004 Confirm append ports use shared payload validation before persistence.
- [X] T005 Confirm forbidden payload paths are reported without protected values.
- [X] T006 Confirm empty ambient request/correlation context appends successfully.
- [X] T007 Confirm append ports do not use `transaction.atomic()` or `transaction.on_commit()`.
- [X] T008 Confirm caller rollback removes business state, audit rows, and outbox rows using PostgreSQL.
- [X] T009 Confirm aggregate-version uniqueness and positive-version DB constraints.
- [X] T010 Run focused audit/outbox, payload, and architecture tests.
