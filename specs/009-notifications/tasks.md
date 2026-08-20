# Tasks: In-App Notifications and Web Push

**Input**: Design documents from `/specs/009-notifications/`

**Prerequisites**: plan.md, spec.md, existing implementation under `specs/008-in-app-web-push/`

**Tests**: Automated notification backend/frontend/contract tests are required. Real provider/browser evidence is deferred.

## Phase 1: Specification and Authority Trace

- [X] T001 Create Feature 009 notification specification in `specs/009-notifications/spec.md`
- [X] T002 Resolve clarifications from CHOT/R-97 and document no additional notification event types in `specs/009-notifications/spec.md`
- [X] T003 Create implementation plan referencing the existing completed Feature 008 notification code path in `specs/009-notifications/plan.md`
- [X] T004 Create task trace and implementation status in `specs/009-notifications/tasks.md`

## Phase 2: Implementation Verification

- [X] T005 Verify Notification, PushSubscription, PushDelivery models and API contract exist in `backend/notifications/` and `contracts/openapi.yaml`
- [X] T006 Verify frontend notification inbox, read, opt-in, and safe-open routes exist in `frontend/src/features/notifications/` and `frontend/src/app/notifications/`
- [X] T007 Verify Feature 008 tasks are complete through convergence T103 in `specs/008-in-app-web-push/tasks.md`
- [X] T008 Run backend notification tests in `backend/tests/unit/notifications` and `backend/tests/integration/api/notifications`
- [X] T009 Run frontend notification tests in `frontend/tests/unit/notifications`
- [X] T010 Run notification-related contract/schema checks after verification

## Phase 3: Deferred Evidence

- [X] T011 Add real browser/device Web Push permission and delivery verification to `docs/DEFERRED_WORK.md`

## Dependencies and Execution Order

T001-T004 complete the Spec Kit trace. T005-T007 verify implementation presence. T008-T010 are automated gates. T011 records non-automatable evidence.
