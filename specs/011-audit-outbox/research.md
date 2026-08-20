# Research: Audit and Transactional Outbox

## R-104 transaction ownership

Decision: preserve append ports as caller-transaction participants.  
Rationale: CHOT §9.4/R-104 require audit/outbox evidence to disappear when the business change rolls back.  
Rejected: internal `transaction.atomic()` or `transaction.on_commit()` because either can leave evidence for a business change that did not commit.

## Payload filtering

Decision: use the shared `core.event_payload` validator at domain record construction and persistence adapter boundary.  
Rationale: duplicate validation is cheap and protects both direct domain construction and adapter entry points. Exact-key matching preserves allowed business state such as `must_change_password`.

## Correlation

Decision: keep correlation adapter-owned via ambient context and permit empty strings outside requests.  
Rationale: scheduled jobs and commands may validly emit events without an HTTP request.
