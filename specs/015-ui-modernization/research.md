# Research: Application UI/UX Modernization

## Incremental architecture

**Decision**: Keep `AuthProvider`, `IdentityRouteBoundary`, `authenticatedFetch`, generated API schema, feature API/model hooks, and the current App Router. Replace presentation and composition incrementally.

**Rationale**: Existing feature modules already separate transport/state from UI. Preserving those boundaries minimizes business and authorization regressions.

**Alternatives considered**: A frontend rewrite was rejected because it adds no business value and expands regression risk.

## Component foundation

**Decision**: Treat the current `components.json`, Tailwind v4, CVA, Slot, and Lucide setup as shadcn-compatible. Add only primitives needed for dropdown, sheet/dialog, tabs, tooltip, chart, and theme behavior; retain compatible existing primitive APIs.

**Rationale**: Bulk regeneration would create unnecessary churn across covered feature tests.

**Alternatives considered**: Rebuild every primitive from a current template; rejected as unrelated migration noise.

## Tokens, typography, and theme

**Decision**: Add shadcn semantic variables and Tailwind mappings with compatibility aliases for current `--color-*` consumers. Dark values live under `.dark`. Use one class-based theme provider with Light/Dark/System and a hydration-safe toggle. Central typography exposes semantic variants; `PageIntro` remains an adapter during migration.

**Rationale**: Compatibility aliases allow staged page migration while removing feature-level hardcoded colors.

**Alternatives considered**: Per-page utilities and a bespoke theme store were rejected for inconsistency and maintenance cost.

## Navigation and account controls

**Decision**: Use one typed capability-aware registry with Lucide icons and active-match rules. Mobile shows Home, Tasks, Attendance, More; More opens authorized secondary routes. Desktop uses a compact sidebar. Header shows brand/context, notifications, theme control, and avatar dropdown. `/account` presents existing self data and actions; `/change-password` remains forced-change safe.

**Rationale**: The current horizontally scrolling nine-item mobile bar and expanded account metadata are crowded.

**Alternatives considered**: Keep all destinations in mobile bottom navigation or duplicate definitions per role; rejected for usability and drift.

## Home data

**Decision**: Load capability-gated sections independently from existing attendance-today, grouped tasks, notifications, reports, and job-health APIs. HELPDESK receives self operational summaries; MANAGER/LEADER receive allowed aggregates and shortcuts. No new endpoint is added.

**Rationale**: Partial failure should not blank the entire Home and no combined dashboard contract exists.

**Alternatives considered**: A new backend dashboard endpoint and synthetic client metrics were rejected as scope and truth violations.

## Reports

**Decision**: Use task status/method/GPS and attendance attempt/anomaly maps as categorical charts. Use failure rate and top-level totals as KPIs. Do not chart user-ID-keyed completer counts or fabricate time series.

**Rationale**: These are the only truthful, named categorical aggregates in current responses.

**Alternatives considered**: Trend lines from aggregate totals and employee charts keyed by raw IDs were rejected as fabricated or privacy-hostile.

## Responsive and accessibility verification

**Decision**: Add targeted unit tests for navigation, theme, account menu, notification grouping, chart transforms, and semantic states. Extend Playwright checks across 320, 375, 390/430, 768, 1280, and 1440 widths with overflow, keyboard, theme, and axe assertions. Record real-device and screen-reader work as pending.

**Rationale**: Existing E2E coverage focuses mainly on 360/1280 and cannot prove physical-device or assistive-technology behavior.

**Alternatives considered**: Claim manual validation from automation; rejected because the completion gate requires truthful evidence.
