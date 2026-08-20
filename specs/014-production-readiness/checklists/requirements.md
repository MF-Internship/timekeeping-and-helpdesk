# Requirements Checklist: Feature 014

- [X] Production readiness cannot pass with unresolved required fields.
- [X] Recovery readiness cannot pass without restore/capacity evidence.
- [X] Recovery DSN collision is rejected before connection.
- [X] Restore verification uses read-only probes.
- [X] Migration safety checks are static and CI-backed.
- [X] Cache policy rejects process-local cache outside development.
- [X] Capacity checker does not leak identities/tokens.
- [X] Real infrastructure evidence is deferred, not fabricated.
