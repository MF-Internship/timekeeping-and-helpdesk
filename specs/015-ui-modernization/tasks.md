# Tasks: Application UI/UX Modernization and Design System

**Input**: Design documents from `specs/015-ui-modernization/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`

**Format**: `[ID] [P?] [Story] Verifiable action with exact file path`

## Phase 1: Setup and Audit

### A. Route/UI inventory

- [x] T001 Record every current route, capability, purpose, major component, target layout, and regression test in `specs/015-ui-modernization/contracts/route-coverage.md`
- [x] T002 [P] Audit user-visible development labels, raw identifiers, arbitrary colors, nested cards, and duplicate shell/state markup in `frontend/src` and record actionable locations in `specs/015-ui-modernization/research.md`
- [x] T003 [P] Audit current responsive and accessibility coverage in `frontend/tests/e2e` and map missing viewports/routes to `specs/015-ui-modernization/quickstart.md`

### B. shadcn/design-system normalization

- [x] T004 Add only approved theme, overlay, menu, tab, tooltip, and chart dependencies to `frontend/package.json` and `frontend/package-lock.json`
- [x] T005 [P] Reuse focused shadcn-compatible primitives under `frontend/src/shared/ui/` and integrate only the required Radix foundations without changing existing business component APIs
- [x] T006 [P] Extend design-system architecture tests for semantic tokens and primitive ownership in `frontend/tests/architecture/design-tokens.test.ts` and `frontend/tests/architecture/ui-reuse-boundary.test.ts`

---

## Phase 2: Foundational Design System

### C. Typography

- [x] T007 Replace ad hoc heading/text combinations with centralized semantic variants and PageHeader/SectionHeader adapters in `frontend/src/shared/ui/typography/`
- [x] T008 [P] Add typography hierarchy regression tests in `frontend/tests/unit/ui/design-system.test.tsx` and `frontend/tests/unit/shell/page-header.test.tsx`

### D. Light/dark theme

- [x] T009 Normalize light/dark semantic CSS variables, chart colors, compatibility aliases, radius, and spacing conventions in `frontend/src/shared/ui/theme/tokens.css` and `frontend/src/app/globals.css`
- [x] T010 Add Light/Dark/System provider and hydration-safe toggle in `frontend/src/shared/ui/theme/ThemeProvider.tsx`, `frontend/src/shared/ui/theme/ThemeToggle.tsx`, and `frontend/src/app/layout.tsx`
- [x] T011 [P] Add theme resolution/toggle tests in `frontend/tests/unit/ui/theme.test.tsx` and dark-token architecture assertions in `frontend/tests/architecture/design-tokens.test.ts`

### Q. Shared loading/empty/error states

- [x] T012 Replace raw detail/request-id dumps with semantic LoadingState, SkeletonState, EmptyState, ErrorState, PermissionState, and stale-data presentation in `frontend/src/shared/ui/async-state/`
- [x] T013 [P] Cover mutually exclusive states, retry, safe support information, and accessible announcements in `frontend/tests/unit/ui/async-state.test.tsx`

**Checkpoint**: Tokens, typography, theme, primitives, and resilient states are stable before route migration.

---

## Phase 3: User Story 1 - Consistent Authenticated Workspace (Priority: P1)

**Goal**: Deliver one responsive, capability-aware shell with compact account and theme controls.

**Independent Test**: Render the shell for each role/capability set at mobile and desktop widths, verify permitted destinations, account actions, theme choices, focus, and no overflow.

### E. AppShell

- [x] T014 [US1] Add PageContainer and responsive shell layout primitives in `frontend/src/shared/ui/shell/AppShell.tsx` and `frontend/src/shared/ui/shell/AppShell.module.css`
- [x] T015 [P] [US1] Update application metadata and focused unauthenticated frame in `frontend/src/app/layout.tsx`, `frontend/src/shared/ui/shell/ApplicationFrame.tsx`, and `frontend/src/app/globals.css`

### F. Header/account dropdown

