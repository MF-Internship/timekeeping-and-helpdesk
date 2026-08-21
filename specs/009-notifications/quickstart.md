# Quickstart: In-App Notifications and Web Push

## Automated Verification

Run backend notification tests:

```powershell
uv run --project backend pytest backend/tests/unit/notifications backend/tests/integration/api/notifications
```

Run frontend notification tests:

```powershell
npm --prefix frontend run test -- --run frontend/tests/unit/notifications
```

Run contract/schema checks if notification contracts changed:

```powershell
uv run --project backend python scripts/check_openapi.py
npm --prefix frontend run api:check
```

## Manual Deferred Verification

See `docs/DEFERRED_WORK.md` item `DW-F009-01` for real browser/device Web Push permission and delivery.
