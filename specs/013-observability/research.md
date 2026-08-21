# Research: Operational Telemetry, Health and Retention

## Metrics

Decision: closed in-process registry with explicit label vocabularies.  
Rationale: prevents accidental high-cardinality series and unsafe labels.

## Retention

Decision: application service depends on a retention port; Django adapter owns ORM deletes.  
Rationale: operations application remains framework-light and pruning categories stay explicit.

## Heartbeat

Decision: never-seen heartbeat evaluates to `unknown`, stale to `alert`, fresh to `ok`.  
Rationale: absence of evidence is not healthy evidence under R-106.
