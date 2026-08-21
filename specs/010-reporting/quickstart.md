# Quickstart: Reporting, Dashboard and Export

Run backend report tests:

```powershell
$env:DATABASE_URL='postgresql://app_runtime:local_runtime_only@127.0.0.1:55432/timekeeping'
uv run --project backend pytest backend/tests/integration/api/reporting backend/tests/unit/attendance/test_domain_contract.py
```

Run frontend report tests:

```powershell
npm --prefix frontend run test -- --run tests/unit/reports
```

Run contract checks:

```powershell
uv run --project backend python scripts/check_openapi.py --all
npm --prefix frontend run api:check
```
