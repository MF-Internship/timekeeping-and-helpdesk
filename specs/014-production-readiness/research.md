# Research: Production Readiness

## Restore probes

Decision: use `audit_outboxevent` for unpublished outbox verification.  
Rationale: Features 011–012 establish `audit.OutboxEvent` as the canonical outbox persistence model.

## Capacity test harness

Decision: keep the 500ms target and increase only the local contract test server backlog.  
Rationale: Windows loopback tests were limited by the fixture server backlog, not by checker semantics.

## Unresolved infrastructure

Decision: keep `UNRESOLVED` production values and evidence as failing readiness state.  
Rationale: CHOT/R-108 require honest failure until real infrastructure is supplied and measured.
