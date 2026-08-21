# Feature Specification: Application UI/UX Modernization and Design System

**Feature Branch**: `feature/015-ui-modernization`

**Created**: 2026-08-21

**Status**: Draft

**Input**: Modernize every existing user-facing frontend route while preserving all canonical behavior, API contracts, RBAC, business rules, and security constraints.

## User Scenarios & Testing

### User Story 1 - Consistent authenticated workspace (Priority: P1)

An authenticated user can move through a compact, role-appropriate application shell, understand the current page, change the visual theme, and reach account actions without crowded permanent controls.

**Why this priority**: The shell, navigation, theme, typography, and state patterns determine the usability and safety of every protected workflow.

**Independent Test**: Sign in as each supported role, inspect all visible navigation destinations, switch Light/Dark/System preferences, use the account menu, and confirm unauthorized destinations are absent while permitted destinations remain reachable.

**Acceptance Scenarios**:

1. **Given** an authenticated HELPDESK, MANAGER, or LEADER, **When** the application shell renders, **Then** only capability-authorized navigation and header actions are visible.
2. **Given** a 320px-wide viewport, **When** a user navigates the application, **Then** primary actions remain usable without horizontal overflow or navigation overlap.
3. **Given** a saved theme preference, **When** the application is reopened, **Then** the selected Light, Dark, or System behavior is applied without exposing sensitive data.

---

### User Story 2 - Action-oriented Home (Priority: P1)

An authenticated user opening `/` sees a concise role-appropriate summary of what matters now and can continue to an authorized primary workflow using only existing data.

**Why this priority**: The current root screen exposes development states and provides no operational value.

**Independent Test**: Open `/` as each role and confirm the page contains only metrics, summaries, and shortcuts supported by that account's existing capabilities and data responses.

**Acceptance Scenarios**:

1. **Given** a HELPDESK user, **When** Home loads, **Then** attendance, task, notification, and shortcut content appears only where the account is authorized and real data is available.
2. **Given** a MANAGER or LEADER, **When** Home loads, **Then** available aggregate operational summaries and authorized shortcuts are presented without inventing data or granting mutation access.
3. **Given** one Home data source fails, **When** other authorized data is available, **Then** usable sections remain visible and the failed section offers a concise retry state.

---

### User Story 3 - Modern primary workflows (Priority: P1)

Users complete task, attendance, notification, and reporting workflows through responsive, scan-friendly pages that preserve every existing action and result.

**Why this priority**: These are the daily operational workflows and contain the highest regression risk.

**Independent Test**: Exercise all currently supported task transitions and evidence flows, attendance check-in/out and geofence guidance, notification read/deep-link behavior, report filters and exports, and compare results with the existing API contracts.

**Acceptance Scenarios**:

1. **Given** an authorized task user, **When** tasks are loaded, **Then** overdue, today, upcoming, and completed work is clearly grouped while details, history, and evidence remain accessible through progressive disclosure.
2. **Given** an authorized HELPDESK user, **When** attendance loads, **Then** location context, attendance state, GPS quality, the primary punch action, guidance, and today's session summary appear in that priority order.
3. **Given** notifications, **When** the inbox loads, **Then** items are grouped by recency, unread state is distinguishable without color alone, and existing mark-read and deep-link behavior remains available.
4. **Given** report aggregates, **When** Reports loads, **Then** real aggregate values are represented as KPIs or truthful categorical charts with a textual equivalent, while exports and canonical formulas remain unchanged.

---

### User Story 4 - Modern administration and account workflows (Priority: P2)

Authorized users manage configuration, locations, holidays, users, operational health, passwords, and account information through clearly grouped responsive interfaces.

**Why this priority**: These workflows are less frequent but are operationally sensitive and must retain authorization and validation behavior.

**Independent Test**: Visit every administrative route as allowed and denied roles, complete each existing action, and verify immutable fields, role restrictions, one-time password display, and backend errors are handled safely.

**Acceptance Scenarios**:

1. **Given** a MANAGER, **When** configuration, location, holiday, or user administration loads, **Then** each existing control is preserved in logical sections with associated labels, descriptions, validation, and actions.
2. **Given** a LEADER, **When** read-only reporting or job-health content loads, **Then** no mutation control or unauthorized account/audit link is exposed.
3. **Given** a denied capability, **When** a protected route is requested directly, **Then** existing route-boundary behavior remains enforced and the frontend does not become an authorization boundary.

