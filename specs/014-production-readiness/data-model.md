# Data Model: Production Readiness

No new production data model is introduced.

Governed artifacts:

- `deploy/environments.yaml`: non-secret environment identities and unresolved infrastructure choices.
- `deploy/recovery-evidence.yaml`: restore/capacity evidence targets and current status.
- migration files: static safety inputs.
- recovery probes: read-only SQL checks.
