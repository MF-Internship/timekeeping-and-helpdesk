# Quickstart: Operational Telemetry, Health and Retention

```powershell
$env:DATABASE_URL='postgresql://app_runtime:local_runtime_only@127.0.0.1:55432/timekeeping'
uv run --project backend pytest backend/tests/unit/core/test_logging.py backend/tests/unit/core/test_metrics.py backend/tests/unit/operations/test_alerts.py backend/tests/unit/operations/test_telemetry_health.py backend/tests/integration/postgres/operations/test_retention_pruning.py backend/tests/integration/api/test_management_command_discovery.py
```
