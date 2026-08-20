# Tasks: Reporting, Dashboard and Export

**Input**: Design documents from `/specs/010-reporting/`

**Prerequisites**: plan.md, spec.md, generated OpenAPI tooling

## Phase 1: Specification and Plan

- [X] T001 Create Feature 010 spec in `specs/010-reporting/spec.md`
- [X] T002 Resolve clarify decisions for failure rate, export privacy, and scope in `specs/010-reporting/spec.md`
- [X] T003 Create implementation plan in `specs/010-reporting/plan.md`
- [X] T004 Create dependency-ordered tasks in `specs/010-reporting/tasks.md`

## Phase 2: Backend Reporting

- [X] T005 Add reporting DTOs, ports, query service, and container in `backend/reporting/application` and `backend/reporting/ports`
- [X] T006 Add config-owned repository and authorization adapters in `backend/config/reporting_adapters.py`
- [X] T007 Add thin reporting API permissions, serializers, views, and URLs in `backend/reporting/adapters/api`
- [X] T008 Wire reporting URLs/container in `backend/config/urls.py` and `backend/config/composition.py`
- [X] T009 Add report export audit action in `backend/audit/domain/records.py`
- [X] T010 Add backend reporting API tests in `backend/tests/integration/api/reporting/test_reporting_api.py`
- [X] T011 Update architecture guard to recognize `reporting` as a business module without registering it as a Django app

## Phase 3: Frontend Reporting

- [X] T012 Regenerate `contracts/openapi.yaml` and `frontend/src/shared/api/schema.ts`
- [X] T013 Add report API wrapper and report state hook in `frontend/src/features/reports`
- [X] T014 Add report panel and `/reports` route in `frontend/src/features/reports/ui/ReportsPanel.tsx` and `frontend/src/app/reports/page.tsx`
- [X] T015 Add capability-gated navigation and route boundary for reports
- [X] T016 Add frontend report API and panel tests in `frontend/tests/unit/reports`

## Phase 4: Verification

- [X] T017 Run backend reporting API tests
- [X] T018 Run attendance formula regression tests
- [X] T019 Run architecture/module boundary checks
- [X] T020 Run frontend report tests
- [X] T021 Run OpenAPI and frontend generated API checks
- [X] T022 Run backend lint/type checks
- [X] T023 Run frontend lint/type checks

## Dependencies and Execution Order

T005-T011 must complete before contract generation. T012 must complete before frontend API wrapper tests. T017-T023 are final feature gates.