---

### User Story 5 - Accessible and resilient presentation (Priority: P2)

Users receive one clear loading, empty, error, permission, or stale-data state at a time and can operate the application with keyboard, touch, zoom, and assistive technology.

**Why this priority**: Cross-cutting state and accessibility consistency prevents confusing failure modes and regressions across every page.

**Independent Test**: Run automated accessibility and responsive checks at representative widths, force loading/empty/error states, and verify labels, focus, contrast, keyboard order, reduced motion, and retry behavior.

**Acceptance Scenarios**:

1. **Given** a request in progress, empty result, denied permission, or request failure, **When** the page renders, **Then** only the relevant state is announced and raw backend internals are not exposed.
2. **Given** keyboard-only operation, **When** a user traverses interactive controls, **Then** focus is visible and all commands, menus, dialogs, tabs, and disclosures are operable.
3. **Given** long Vietnamese content or a small viewport, **When** the page renders, **Then** text wraps, controls remain reachable, and no incoherent overlap or horizontal page overflow occurs.

### Edge Cases

- A role has no secondary navigation entries after capability filtering.
- System theme changes while the application is open.
- Aggregate report fields are zero, null, absent, or not suitable for a chart.
- A notification deep link is stale, invalid, or no longer authorized.
- A route is opened during authentication loading, forced password change, or inactive account state.
- A table row contains long names, addresses, status labels, or validation messages at 320px width.
- Existing data is visible while a refresh fails; stale data remains clearly identified without being discarded.

## Requirements

### Functional Requirements

- **FR-001**: The application MUST use one coherent visual language across every user-facing route, with centralized semantic typography, color, spacing, radius, surface, status, and chart conventions.
- **FR-002**: The authenticated experience MUST use one reusable shell with restrained MobiFone branding, compact current-page context, responsive content bounds, notifications where authorized, theme control, and an account menu.
- **FR-003**: Navigation MUST be defined centrally, filtered by existing capabilities, limited to Home, Tasks, Attendance, and More on mobile, and presented as a scalable compact navigation model on larger screens.
- **FR-004**: Frontend capability checks MUST remain presentation-only; existing backend authorization, route boundaries, object scope, and forced-password behavior MUST remain unchanged.
- **FR-005**: `/` MUST become an authenticated, role-appropriate Home that uses only existing authorized responses and offers next actions without becoming a duplicate reporting page.
- **FR-006**: Task screens MUST preserve all create, assign, update, status, evidence, history, and completion behaviors while grouping work by operational urgency and disclosing secondary detail progressively.
- **FR-007**: Attendance MUST preserve canonical GPS, geofence, candidate-choice, check-in/out, failure, and session behavior while keeping the primary action visually dominant.
- **FR-008**: Notifications MUST preserve list, unread count, mark-read, browser push, and deep-link semantics while presenting an inbox grouped into Today, Yesterday, and Earlier with All and Unread views.
- **FR-009**: Reports MUST preserve filters, exports, access scope, and formulas; categorical charts MUST use only real response fields and MUST include an accessible textual summary.
- **FR-010**: Configuration MUST preserve all current fields and validation while grouping settings into meaningful operational sections.
- **FR-011**: Location and holiday administration MUST preserve all existing hierarchy, status, geofence, and edit semantics in responsive list/form layouts.
- **FR-012**: User administration MUST preserve search, filters, pagination, immutable username, assignable-role restrictions, protected MANAGER behavior, activation, reset-password, and one-time generated-password display.
- **FR-013**: Account and password workflows MUST separate profile, password, preferences, and session actions where existing contracts support them and MUST NOT expose JWT or session internals.
- **FR-014**: Operational job-health content MUST retain MANAGER/LEADER access-scope differences and existing state semantics while using the shared page and state patterns.
- **FR-015**: Loading, empty, error, permission, retry, and stale-data presentation MUST be standardized and MUST not expose raw backend messages, UUIDs, stack details, or developer placeholders.
- **FR-016**: All user-visible feature-number labels, debug text, demo states, raw identifiers not meaningful to users, and internal development terminology MUST be removed from production UI.
- **FR-017**: Light, Dark, and System theme preferences MUST apply consistently to navigation, forms, tables, overlays, charts, notifications, reports, guidance, and maps; the non-sensitive preference MAY be stored locally.
- **FR-018**: Interactive controls MUST have visible focus, accessible names, associated labels and errors, keyboard operation, sufficient contrast, color-independent statuses, reasonable touch targets, and reduced-motion behavior.
- **FR-019**: Layouts MUST avoid horizontal page overflow and incoherent overlap at 320px, 375px, 390-430px, tablet, desktop, and large-desktop widths.
- **FR-020**: Existing API transport, generated contracts, business state ownership, formulas, security behavior, and all currently working actions MUST remain unchanged unless an actual regression is proven.

