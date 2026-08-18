# US2 Location API verification

Verified 2026-08-18: all roles can list; only Manager can update; permission denial precedes
malformed DTO processing; POST/DELETE are absent; same-value updates are no-ops; stale versions
return `409 LOCATION_VERSION_CONFLICT`; a real two-worker PostgreSQL race has exactly one winner.

Result: pass in the 445-test backend gate.
