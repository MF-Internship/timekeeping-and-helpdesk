# Quickstart: Feature 015 Validation

## Targeted development checks

```powershell
cd frontend
npm test -- --run tests/unit/shell tests/unit/ui
npm test -- --run tests/unit/notifications tests/unit/reports
npm run lint
npm run typecheck
```

## Broad completion checks

```powershell
cd frontend
npm test
npm run lint
npm run typecheck
npm run api:check
npm run build
npm run test:e2e
```

## End-to-end expectations

1. Sign in with HELPDESK, MANAGER, and LEADER fixtures and verify [route coverage](./contracts/route-coverage.md).
2. Verify `/` contains only real capability-authorized summaries and shortcuts.
3. Exercise task, attendance, notification, report/export, location/config, user, account, and job-health behavior appropriate to each role.
4. Check Light, Dark, and System modes at 320, 375, 390/430, 768, 1280, and 1440 widths.
5. Assert no horizontal document overflow, navigation overlap, inaccessible overlay, serious/critical axe issue, feature-number label, raw UUID, or fabricated chart series.

Physical-device, real screen-reader, map gesture, and browser-specific safe-area checks remain `PENDING` in `docs/DEFERRED_WORK.md` until performed.

## Completion evidence (2026-08-21)

- Unit/contract/architecture: **PASS**, 468 tests.
- Lint: **PASS** (43 pre-existing/configured warning-only magic-number findings, 0 errors).
- TypeScript: **PASS**.
- Generated API contract: **PASS**, unchanged.
- Production build: **PASS**, 14 user-facing routes plus the framework not-found route.
- Playwright Chromium: **PASS**, 32 tests across 320, 375, 390/430, 768, 1280, and 1440 widths.
- Live browser inspection: **PASS** for settled dark Home at desktop and 320 px; no document overflow and responsive navigation present.
- Source scan: **PASS**, no `FEATURE 001` through `FEATURE 015` production labels.
