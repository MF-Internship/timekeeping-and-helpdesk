# Quickstart: Reliable Outbox Relay

Run focused verification with a real PostgreSQL database:

```powershell
$env:DATABASE_URL='postgresql://app_runtime:local_runtime_only@127.0.0.1:55432/timekeeping'
uv run --project backend pytest backend/tests/unit/audit/test_outbox_relay_domain.py backend/tests/unit/audit/test_outbox_relay_service.py backend/tests/integration/postgres/audit/test_outbox_relay.py backend/tests/integration/api/test_management_command_discovery.py
```

Run the command with an explicit transport:

```powershell
$env:OUTBOX_RELAY_TRANSPORT='logging'
uv run --project backend python manage.py relay_outbox --worker-id local-worker
```
