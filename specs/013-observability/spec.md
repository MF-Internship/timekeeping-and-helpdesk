# Feature 013: Operational Telemetry, Health and Retention

**Branch**: `feature/013-observability`  
**Status**: Specified  
**Authority**: `docs/CHOT_YEU_CAU.md` §9.6, `docs/RA_SOAT_YEU_CAU.md` R-106

## Requirements

- Logging must use real Django `LOGGING`, correlation defaults, and canonical named loggers.
- Metrics must use a closed metric/label vocabulary and drop invalid metrics safely.
- Alerts must sanitize URL/token/credential/GPS-like strings and never break business execution.
- Heartbeat health must distinguish `unknown`, `alert`, and `ok`; never-seen heartbeat is `unknown`.
- Retention pruning must be bounded, batched, and only touch canonical operational categories.
- `PENDING` outbox rows and `AuditLog` rows must never be pruned by this feature.
- Management commands must remain thin shims.

## Out of Scope

- External monitoring/alert delivery infrastructure.
- New public APIs.
