# Requirements Checklist: Feature 011

- [X] More than the canonical `AuditLog` shape is not introduced.
- [X] R-104 outbox envelope is preserved.
- [X] Append ports do not own transactions.
- [X] Shared payload filtering covers audit and outbox.
- [X] Secret values are not reported in validation errors.
- [X] Empty correlation context is valid.
- [X] PostgreSQL rollback tests exist.
- [X] Relay/retry/consumer-dedupe behavior is deferred to Feature 012.