- [x] T016 [US1] Replace expanded account metadata and Unicode back control with compact Lucide header actions in `frontend/src/shared/ui/shell/AppHeader.tsx` and `frontend/src/shared/ui/shell/AppHeader.module.css`
- [x] T017 [US1] Implement capability-safe AccountMenu with profile, password, appearance, and logout actions in `frontend/src/shared/ui/shell/AccountMenu.tsx`

### G. Responsive navigation

- [x] T018 [US1] Replace `employee-navigation.ts` with one typed icon/capability/active-match registry in `frontend/src/shared/ui/shell/navigation.ts`
- [x] T019 [US1] Implement desktop compact sidebar and Home/Tasks/Attendance/More mobile navigation in `frontend/src/shared/ui/shell/PrimaryNavigation.tsx`, `NavigationRail.tsx`, and `BottomNavigation.tsx`
- [x] T020 [US1] Implement the authorized More Sheet and safe-area behavior in `frontend/src/shared/ui/shell/MobileMoreMenu.tsx` and `frontend/src/shared/ui/shell/PrimaryNavigation.module.css`
- [x] T021 [P] [US1] Update shell/header/navigation unit tests for HELPDESK, MANAGER, LEADER, active routes, account actions, and mobile grouping in `frontend/tests/unit/shell/`

**Checkpoint**: US1 shell is independently usable with current route content.

---

## Phase 4: User Story 2 - Action-Oriented Home (Priority: P1)

**Goal**: Replace root development states with truthful role-appropriate current work.

**Independent Test**: Render `/` with each role fixture and independent API failures; verify only authorized real summaries and shortcuts appear.

### H. Home `/`

- [x] T022 [US2] Add capability-gated independent Home section state in `frontend/src/features/home/model/use-home-dashboard.ts` using existing feature API modules only
- [x] T023 [US2] Compose HELPDESK attendance/task/notification summaries and authorized quick actions in `frontend/src/features/home/ui/HomeDashboard.tsx`
- [x] T024 [US2] Compose MANAGER/LEADER report/job-health summaries and read/write-appropriate shortcuts in `frontend/src/features/home/ui/HomeDashboard.tsx`
- [x] T025 [US2] Replace demo AsyncState root content and protect authenticated Home in `frontend/src/app/page.tsx` and `frontend/src/features/identity/model/IdentityRouteBoundary.tsx`
- [x] T026 [P] [US2] Add role, truthfulness, and partial-failure Home tests in `frontend/tests/unit/home/home-dashboard.test.tsx`

**Checkpoint**: US2 answers what matters now without a new backend contract.

---

## Phase 5: User Story 3 - Modern Primary Workflows (Priority: P1)

**Goal**: Modernize Tasks, Attendance, Notifications, and Reports while retaining feature behavior.

**Independent Test**: Run existing feature suites and new responsive/presentation tests for each primary workflow.

### I. Tasks modernization

- [x] T027 [US3] Remove the Feature 007 label and compose responsive PageHeader/create/action groups in `frontend/src/features/tasks/ui/TaskManagementPanel.tsx` and `TaskManagement.module.css`
- [x] T028 [US3] Refine TaskCard, TaskGroup/TaskSection, status/meta, evidence summary, and history progressive disclosure in `frontend/src/features/tasks/ui/`
- [x] T029 [P] [US3] Extend task regression tests for groups, preserved actions, detail/history disclosure, long content, and viewport layout in `frontend/tests/unit/tasks/` and `frontend/tests/e2e/tasks.spec.ts`

### J. Attendance modernization

- [x] T030 [US3] Recompose attendance hierarchy and bounded desktop grid without altering hooks in `frontend/src/features/attendance/ui/AttendancePanel.tsx` and `AttendancePanel.module.css`
- [x] T031 [US3] Modernize GPS/guidance status, location summary, map/diagram, session timeline, and primary action presentation in `frontend/src/features/attendance/ui/` and `frontend/src/features/guidance/ui/`
- [x] T032 [P] [US3] Extend attendance/guidance regression, accessibility, 320px, tablet, and desktop checks in `frontend/tests/unit/attendance/`, `frontend/tests/unit/guidance/`, and `frontend/tests/e2e/attendance-*.spec.ts`

