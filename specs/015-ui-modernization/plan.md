# Implementation Plan: Application UI/UX Modernization and Design System

**Branch**: `feature/015-ui-modernization` | **Date**: 2026-08-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/015-ui-modernization/spec.md`

## Summary

Incrementally modernize the existing Next.js frontend around its current feature/model/API boundaries. Normalize semantic tokens and typography, add Light/Dark/System theming, consolidate capability-aware navigation and account actions in the existing shell, build an authorized Home and account page, and migrate every current screen to responsive semantic components without changing generated contracts, transport, backend behavior, RBAC, or business state. Reports use only categorical aggregates exposed by current APIs; no time series is synthesized.

## Technical Context

**Language/Version**: TypeScript 5.9 strict, React 19.1, Next.js 16.3 App Router

**Primary Dependencies**: Existing Tailwind CSS 4, CVA, Radix Slot, Lucide; focused Radix/shadcn dependencies for DropdownMenu, Sheet/Dialog, Tabs, Tooltip, theme management, and Recharts-compatible charts

**Storage**: Existing backend only; browser-local non-sensitive theme selection

**Testing**: Vitest + Testing Library, architecture/contract tests, Playwright, axe-core, ESLint, TypeScript, production build

**Target Platform**: Responsive authenticated web application, Chromium automation at 320-1440px, current production browser support

**Project Type**: Existing web application with separate frontend and backend

**Performance Goals**: Preserve current request count per workflow where practical; make Home sections independent; limit charts to small aggregate datasets

**Constraints**: No backend/API/business-rule redesign; frontend permissions remain presentational; generated schema and authenticated transport remain canonical; no fabricated metrics; no raw sensitive identifiers; progressive migration must keep existing tests useful

**Scale/Scope**: 13 current user-facing routes plus new `/account`; three roles; approximately 50 users; frontend only unless verification proves an existing contract regression

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

- **Source authority**: PASS. UI decisions defer to CHOT, resolved R decisions, PRD, clean-code rules, and the constitution. No business rule is introduced.
- **Thin UI and inward dependencies**: PASS. Existing feature model/API hooks retain business state; presentation components compose them and do not own transitions or authorization.
- **Layered authorization**: PASS. Capability filtering controls visibility only; `IdentityRouteBoundary` and backend RBAC/object scope remain unchanged.
- **Stable generated contracts**: PASS. The generated schema, `apiClient`, and `authenticatedFetch` are reused and not duplicated or hand-edited.
- **Location/GPS integrity**: PASS. Attendance and guidance hooks remain authoritative; layout changes do not reinterpret GPS/geofence semantics.
- **Testing and maintainability**: PASS. Each migration has targeted regression checks followed by architecture, E2E, lint, typecheck, and build gates.
- **Dependency justification**: PASS. Focused primitives, theme support, and chart rendering fill explicit gaps; no general UI framework rewrite is introduced.

Post-design re-check: PASS. UI contracts introduce no new server data or authority, the route matrix preserves capabilities, and chart transformations are deterministic views of current responses.

## Project Structure

### Documentation (this feature)

```text
specs/015-ui-modernization/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── route-coverage.md
│   └── visualizations.md
└── tasks.md
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── app/                    # route composition and providers
│   ├── features/               # existing feature API/model/UI ownership
│   │   ├── home/               # capability-gated Home composition
│   │   ├── reports/            # deterministic chart transforms and panels
│   │   └── ...                 # presentation migration in existing modules
│   └── shared/
│       ├── lib/                # shared presentation formatters only
│       └── ui/
│           ├── primitives/     # focused shadcn/Radix primitives
│           ├── shell/          # shell, header, menus, navigation registry
│           ├── theme/          # provider, toggle, semantic variables
│           └── ...             # semantic page/state/layout components
└── tests/
    ├── unit/
    ├── architecture/
    ├── contract/
    └── e2e/

docs/
└── DEFERRED_WORK.md
```

**Structure Decision**: Preserve the existing App Router and feature-first frontend. Shared UI owns generic primitives and cross-cutting semantic application concepts; feature folders retain transforms, state, and domain-specific presentation. Backend and generated contracts remain untouched.

## Migration Phases

1. Audit routes, dependencies, current visual debt, tokens, and test coverage.
2. Normalize semantic variables, typography, theme provider, focused primitives, and shared page/state components with compatibility aliases.
3. Consolidate shell, header, account dropdown, capability registry, desktop navigation, and four-destination mobile navigation.
4. Build capability-gated Home and read-only Account using existing data modules.
5. Migrate Tasks, Attendance/Guidance, Notifications, and Reports while preserving feature hooks and behavior.
6. Migrate Configuration, Locations, Holidays, Users, Job Health, Login, Change Password, and notification target states.
7. Remove development labels, complete accessibility/responsive audits, record manual-only work, and run broad verification.

## Visualization Contracts

| Endpoint/query | Response field | Transformation | Visualization |
|---|---|---|---|
| Task report with existing date/user filters | `status_counts` | Canonical status order, missing keys to zero | Categorical bar/donut plus textual list |
| Same | `completion_method_counts` | Non-empty method/value entries | Categorical bar plus textual list |
| Same | `gps_quality_counts` | Non-empty quality/value entries | Categorical bar plus textual list |
| Attendance report with existing date/user filters | `attempt_counts` | Non-empty outcome/value entries | Categorical bar plus textual list |
| Same | `anomaly_counts` | Non-empty anomaly/value entries | Categorical bar plus textual list |
| Same | `failure_rate` and attendance totals | Direct values preserving numerator/denominator/excluded meaning | KPI/progress and text, not a population partition |

`actual_completer_counts` is not charted because keys are user IDs without display names. No trend visualization is permitted because the current contract has no time buckets.
