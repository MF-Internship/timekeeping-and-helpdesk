# Tasks: Reliable Outbox Relay

- [X] T001 Create Feature 012 Spec Kit artifacts tied to CHOT §9.5/R-105.
- [X] T002 Add persisted relay fields to `OutboxEvent`.
- [X] T003 Add `ProcessedEvent` with `UNIQUE(consumer, event_id)`.
- [X] T004 Implement relay domain policy for lease and capped backoff.
- [X] T005 Implement repository claim with `select_for_update(skip_locked=True)`.
- [X] T006 Keep transport calls outside the claim transaction.
- [X] T007 Implement conditional publish success finalization.
- [X] T008 Implement failure retry and `DEAD_LETTER` retention.
- [X] T009 Sanitize stored/logged/alerted transport failures.
- [X] T010 Implement consumer dedupe inside caller transaction.
- [X] T011 Add closed transport registry and fail-closed settings.
- [X] T012 Add thin `relay_outbox` management command.
- [X] T013 Add unit and PostgreSQL concurrency tests.
- [X] T014 Record real external transport verification as deferred work.
