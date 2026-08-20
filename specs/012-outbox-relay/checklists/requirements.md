# Requirements Checklist: Feature 012

- [X] `SKIP LOCKED` claim implemented.
- [X] Transport call is outside claim transaction.
- [X] Lease is persisted and reclaimable.
- [X] Retry state is persisted.
- [X] Backoff is capped.
- [X] Failed event does not abort batch.
- [X] Dead-letter rows are retained.
- [X] Failure diagnostics are sanitized.
- [X] Consumer dedupe is transactionally safe.
- [X] Command remains a thin shim.