### K. Notifications modernization

- [x] T033 [US3] Add deterministic All/Unread filtering and Today/Yesterday/Earlier grouping in `frontend/src/features/notifications/model/notification-groups.ts`
- [x] T034 [US3] Remove Feature 008/debug presentation and build inbox tabs, grouped rows, category icons, unread state, push control, skeleton/empty/error states in `frontend/src/features/notifications/ui/NotificationInbox.tsx` and `Notifications.module.css`
- [x] T035 [P] [US3] Cover grouping boundaries, unread interaction, stale links, push behavior, loading/empty/error, and accessibility in `frontend/tests/unit/notifications/` and `frontend/tests/e2e/notifications.spec.ts`

### L. Reporting and charts

- [x] T036 [US3] Implement pure truthful chart transforms with canonical labels and zero/unknown handling in `frontend/src/features/reports/model/report-charts.ts`
- [x] T037 [US3] Replace report text dump with filters, KPIs, task/attendance categorical charts, accessible summaries, and empty states in `frontend/src/features/reports/ui/ReportsPanel.tsx` and supporting feature components
- [x] T038 [US3] Route report exports through authenticated transport with Blob download while preserving filters/capabilities in `frontend/src/features/reports/api/report-api.ts` and report UI
- [x] T039 [P] [US3] Add transform truthfulness, no-time-series, KPI/chart, dark-mode, export-auth, and role tests in `frontend/tests/unit/reports/`

**Checkpoint**: US3 preserves all daily workflow behavior and renders only truthful visualizations.

---

## Phase 6: User Story 4 - Administration and Account (Priority: P2)

**Goal**: Modernize lower-frequency sensitive routes with clear grouping and responsive data actions.

**Independent Test**: Exercise permitted and denied administrative actions and account behavior with existing contract fixtures.

### M. Configuration

- [x] T040 [US4] Group existing schedule, attendance, GPS/location, and task settings with descriptions/warnings in `frontend/src/features/locations/ui/ConfigEditor.tsx` and its styles
- [x] T041 [P] [US4] Preserve validation, warnings, read-only LEADER controls, and MANAGER mutations in `frontend/src/features/locations/ui/ConfigEditor.test.tsx`

### N. Locations and holidays

- [x] T042 [US4] Build responsive location directory rows/table, badges, metadata, filters, action menu, and bounded editor in `frontend/src/features/locations/ui/LocationDirectory.tsx`
- [x] T043 [US4] Modernize holiday list/editor into the shared page/form patterns in `frontend/src/features/locations/ui/HolidayManager.tsx`
- [x] T044 [P] [US4] Preserve optimistic version conflicts, warnings, hierarchy/filter semantics, and holiday actions in existing `frontend/src/features/locations/ui/*.test.tsx`

### O. User management

- [x] T045 [US4] Recompose user filters, responsive data rows/table, pagination, and DropdownMenu actions in `frontend/src/features/identity/ui/UserDirectory.tsx`
- [x] T046 [US4] Modernize user editor and one-time password dialog while preserving immutable username, roles, status, and protected MANAGER rules in `frontend/src/features/identity/ui/UserEditor.tsx` and `GeneratedPasswordDialog.tsx`
- [x] T047 [P] [US4] Extend user directory tests for responsive actions, role/status restrictions, password display, filters, and pagination in `frontend/tests/unit/identity/`

### P. Account

- [x] T048 [US4] Create authenticated read-only profile/preferences/session composition in `frontend/src/features/identity/ui/AccountPanel.tsx` and `frontend/src/app/account/page.tsx`
- [x] T049 [US4] Modernize `/change-password` labels/errors/layout while retaining forced-change behavior in `frontend/src/features/identity/ui/ChangePasswordForm.tsx` and `frontend/src/app/change-password/page.tsx`
- [x] T050 [P] [US4] Add account privacy, menu, logout, theme, and forced-password tests in `frontend/tests/unit/identity/account-panel.test.tsx` and existing auth tests

