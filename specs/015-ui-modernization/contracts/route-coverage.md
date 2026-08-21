# Route Migration and Regression Contract

| Route | Capability/state | Existing purpose and major components | New layout/components | Regression verification |
|---|---|---|---|---|
| `/` | Authenticated | Development AsyncState demo | `HomeDashboard`, PageHeader, capability sections | Role fixtures; no demo states; authorized requests only |
| `/login` | Anonymous | `LoginForm`, identity boundary | Focused auth shell and semantic errors | Login/account-state unit + E2E |
| `/change-password` | Forced/authenticated | `ChangePasswordForm` | Account password section | Forced-change redirect and form tests |
| `/account` | Authenticated | New view of existing account state | Profile, preference, password/session actions | No JWT fields; menu/route tests |
| `/tasks` | `task.view.self` implication | Task panel, forms, groups, evidence/history | PageHeader, responsive form, TaskSection/Card/History disclosure | Existing task unit/E2E plus viewport checks |
| `/attendance` | `attendance.view.self` implication | Attendance panel, punch, choices, guidance | Bounded action-first grid and timeline | Existing attendance/guidance plus accessibility |
| `/notifications` | `notification.view.self` | Inbox, push opt-in, mark read | Tabs, date groups, inbox rows, resilient states | Existing notification tests plus grouping/read E2E |
| `/notifications/open/[reference]` | Notification plus target scope | Target resolution and redirect | Shared loading/error page state | Existing invalid/stale/authorized tests |
| `/reports` | `report.view.self` implication | Reports panel, filters, exports | KPIs, categorical charts, summaries, authenticated export | Transform/unit tests; capability/export regression |
| `/locations` | `location.view` | Filters, list, optimistic editor/warnings | Responsive directory, status/meta, compact actions | Existing tests; conflict draft retention |
| `/holidays` | `holiday.manage` | Holiday manager | Structured schedule editor | Existing tests and denied-route check |
| `/config` | `config.view` | Config editor | Attendance/GPS/schedule/task sections | Existing tests; mutation hidden for read-only |
| `/users` | `user.view` | Filters, pagination, create/edit/status/role/reset | Responsive data view and row action menu | Existing identity tests; MANAGER protections |
| `/operations/job-health` | `operations.job_health.view` | Polling/stale-good health | Status hierarchy, metrics, scoped actions | Existing state/API/panel tests |

## Role navigation expectations

- HELPDESK: Home, Tasks, Attendance, Notifications, self Reports when capability is present, Account.
- MANAGER: Home, Tasks, Reports, Users, Locations, Holidays, Configuration, Job Health, Notifications, Account; no attendance punch action.
- LEADER: Home, read-only Tasks/Reports, Locations/Configuration where current capabilities allow, Job Health, Notifications, Account; no user directory or mutation entries.

The registry filters by returned capabilities; these summaries are regression expectations, not a second authorization matrix.