### Route Modernization Coverage

| Route | Existing access | Existing purpose to preserve | Modernization scope |
|---|---|---|---|
| `/` | Authenticated state | Root application entry | Role-aware Home, next actions, real authorized summaries |
| `/login` | Anonymous | Sign in and account-state handling | Focused responsive authentication layout and safe errors |
| `/change-password` | Forced-change or authenticated | Change own password | Account/password section with clear validation |
| `/account` | Authenticated state | New presentation of existing self-account data and actions | Read-only profile, theme preference, password link, and logout without new backend behavior |
| `/tasks` | `task.view.self` or implication | Task creation, assignment, transitions, evidence, history | Operational groups, responsive forms, progressive detail |
| `/attendance` | `attendance.view.self` or implication | Today state, punch, candidate choice, guidance | Action-first responsive attendance workspace |
| `/notifications` | `notification.view.self` | Inbox, read state, push opt-in | Tabs, date groups, accessible unread state and actions |
| `/notifications/open/[reference]` | `notification.view.self` plus target authorization | Safe notification target resolution | Shared redirect/loading/error presentation without UUID display |
| `/reports` | `report.view.self` or implication | Attendance/task aggregates and exports | Filters, KPI hierarchy, truthful categorical charts, summaries |
| `/locations` | `location.view` | Location list, create/edit, hierarchy and status | Responsive directory, status/meta, compact actions and forms |
| `/holidays` | `holiday.manage` | Holiday configuration | Structured schedule section and responsive editor |
| `/config` | `config.view` | Operational configuration | Logical setting groups, descriptions, validation, warnings |
| `/users` | `user.view` | User search, pagination and administration | Responsive data view, action menu, preserved restrictions |
| `/operations/job-health` | `operations.job_health.view` | Reconciliation health and scoped investigation | Operational status hierarchy and shared resilient states |

### Key Entities

- **Theme Preference**: Non-sensitive local choice of Light, Dark, or System; it does not alter account or business data.
- **Navigation Item**: A destination, label, icon, grouping, and optional capability used only to determine presentation.
- **Route Coverage Record**: Route, capability, preserved purpose, modernization scope, and regression evidence.
- **Visualization Definition**: Existing response fields, deterministic transformation, visual form, and textual equivalent.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All 13 existing user-facing routes are present in the coverage inventory and regression-verified, and the delivered 14-route set including `/account` uses the shared layout/state conventions.
- **SC-002**: At 320px through large desktop widths, automated representative-page checks find no horizontal document overflow, blocked primary action, or navigation/content overlap.
- **SC-003**: Each supported role sees zero navigation destinations outside its existing capabilities, and every permitted current destination remains reachable.
- **SC-004**: Light, Dark, and System modes render all representative routes without unreadable text, missing status meaning, or illegible chart content.
- **SC-005**: Automated accessibility checks report no serious or critical violations on Home, Tasks, Attendance, Notifications, Reports, Users, and Login representative states.
- **SC-006**: All existing frontend unit and integration tests pass, frontend lint and type checks pass, and the production frontend build succeeds.
- **SC-007**: A source scan finds zero user-visible `FEATURE 001` through `FEATURE 015` labels and zero root-page demo API/error states.
- **SC-008**: Every chart can be traced to documented current response fields and has a readable non-visual summary; no synthetic historical series exists.

## Assumptions

- Existing backend endpoints, generated API schema, authenticated transport, capability set, and business behavior remain authoritative and unchanged.
- The current Next.js, Tailwind, shadcn-compatible configuration, Lucide icon system, and feature-module structure are extended incrementally rather than rewritten.
- Home degrades by capability and available response data; a missing authorized data source removes or errors only that section.
- Automated browser checks cover representative viewports; physical-device, screen-reader, and real map gesture checks are recorded as pending deferred work rather than fabricated as passed.
- Authority is `docs/CHOT_YEU_CAU.md` → resolved decisions in `docs/RA_SOAT_YEU_CAU.md` → PRD → clean-code rules → constitution → this feature.
