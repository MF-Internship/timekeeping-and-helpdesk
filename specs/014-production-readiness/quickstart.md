# Quickstart: Production Readiness

```powershell
$env:DATABASE_URL='postgresql://app_runtime:local_runtime_only@127.0.0.1:55432/timekeeping'
uv run --project backend pytest backend/tests/unit/core/test_deployment.py backend/tests/unit/core/test_cache.py backend/tests/unit/config/test_cache_settings.py backend/tests/integration/postgres/test_verify_restore.py backend/tests/contract/test_deployment_checks.py backend/tests/contract/test_migration_safety.py backend/tests/contract/test_capacity_check.py backend/tests/contract/test_cache_deployment.py backend/tests/contract/test_cache_migration.py backend/tests/contract/test_readiness_baseline.py
```

Expected: automated machine-verifiable checks pass; production/recovery readiness commands still fail while real evidence remains unresolved.
