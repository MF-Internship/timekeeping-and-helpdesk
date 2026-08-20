# Quickstart: Audit and Transactional Outbox

Run focused verification with a real PostgreSQL database:

```powershell
$env:DATABASE_URL='postgresql://app_runtime:local_runtime_only@127.0.0.1:55432/timekeeping'
uv run --project backend pytest backend/tests/unit/audit backend/tests/unit/core/test_event_payload.py backend/tests/integration/postgres/audit backend/tests/architecture/test_module_boundaries.py
```

Expected result:

- audit/outbox unit tests pass;
- PostgreSQL rollback and constraint tests pass;
- architecture boundary tests pass.
