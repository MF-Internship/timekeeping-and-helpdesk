# Contract: Production Readiness

No public API contract is added.

CLI contracts:

- `deployment_check.py isolation`: fails on identity/cache isolation defects.
- `deployment_check.py production-ready`: fails while required production fields are unresolved.
- `deployment_check.py recovery-ready`: fails without passed, current restore/capacity evidence.
- `migration_check.py check`: fails unsafe migration graph/patterns.
- `capacity_check.py measure`: fails below 50 identities, below concurrency 20, or above p95 target.
- `manage.py verify_restore`: verifies only an isolated recovery database with read-only probes.