### Remaining routes

- [x] T051 [P] [US4] Modernize job-health status hierarchy without changing polling/stale/access scope in `frontend/src/features/operations/ui/JobHealthPanel.tsx`
- [x] T052 [P] [US4] Apply shared page/state layout to Login and notification-open routes in `frontend/src/app/login/page.tsx` and `frontend/src/app/notifications/open/[reference]/page.tsx`

**Checkpoint**: All 14 delivered routes use consistent shell, page, form, state, and responsive patterns.

---

## Phase 7: User Story 5 - Accessible and Resilient Presentation (Priority: P2)

**Goal**: Complete cross-route production cleanup and automated responsive/accessibility evidence.

**Independent Test**: Run source scans and representative role/theme/viewport/accessibility E2E coverage.

### R. Removal of FEATURE/debug UI

- [x] T053 [US5] Remove every user-visible Feature 001-015 label, development placeholder, raw UUID/internal message, and production Unicode navigation symbol from `frontend/src`
- [x] T054 [P] [US5] Add source-level regression assertions for forbidden production labels and alternate API transport in `frontend/tests/architecture/`

### S. Accessibility

- [x] T055 [US5] Audit and fix labels, error associations, accessible icon names, focus order, keyboard overlays, color-independent status, contrast, touch targets, chart summaries, and reduced motion across `frontend/src`
- [x] T056 [P] [US5] Add axe and keyboard assertions for Home, Tasks, Attendance, Notifications, Reports, Users, Account, and Login in `frontend/tests/e2e/accessibility.spec.ts`

### T. Responsive verification

- [x] T057 [US5] Add Playwright viewport matrix and assertions for no overflow, navigation/content separation, long text, overlay fit, charts, and safe areas in `frontend/tests/e2e/responsive-shell.spec.ts` and `frontend/tests/e2e/accessibility.spec.ts`
- [x] T058 [P] [US5] Record physical-device, screen-reader, map gesture, long-production-content, and browser safe-area checks as PENDING in `docs/DEFERRED_WORK.md`

### U. Regression tests and completion

- [x] T059 [US5] Run targeted unit suites after each migration and fix failures without changing canonical behavior
- [x] T060 [US5] Run full frontend unit/contract/architecture tests, lint, typecheck, API contract check, production build, and E2E suite from `frontend/`
- [x] T061 [US5] Verify route/capability coverage for HELPDESK, MANAGER, and LEADER against `specs/015-ui-modernization/contracts/route-coverage.md`
- [x] T062 [US5] Mark completed tasks in `specs/015-ui-modernization/tasks.md` and record final automated evidence in `specs/015-ui-modernization/quickstart.md`

## Dependencies and Execution Order

- Phase 1 precedes Phase 2; design-system foundations block route migration.
- US1 shell precedes Home and all route-wide responsive verification.
- US2 Home can proceed after US1 and shared states.
- US3 and US4 can proceed after US1; tasks touching shared primitives remain sequential.
- US5 begins after route migration and gates completion.

## Parallel Opportunities

- Audit tasks T002-T003, primitive/test tasks T005-T006, and foundation tests marked `[P]` use separate files.
- After US1, feature migrations in Tasks, Attendance, Notifications, Reports, and administration can proceed independently where they do not share files.
- Unit test additions marked `[P]` can be prepared alongside their corresponding implementation, but verification must observe the implementation dependency.

## Implementation Strategy

1. Establish compatibility-preserving foundations and shell.
2. Deliver Home as the first complete operational increment.
3. Migrate primary workflows one feature at a time with targeted tests.
4. Migrate administration/account routes with authorization regression checks.
5. Complete cross-route accessibility, responsive, source-scan, and broad quality gates before Git integration.

