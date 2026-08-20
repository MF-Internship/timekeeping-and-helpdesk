# Spec Kit Full Application Workflow

## 0. Nguyên tắc vận hành

Không phát triển toàn bộ hệ thống bằng một mega-spec.

Mỗi feature phải đi qua đầy đủ:

```text
/speckit.specify
        ↓
/speckit.clarify
        ↓
/speckit.plan
        ↓
/speckit.tasks
        ↓
/speckit.analyze
        ↓
Fix CRITICAL/HIGH nếu cần
        ↓
/speckit.implement
        ↓
Verification
        ↓
Commit / PR
        ↓
Next feature
```

Toàn bộ ứng dụng có một dependency roadmap:

```text
00 Constitution
       │
       ▼
01 Project Foundation + API Contract
       │
       ▼
02 Identity + Authentication + RBAC
       │
       ▼
03 Location + Config + Seed
       │
       ├──────────────────────┐
       ▼                      ▼
04 Attendance Core       06 Task Core
       │                      │
       ▼                      ▼
05 Attendance Jobs       07 Task Evidence
       │                      │
       └──────────┬───────────┘
                  ▼
           08 Notifications
                  │
                  ▼
           09 Reporting
                  │
                  ▼
           10 Audit + Outbox
                  │
                  ▼
           11 Outbox Relay
                  │
                  ▼
           12 Observability
                  │
                  ▼
           13 Production Readiness
                  │
                  ▼
           Full-System Audit
```

---

# 00 — Project Constitution

Chỉ chạy một lần khi bắt đầu project.

## Command

```text
/speckit.constitution
```

## Message

```text
Create the Project Constitution for the Helpdesk Attendance and
Task Management application.

Read completely:

- CHOT_YEU_CAU.md
- QUY_TAC_CLEAN_CODE.md
- RA_SOAT_YEU_CAU.md
- phan_mem_web_cham_cong_va_quan_ly_cong_viec_helpdesk.md
- dia_chi_ttkd.csv
- dia_chi_cua_hang.csv

Governance:

1. CHOT_YEU_CAU.md is the authoritative source of current
   business rules, schema expectations, APIs and RBAC.
2. QUY_TAC_CLEAN_CODE.md defines mandatory implementation,
   architecture, validation and testing rules.
3. The PRD describes user-facing requirements and UX.
4. RA_SOAT_YEU_CAU.md is the decision log, rationale and
   pre-code checklist.
5. Feature specifications are derived implementation scopes,
   not independent business sources of truth.

Create project-wide principles covering:

- mandatory technology stack;
- source-of-truth governance;
- canonical vocabulary;
- modular architecture;
- dependency direction;
- domain/application/ports/adapters;
- thin API/controller layers;
- authorization-before-validation;
- canonical RBAC;
- object-scope authorization;
- server-owned versus client-owned data;
- database constraints;
- transaction boundaries;
- concurrency safety;
- auditability;
- transactional outbox;
- API contract discipline;
- schema compatibility;
- migration safety;
- security/secrets;
- observability;
- testing strategy;
- PostgreSQL integration tests;
- CI gates;
- Definition of Done.

Do not copy feature-specific business rules into the Constitution.

If documents conflict, CHOT_YEU_CAU.md wins and the conflict
must be reported.

Do not implement code.
```

## Gate

Không bắt đầu Feature 001 cho tới khi Constitution có ít nhất:

```text
Source of Truth
Architecture
Authorization
Domain Integrity
Database Integrity
Transactions
Security
API Contract
Testing
Migration Safety
Observability
Definition of Done
```

---

# Template workflow dùng cho mọi feature

Các Feature 001–013 đều dùng cùng lifecycle.

---

## Bước A — Specify

```text
/speckit.specify
```

Mục tiêu:

```text
WHAT
WHY
Actors
User scenarios
Business rules
Edge cases
Acceptance criteria
Out of scope
```

Không viết implementation details nếu chưa cần.

---

## Bước B — Clarify

```text
/speckit.clarify
```

Dùng message chuẩn:

```text
Clarify the current feature.

Read:

- Project Constitution;
- current spec.md;
- CHOT_YEU_CAU.md;
- QUY_TAC_CLEAN_CODE.md;
- RA_SOAT_YEU_CAU.md;
- PRD;
- relevant source data.

Do not ask questions already resolved by CHOT_YEU_CAU.md or
an existing R-xx decision.

Look for:

- ambiguous behavior;
- missing acceptance criteria;
- conflicting requirements;
- authorization ambiguity;
- object-scope ambiguity;
- state-transition ambiguity;
- transaction ambiguity;
- concurrency ambiguity;
- idempotency ambiguity;
- retry/failure ambiguity;
- client/server ownership ambiguity;
- audit ambiguity;
- security ambiguity;
- migration/data ambiguity.

If a genuinely new business decision is required:

do not decide silently.

Report it as a governance issue requiring:

RA_SOAT
→ CHOT
→ PRD / QUY_TAC
→ current spec.

Update spec.md after clarification.
```

---

## Bước C — Plan

```text
/speckit.plan
```

Message chuẩn:

```text
Create the implementation plan for the current feature.

Use:

- Project Constitution;
- current spec.md;
- CHOT_YEU_CAU.md;
- QUY_TAC_CLEAN_CODE.md;
- relevant R-xx decisions;
- existing repository structure.

Inspect the existing codebase before proposing new architecture.

Plan where relevant:

- modules;
- domain layer;
- application services;
- ports;
- adapters;
- models;
- migrations;
- database constraints;
- indexes;
- transactions;
- concurrency handling;
- APIs;
- serializers/DTOs;
- authorization;
- object scope;
- audit;
- outbox events;
- frontend state;
- frontend API integration;
- error semantics;
- unit tests;
- PostgreSQL integration tests;
- contract tests;
- CI verification;
- migration compatibility.

Reuse existing approved patterns.

Do not implement code.

Do not introduce new dependencies or infrastructure unless an
approved requirement needs them.
```

---

## Bước D — Tasks

```text
/speckit.tasks
```

Message:

```text
Generate concrete implementation tasks from spec.md and plan.md.

Requirements:

- dependency ordered;
- one verifiable outcome per task;
- reference concrete modules/files;
- tests placed alongside behavior;
- include success paths;
- include deny paths;
- include edge cases;
- include DB constraints;
- include PostgreSQL concurrency tests where required;
- include authorization/object-scope tests;
- include API contract changes;
- include migration checks;
- include lint/type/static verification.

Mark [P] only for genuinely independent tasks.

Do not create vague tasks such as:

- Implement backend
- Implement frontend
- Add validation
- Add tests

Do not implement.
```

---

## Bước E — Analyze

```text
/speckit.analyze
```

Message:

```text
Perform a strict consistency audit.

Compare:

- Project Constitution;
- spec.md;
- plan.md;
- tasks.md;
- CHOT_YEU_CAU.md;
- QUY_TAC_CLEAN_CODE.md;
- relevant R-xx decisions;
- PRD where applicable.

Detect:

- missing authoritative requirements;
- invented requirements;
- contradictions;
- Constitution violations;
- missing permission checks;
- missing object-scope checks;
- incorrect permission/validation ordering;
- server-owned field exposure;
- missing DB constraints;
- missing transactions;
- concurrency races;
- incomplete audit coverage;
- incomplete outbox coverage;
- missing failure cases;
- missing idempotency;
- inconsistent terminology;
- insufficient tests.

Classify:

CRITICAL
HIGH
MEDIUM
LOW

Do not implement.

No implementation may start while CRITICAL findings remain.
```

---

## Bước F — Implement

```text
/speckit.implement
```

Message:

```text
Implement the approved tasks for the current feature.

Rules:

- follow tasks.md dependency order;
- obey the Project Constitution;
- CHOT_YEU_CAU.md remains authoritative;
- obey QUY_TAC_CLEAN_CODE.md;
- respect relevant R-xx decisions;
- never weaken authorization, DB constraints, validation or tests;
- never silently change business behavior;
- do not implement behavior outside the approved spec.

After each logical task group:

- run relevant unit tests;
- run PostgreSQL integration tests where applicable;
- run lint;
- run type checks;
- run contract checks where applicable.

Before declaring completion run the complete feature verification.

If code exposes a genuine requirements conflict, stop the affected
task and report it instead of inventing a decision.
```

---

# 001 — Project Foundation + API Contract

## Branch / feature

```text
001-project-foundation
```

## Dependency

```text
Constitution
```

## Chức năng

### Backend

- Django REST Framework skeleton.
- PostgreSQL.
- module architecture.
- composition root.
- shared/core.
- exception/error handling.
- request ID.
- correlation context.
- API version prefix.

### Frontend

- Next.js.
- App Router.
- shared layer.
- API transport.
- `authenticatedFetch`.
- error handling.

### Contract

- OpenAPI.
- generated TypeScript schema.
- deterministic schema.
- API compatibility check.

### Engineering

- lint.
- type check.
- test.
- PostgreSQL test environment.
- CI.
- migration checker.

## Specify message

```text
Feature: Project Foundation and API Contract Baseline

Create the technical foundation required by all later features.

Scope:

Backend:
- Django REST Framework foundation;
- PostgreSQL integration;
- config composition root;
- shared/core primitives;
- module architecture convention;
- standard error response;
- request ID;
- correlation context;
- /api/v1/ routing.

Frontend:
- Next.js application foundation;
- shared API transport;
- authenticatedFetch chokepoint;
- generated API types/client foundation;
- shared error handling.

Contracts:
- OpenAPI generation;
- stable operation IDs;
- deterministic schema output;
- generated TypeScript contract;
- schema drift verification;
- backward compatibility verification.

Engineering:
- lint;
- formatting;
- typing;
- test infrastructure;
- PostgreSQL integration testing;
- migration static checks;
- CI baseline.

Do not implement Auth, Location, Attendance, Task,
Notifications or Reporting.
```

## DoD

```text
[ ] Next.js boots
[ ] Django boots
[ ] PostgreSQL connection works
[ ] tests use PostgreSQL where required
[ ] /api/v1 exists
[ ] request_id exists
[ ] standard API error format exists
[ ] OpenAPI deterministic
[ ] generated TS schema works
[ ] CI passes
[ ] migration checker passes
```

Tài liệu yêu cầu `/api/v1/` được định nghĩa ở một vị trí canonical, schema sinh ổn định, `operationId` explicit và OpenAPI/TypeScript artifacts được kiểm drift. fileciteturn3file0L28-L28

---

# 002 — Identity + Authentication + RBAC

## Branch

```text
002-identity-auth-rbac
```

## Dependency

```text
001
```

## Chức năng

### User

- create user.
- list.
- search.
- filter.
- edit profile information.
- active/inactive.
- immutable username.
- role.

### Authentication

- login.
- access JWT.
- refresh JWT.
- rotation.
- blacklist.
- logout.
- password change.
- forced first password change.
- refresh revocation.

### Administration

- reset password.
- generated password.
- show password one time.
- account locking.

### Authorization

- LEADER.
- MANAGER.
- HELPDESK.
- PermissionAction.
- canonical role map.
- five permission implications.
- object scope foundation.
- capabilities.

## Specify

```text
Feature: Identity, Authentication and Canonical RBAC

Implement the identity and access-control model already defined by
the authoritative documents.

Scope:

User:
- User model;
- immutable unique username;
- required full_name;
- optional non-unique phone;
- optional non-unique email;
- active state;
- must_change_password.

Authentication:
- login;
- short-lived access token;
- refresh token;
- refresh rotation;
- blacklist/revocation;
- logout;
- password change;
- first-login password change enforcement.

Administration:
- list/search/filter users;
- create user;
- update allowed information;
- activate/deactivate;
- reset password;
- generate password server-side;
- display generated password exactly once.

Authorization:
- LEADER;
- MANAGER;
- HELPDESK;
- canonical PermissionAction map;
- documented PERMISSION_IMPLIES only;
- frontend capabilities;
- action permission before DTO validation;
- protected MANAGER target behavior.

Important:

- MANAGER cannot create another MANAGER;
- MANAGER cannot mutate existing MANAGER accounts through user admin;
- LEADER has no mutation actions;
- HELPDESK cannot administer users;
- MANAGER does not check in/out;
- self endpoints derive user from authentication context.

Add allow/deny acceptance scenarios.
```

## DoD

```text
[ ] login tests
[ ] refresh tests
[ ] refresh reuse denied
[ ] logout revokes correctly
[ ] account inactive checked on every request
[ ] must_change_password works
[ ] password reset works
[ ] MANAGER target protected
[ ] LEADER mutations denied
[ ] RBAC matrix tests
[ ] object-scope foundation tests
```

Quản lý chỉ được tạo/gán `LEADER` hoặc `HELPDESK`; existing Manager accounts vẫn được nhìn thấy nhưng bị chặn mọi thao tác ghi. fileciteturn3file1L40-L59

---

# 003 — Location + Geofence + Config + Seed

## Branch

```text
003-location-config
```

## Dependency

```text
002
```

## Chức năng

### Location

- BUSINESS_CENTER.
- SHOP.
- parent.
- radius.
- active.
- version.

### Seed

- 7 TTKD.
- 69 shops.
- 76 total.
- two CSV mappings.
- idempotency.

### Geofence

- Haversine.
- validated GPS.
- INSIDE.
- OUTSIDE.
- no UNCERTAIN.

### Config

- shift start.
- shift end.
- grace.
- max attendance accuracy.
- task GPS thresholds.
- radius.
- working weekdays.

### Holiday

- CRUD according to RBAC.

## Specify

```text
Feature: Location, Geofence, Configuration and Reference Data

Scope:

Location:
- Location model;
- LocationKind;
- parent;
- address;
- coordinates;
- radius;
- active state;
- optimistic version;
- list/read/update according to RBAC.

Seed:
- dia_chi_ttkd.csv;
- dia_chi_cua_hang.csv;
- explicit separate mappings;
- validate headers;
- exactly 7 BUSINESS_CENTER;
- exactly 69 SHOP;
- exactly 76 total records;
- preserve source coordinates;
- idempotency;
- duplicate code is an error;
- duplicate coordinates are valid;
- overlapping geofences are warnings only.

Geofence:
- GPS input validation;
- haversine;
- INSIDE_GEOFENCE;
- OUTSIDE_GEOFENCE;
- no UNCERTAIN;
- quality and radius remain independent.

Config:
- singleton configuration;
- shift;
- grace periods;
- radius configuration;
- attendance accuracy threshold;
- Task GPS thresholds;
- working weekdays.

Holiday:
- management using canonical RBAC.

Do not implement attendance/task workflows yet.
```

## DoD

```text
[ ] exactly 76 locations
[ ] exactly 7 centers
[ ] exactly 69 shops
[ ] CSV header validation
[ ] idempotent seed
[ ] duplicate coordinate accepted
[ ] duplicate code rejected
[ ] geofence tests
[ ] GPS validation tests
[ ] config validation tests
[ ] stale Location version returns conflict
```

Checklist hiện hành yêu cầu chính xác 76 Location, hai CSV dùng mapping header riêng biệt, duplicate coordinate là hợp lệ còn duplicate code mới chặn. fileciteturn3file0L13-L14

---

# 004 — Attendance Core

## Branch

```text
004-attendance-core
```

## Dependency

```text
002
003
```

## Chức năng

- Check In.
- Check Out.
- GPS quality.
- geofence.
- multiple Location candidates.
- Location selection.
- Attendance.
- AttendanceAttempt.
- AttendanceSession.
- multiple sessions/day.
- self history.
- punch index.

## Specify

```text
Feature: Attendance Check-In and Check-Out Core

Scope:

- HELPDESK Check-In;
- HELPDESK Check-Out;
- multiple sessions per work date;
- fresh GPS sample;
- GPS boundary validation;
- attendance-specific accuracy gate;
- geofence candidate resolution;
- no candidate;
- one candidate;
- multiple candidates;
- selected_location_id revalidation;
- Attendance persistence;
- AttendanceAttempt persistence;
- AttendanceSession lifecycle;
- SESSION_ALREADY_OPEN;
- NO_OPEN_SESSION;
- OUTSIDE_RADIUS;
- INVALID_LOCATION_CHOICE;
- LOCATION_CHOICE_REQUIRED;
- self attendance read model;
- derived punch_index.

Important:

- MANAGER cannot Check In/Out;
- kind is server-owned;
- user_id is server-owned;
- recorded_at is server UTC;
- work_date derives from Asia/Ho_Chi_Minh;
- quality gate and radius gate are independent;
- accuracy is never subtracted from radius;
- AttendanceAttempt semantics must match CHOT exactly;
- one open AttendanceSession per user is DB-enforced.

Include race-condition acceptance tests using PostgreSQL.
```

## DoD

```text
[ ] first check-in works
[ ] double check-in rejected
[ ] checkout works
[ ] checkout without session rejected
[ ] IN → OUT → IN → OUT supported
[ ] weak GPS rejected
[ ] outside radius rejected
[ ] one Location auto selected
[ ] multiple Locations require choice
[ ] invalid choice rejected
[ ] attempt logged correctly
[ ] pre-boundary request doesn't log attempt
[ ] partial unique DB constraint tested
[ ] concurrent double tap tested
```

Attendance hiện tại phải hỗ trợ nhiều lượt trong ngày, dùng partial unique index cho open session, và `AttendanceAttempt` có semantics riêng kể cả về transaction. fileciteturn3file0L15-L16

---

# 005 — Attendance Reconciliation + Anomalies

## Branch

```text
005-attendance-reconciliation
```

## Dependency

```text
004
```

## Chức năng

- duration.
- total worked time.
- LATE_CHECK_IN.
- EARLY_CHECK_OUT.
- LATE_CHECK_OUT.
- MISSING_CHECK_OUT.
- daily reconciliation.
- JobRun.
- job health.

## Specify

```text
Feature: Attendance Sessions, Anomalies and Daily Reconciliation

Scope:

- completed session duration;
- total work duration for a work date;
- first Check-In late evaluation;
- final Check-Out early evaluation;
- final Check-Out late evaluation;
- anomaly replacement when the final checkout changes;
- MISSING_CHECK_OUT;
- end-of-day job;
- closed_by_job;
- JobRun;
- operational job-health read model.

Important:

- an AttendanceSession represents working time, not continuous
  geofence presence;
- user can leave the location while session remains open;
- Check-Out may occur at a different Location;
- daily worked time is the sum of completed sessions;
- system-closed incomplete sessions retain NULL check_out;
- do not invent checkout timestamps;
- do not count incomplete session duration;
- reconciliation runs every calendar day;
- holiday/weekend does not disable reconciliation;
- no overnight sessions in MVP.

Job must be safe under repeated execution.
```

## DoD

```text
[ ] duration correct
[ ] multiple session sum correct
[ ] first IN determines lateness
[ ] last OUT determines early/late
[ ] previous final-OUT anomaly replaced correctly
[ ] missing checkout created
[ ] job is idempotent
[ ] weekends handled
[ ] holidays handled
[ ] incomplete session isn't included in hours
[ ] JobRun persisted
```

---

# 006 — Task Management Core

## Branch

```text
006-task-management
```

## Dependency

```text
002
003
```

## Chức năng

- Manager creates task.
- Helpdesk creates own task.
- multiple assignees.
- optional Location.
- assigned date.
- TODO.
- IN_PROGRESS.
- BLOCKED.
- COMPLETED state foundation.
- overdue.
- today.
- upcoming.
- completed.
- task history/update.

## Specify

```text
Feature: Task Management Core

Scope:

Task creation:
- MANAGER assigns tasks;
- HELPDESK may create arising tasks;
- one or multiple assignees;
- optional expected Location;
- assigned_date.

Lifecycle:
- TODO;
- IN_PROGRESS;
- BLOCKED;
- COMPLETED;
- canonical state transition matrix;
- BLOCKED requires block_reason;
- COMPLETED is terminal.

Task lists:
- Overdue;
- Today;
- Upcoming;
- Completed.

Assignment behavior:
- inactive assignee cannot receive new assignment;
- previously assigned inactive user remains historical assignee;
- assigned_date remains unchanged;
- overdue status and overdue days derive at read time.

Authorization:
- self scope means creator or assignee;
- MANAGER any-scope still obeys state machine;
- LEADER is read-only.

Do not implement photo/GPS evidence completion yet.
```

## DoD

```text
[ ] Manager create
[ ] Helpdesk self-create
[ ] multi assignee
[ ] inactive assignment blocked
[ ] state transition tests
[ ] BLOCKED requires reason
[ ] terminal COMPLETED enforced
[ ] self scope tests
[ ] overdue derived correctly
[ ] assigned_date immutable
```

---

# 007 — Task Completion + Evidence

## Branch

```text
007-task-evidence
```

## Dependency

```text
006
003
```

## Chức năng

### FIELD_EVIDENCE

- task completion.
- GPS.
- quality.
- Location resolution.
- multiple candidates.
- TaskUpdate.
- TaskPhoto.

### Upload

- staging.
- presigned upload.
- checksum.
- MIME.
- file size.
- finalize.
- idempotency.
- cleanup.
- local draft.

### MANAGER_OVERRIDE

- reason.
- optional photos.
- no required GPS.

### Presentation

- resolved address.
- Google Maps link.

## Specify

```text
Feature: Task Field Evidence and Completion

Scope:

FIELD_EVIDENCE:
- allowed creator/assignee completes Task;
- fresh GPS sample;
- TaskGpsQuality GOOD / LOW_ACCURACY / UNRELIABLE;
- Location matching;
- GOOD GPS with multiple candidates requires user selection;
- persist location_candidates snapshot;
- TaskUpdate append-only;
- atomic completion.

Photos:
- 1-5 photos for FIELD_EVIDENCE;
- client compression;
- supported image handling;
- maximum file size;
- private staging;
- EvidenceUpload;
- presigned upload;
- checksum/MIME/size verification;
- finalize;
- Idempotency-Key;
- expired upload cleanup.

Draft:
- locally persist compressed photos + note;
- account scoped;
- Task scoped;
- no GPS;
- no token;
- no presigned URL;
- documented purge behavior.

MANAGER_OVERRIDE:
- no mandatory GPS;
- 0-5 photos;
- mandatory reason/note;
- mandatory audit;
- distinct completion method.

Presentation:
- resolved_address derives only from Location;
- no external reverse geocoding;
- maps_url derives from exact record coordinates.
```

## DoD

```text
[ ] 1–5 evidence photos
[ ] 0 photos rejected for FIELD_EVIDENCE
[ ] >5 rejected
[ ] size validation
[ ] MIME validation
[ ] checksum verification
[ ] upload owner validation
[ ] Task validation
[ ] idempotent finalize
[ ] weak Task GPS doesn't use Attendance rule
[ ] LOW_ACCURACY supported
[ ] UNRELIABLE supported
[ ] multiple GOOD candidates require selection
[ ] MANAGER_OVERRIDE works
[ ] manager reason required
[ ] maps URL uses captured coordinates
[ ] no EXIF GPS
```

Task GPS policy khác Attendance và FIELD_EVIDENCE có riêng quy tắc ảnh/upload; checklist yêu cầu 1–5 ảnh cho FIELD_EVIDENCE nhưng `MANAGER_OVERRIDE` dùng reason bắt buộc thay cho GPS/ảnh bắt buộc. fileciteturn3file0L17-L19

---

# 008 — Notifications

## Branch

```text
008-notifications
```

## Dependency

```text
004
005
006
007
```

## Chức năng

- in-app notifications.
- unread/read.
- push subscriptions.
- web push.
- Task assigned.
- upcoming Task.
- overdue Task.
- open Attendance session.
- multi-assignee task completed.
- quiet hours.
- dedupe.
- suppression.

## Specify

```text
Feature: In-App Notifications and Web Push

Supported events only:

1. Task newly assigned;
2. Task approaching assigned_date;
3. Task overdue;
4. Attendance session still open near shift end;
5. Multi-assignee Task completed by another assignee.

Scope:

- Notification persistence;
- inbox;
- unread/read;
- PushSubscription;
- opt-in;
- unsubscribe/revoke;
- delivery scheduling;
- quiet hours;
- TTL;
- dedupe;
- suppression/revalidation;
- authorization-safe deep links.

Requirements:

- in-app is the authoritative complete source;
- push is best effort;
- quiet hours: 21:00-07:00 Asia/Ho_Chi_Minh;
- push payload is generic;
- do not expose names/GPS/photos on lock screen;
- revoke subscription on logout/account switch/inactive account.

Do not implement email or SMS.
Do not create lock/reset-password notifications.
```

## DoD

```text
[ ] exactly five event types
[ ] in-app works without push
[ ] read/unread
[ ] opt-in
[ ] revoke
[ ] quiet hours
[ ] TTL
[ ] dedupe
[ ] suppression
[ ] generic lock screen
[ ] stale deep link authorization rechecked
```

Notification scope đã được chốt đúng năm event và in-app mới là nguồn đầy đủ. fileciteturn1file13L470-L488

---

# 009 — Reporting + Dashboard + Export

## Branch

```text
009-reporting
```

## Dependency

```text
004
005
006
007
```

## Chức năng

### Attendance reporting

- currently working.
- no Check-In.
- checked out.
- session list.
- work duration.
- missing checkout.
- anomalies.
- attempts.
- failure rate.

### Task reporting

- status.
- completed.
- assigned closed.
- actually completed.
- GPS quality.
- completion method.

### Filters

- date.
- employee.
- range.

### Export

- sensitive coordinate opt-in.
- audit.
- no-store.

## Specify

```text
Feature: Reporting, Dashboard and Export

Attendance reports:

- currently open sessions;
- employees with no Check-In;
- employees checked out;
- daily attendance history;
- session list;
- total completed-session duration;
- missing-checkout sessions;
- attendance anomaly report;
- attendance attempt report;
- rejected attempt analysis;
- nearest-location diagnostics;
- attendance failure rate.

Task reports:

- total;
- TODO;
- IN_PROGRESS;
- BLOCKED;
- COMPLETED;
- completion method;
- GPS quality;
- actual completion actor;
- assigned-task-closed metric;
- employee filter;
- date-range filter.

Operational reporting:
- reconciliation job health.

Export:
- authorization controlled;
- exclude coordinates/maps/photo URLs by default;
- explicit sensitive-data opt-in;
- audit sensitive exports;
- no-store.

Reporting must remain read-only.

Important:

- anomalies and rejected attempts are distinct datasets;
- LOCATION_CHOICE_REQUIRED is excluded from both numerator and
  denominator of failure rate;
- expose numerator, denominator, excluded count and coverage;
- zero denominator = N/A;
- incomplete system-closed sessions do not contribute work duration;
- "actually completed" and "assigned task closed" are separate metrics.
```

## DoD

```text
[ ] attendance dashboard
[ ] session reporting
[ ] total duration reporting
[ ] anomaly report
[ ] attempt report
[ ] correct failure-rate formula
[ ] zero denominator N/A
[ ] Task reports
[ ] GPS quality reporting
[ ] completion method reporting
[ ] sensitive export opt-in
[ ] export audit
[ ] no-store
```

PRD yêu cầu tách rõ anomaly khỏi rejected attempt, và tách “việc tự tay hoàn thành” khỏi “việc được giao đã đóng”. fileciteturn3file1L142-L189

---

# 010 — Audit + Transactional Outbox

## Branch

```text
010-audit-outbox
```

## Dependency

```text
001+
```

## Chức năng

- AuditLog.
- immutable logs.
- OutboxEvent.
- event envelope.
- transaction participation.
- request/correlation.
- sanitizer.
- architecture boundaries.

## Specify

```text
Feature: Audit and Transactional Outbox

Scope:

Audit:
- immutable AuditLog;
- canonical fields;
- mandatory sensitive mutations;
- append_audit_entry application port.

Outbox:
- OutboxEvent;
- canonical event envelope;
- append_outbox_event;
- request/correlation context;
- transaction participation.

Safety:
- shared payload filter;
- exact forbidden keys;
- reject credential/URL-like sensitive values;
- errors must report paths, never secret values.

Architecture:
- business modules may cross state boundaries only using
  approved application ports;
- static architecture checks where required.

Transaction rule:

append_audit_entry and append_outbox_event participate in the
caller's transaction.

They must not:
- open their own atomic transaction;
- use transaction.on_commit internally.

Caller rollback must remove audit/outbox entries.
```

## DoD

```text
[ ] audit immutable
[ ] audit sensitive operations
[ ] outbox envelope correct
[ ] rollback removes audit
[ ] rollback removes outbox
[ ] payload redaction/filter
[ ] no secret leakage
[ ] architecture boundary tests
```

Audit/outbox phải cùng transaction với business change, không tự tạo transaction hoặc `on_commit`. fileciteturn3file0L25-L25

---

# 011 — Reliable Outbox Relay

## Branch

```text
011-outbox-relay
```

## Dependency

```text
010
```

## Chức năng

- claim.
- lease.
- retry.
- backoff.
- dead letter.
- consumer dedupe.
- worker concurrency.

## Specify

```text
Feature: Reliable Outbox Relay

Scope:

- persisted publish state;
- claimable events;
- SELECT FOR UPDATE SKIP LOCKED;
- lease_expires_at;
- leased_by;
- attempt_count;
- next_attempt_at;
- exponential backoff with cap;
- DEAD_LETTER;
- sanitized error;
- transport abstraction;
- consumer deduplication;
- relay command as thin adapter.

Concurrency requirements:

- concurrent workers claim disjoint sets;
- claim transaction does not contain transport calls;
- crashed worker recovers through lease expiration;
- no manual release is required.

Reliability:

- one failed event does not abort the batch;
- exhausted event remains persisted;
- consumer dedupe is UNIQUE(consumer, event_id);
- consumer receipt participates in consumer business transaction.
```

## DoD

```text
[ ] two workers claim disjoint rows
[ ] SKIP LOCKED test
[ ] lease expiry reclaim
[ ] retry count
[ ] capped backoff
[ ] dead letter retained
[ ] sanitized error
[ ] batch continues after failure
[ ] consumer dedupe
[ ] consumer rollback behavior
```

---

# 012 — Observability + Operational Health

## Branch

```text
012-observability
```

## Dependency

```text
005
011
```

## Chức năng

- structured logging.
- request/correlation ID.
- metrics.
- alerts.
- sanitization.
- operational health.
- retention.
- pruning.

## Specify

```text
Feature: Operational Telemetry, Health and Retention

Scope:

Logging:
- dictConfig;
- request/correlation fields;
- operational logger names.

Metrics:
- closed metric registry;
- closed label vocabularies;
- reject unknown metric/labels.

Alerts:
- sanitized reasons;
- sensitive-data redaction;
- alert transport failure cannot break business operation.

Health:
- pure health evaluation;
- attendance reconciliation health;
- outbox relay health;
- recovery drill health where applicable;
- missing data is not automatically healthy.

Retention:
- documented retention classes;
- batched pruning;
- preserve pending OutboxEvent regardless of age;
- preserve immutable AuditLog according to project rules.

Do not add an external observability platform unless the
authoritative requirements explicitly need it.
```

## DoD

```text
[ ] logging configured
[ ] correlation works
[ ] unknown metric rejected
[ ] unknown label rejected
[ ] redaction tests
[ ] GPS doesn't leak
[ ] URLs/tokens don't leak
[ ] telemetry failure isolated
[ ] health unknown behavior correct
[ ] retention batch tested
[ ] pending outbox preserved
```

---

# 013 — Deployment + Migration + Backup + Recovery

## Branch

```text
013-production-readiness
```

## Dependency

```text
001–012
```

## Chức năng

### Environment

- development.
- staging.
- production.
- secret references.
- DB app/admin separation.
- cache configuration.
- Redis policy if selected.
- edge/origin boundary.

### Migration

- static migration checker.
- expand/migrate/contract.
- release compatibility.

### Recovery

- backup manifest.
- recovery evidence.
- RPO.
- RTO.
- restore drill.
- read-only verification.
- capacity check.

## Specify

```text
Feature: Deployment, Environment Isolation, Migration Safety and Recovery

Scope:

Environment isolation:
- development;
- staging;
- production;
- deploy/environments.yaml;
- fail-closed environment parsing;
- separate secret references;
- application DB versus migration/admin DB;
- cache backend policy;
- Redis security policy where configured;
- frontend/backend origin credential boundary;
- deployment isolation checks.

Migration safety:
- one migration leaf per application;
- expand/migrate/contract;
- backwards-compatible rollout;
- static migration checker;
- destructive migration separation.

Backup and recovery:
- backup configuration metadata;
- recovery evidence;
- RPO target;
- RTO target;
- restore drill;
- recovery database identity isolation;
- read-only recovery verification;
- capacity verification.

Do not invent unresolved infrastructure values.

Keep infrastructure decisions marked unresolved until an
authorized operator supplies them.

Do not report production readiness while mandatory evidence or
configuration remains unresolved.
```

## DoD

```text
[ ] dev/staging/prod separate
[ ] secrets not committed
[ ] application/admin DB separated
[ ] fail-closed env parsing
[ ] cache policy verified
[ ] deployment isolation checker
[ ] migration checker
[ ] expand/contract rules tested
[ ] backup metadata
[ ] restore verification
[ ] recovery DB isolation
[ ] capacity check
[ ] production-ready fails when unresolved
```

Hiện requirement nghiệp vụ đã không còn OPEN; các điểm còn treo thuộc lựa chọn infrastructure staging/production và phải được giữ `UNRESOLVED` cho đến khi người có thẩm quyền cung cấp. fileciteturn4file0L5-L24

---

# 14 — Full-System Analysis

Sau khi 001–013 hoàn thành, không deploy ngay.

Chạy:

```text
/speckit.analyze
```

## Message

```text
Perform a FULL SYSTEM consistency audit.

This audit covers the entire application, not the currently selected
feature only.

Read:

- Project Constitution;
- all specs/*/spec.md;
- all specs/*/plan.md;
- all specs/*/tasks.md;
- CHOT_YEU_CAU.md;
- QUY_TAC_CLEAN_CODE.md;
- RA_SOAT_YEU_CAU.md;
- PRD;
- current implementation;
- tests;
- API contracts;
- migrations.

Build a traceability matrix:

CHOT requirement
→ Feature specification
→ Implementation component
→ Tests

Verify:

1. every CHOT requirement has an owner;
2. no requirement is duplicated with contradictory semantics;
3. canonical vocabulary is respected;
4. module boundaries are respected;
5. RBAC uses only the canonical permission model;
6. object scopes are correct;
7. permission checks precede DTO validation;
8. server-owned data cannot be client supplied;
9. database invariants are actually DB-enforced;
10. documented concurrency races are tested;
11. transactions match documented boundaries;
12. audit coverage is complete;
13. outbox coverage is complete;
14. event relay is safe under concurrency;
15. jobs are idempotent;
16. notification behavior uses committed state;
17. reporting is read-only;
18. migration history is rollout-safe;
19. API contract matches implementation;
20. generated frontend contract matches OpenAPI;
21. tokens/passwords/GPS/secrets cannot leak;
22. production readiness checks match authoritative deployment rules.

Classify:

CRITICAL
HIGH
MEDIUM
LOW

Do not fix code during this pass.
```

---

# 15 — Cross-feature E2E scenarios

Sau full-system analyze, chạy E2E theo business flow thực tế.

## Flow 1 — Tạo nhân viên

```text
Manager Login
→ Create HELPDESK
→ Generated Password
→ Employee Login
→ PASSWORD_CHANGE_REQUIRED
→ Change Password
→ New access + refresh
→ Old refresh invalid
```

---

## Flow 2 — Attendance bình thường

```text
Helpdesk Login
→ GPS
→ one Location
→ Check In
→ Attendance
→ AttendanceAttempt ACCEPTED
→ AttendanceSession open
→ Check Out
→ Session closed
→ duration calculated
```

---

## Flow 3 — Multiple Locations

```text
GPS
→ two candidate Locations
→ 409 LOCATION_CHOICE_REQUIRED
→ user chooses Location
→ backend recomputes candidates
→ validates selected_location_id
→ Check In accepted
```

---

## Flow 4 — Weak Attendance GPS

```text
GPS accuracy > attendance threshold
→ WEAK_GPS
→ no Attendance
→ no AttendanceSession
→ AttendanceAttempt recorded
```

---

## Flow 5 — Multiple attendance sessions

```text
IN
→ OUT
→ IN
→ OUT

daily duration
=
session1.duration
+
session2.duration
```

---

## Flow 6 — Missing Check Out

```text
Check In
→ no Check Out
→ end-of-day reconciliation
→ session closed_by_job
→ check_out remains NULL
→ duration remains NULL
→ MISSING_CHECK_OUT
→ report contains incomplete session
```

---

## Flow 7 — Task assignment

```text
Manager
→ Create Task
→ assign Helpdesk A + B
→ notification A
→ notification B
→ Task appears Today/Upcoming
```

---

## Flow 8 — FIELD_EVIDENCE

```text
Helpdesk
→ Task
→ upload evidence photos
→ fresh GPS
→ finalize
→ verify photos
→ resolve Location
→ TaskUpdate
→ Task COMPLETED
→ TaskPhoto bindings
→ multi-assignee notification
```

---

## Flow 9 — Weak Task GPS

```text
Task completion
→ GPS LOW_ACCURACY
→ warning
→ completion still allowed
→ location NULL as documented
→ gps_quality preserved
→ reporting distinguishes weak GPS
```

---

## Flow 10 — Manager override

```text
Manager
→ Task
→ MANAGER_OVERRIDE
→ required reason
→ GPS optional
→ photos optional
→ Task complete
→ AuditLog
```

---

## Flow 11 — User locking

```text
Manager
→ disable Helpdesk
→ next API request rejected
→ existing refresh sessions revoked
→ existing Task history preserved
→ cannot receive new assignment
→ historical reporting unchanged
```

---

## Flow 12 — Reporting

```text
Leader Login
→ attendance reports
→ task reports
→ location/config read
→ no user admin
→ no mutations

Manager Login
→ full reports
→ explicit sensitive export
→ AuditLog created
```

---

# 16 — Security verification

Chạy riêng một security pass:

```text
Authentication
Authorization
Object Scope
Input Validation
Rate Limits
CSRF
CORS/origin boundary
Secrets
JWT lifecycle
Password leakage
GPS privacy
Photo access
Audit
Outbox payload
Logs
Reports
Exports
```

Critical negative tests:

```text
HELPDESK cannot:
- manage users
- modify Location
- view all attendance without permission
- MANAGER_OVERRIDE arbitrary Tasks

LEADER cannot:
- mutate Task
- modify Config
- modify Location
- manage users
- Check In/Out

MANAGER cannot:
- Check In/Out
- create MANAGER account
- mutate existing MANAGER through user admin

Client cannot supply:
- recorded_at
- work_date
- validation_result
- resolution_method
- gps_quality
- authenticated user_id
- attendance kind
```

---

# 17 — Final CI pipeline

Pipeline cuối nên gần như:

```text
Install
  ↓
Formatting
  ↓
Lint
  ↓
Type Check
  ↓
Architecture checks
  ↓
Migration static check
  ↓
Unit Tests
  ↓
PostgreSQL Integration Tests
  ↓
Concurrency Tests
  ↓
RBAC Matrix Tests
  ↓
API Contract Generation
  ↓
OpenAPI Drift
  ↓
Backward Compatibility
  ↓
Frontend Contract Generation
  ↓
Frontend Tests
  ↓
Build Backend
  ↓
Build Frontend
  ↓
Security Static Checks
```

Không phải mọi operational readiness command nhất thiết trở thành CI gate. Những check cần evidence môi trường thật như restore drill/capacity/production readiness phải giữ đúng semantics mà tài liệu đã chốt.

---

# 18 — Quy tắc commit / PR

Mỗi feature nên hoàn thành trên branch riêng:

```text
001-project-foundation
002-identity-auth-rbac
003-location-config
004-attendance-core
005-attendance-reconciliation
006-task-management
007-task-evidence
008-notifications
009-reporting
010-audit-outbox
011-outbox-relay
012-observability
013-production-readiness
```

Một feature chỉ merge khi:

```text
Specification        PASS
Clarification        PASS
Plan                 PASS
Tasks                PASS
Analyze CRITICAL=0   PASS
Implementation       PASS
Tests                PASS
CI                   PASS
Review               PASS
```

---

# 19 — Definition of Done chung

Mỗi feature phải qua checklist:

```text
[ ] CHOT requirements covered
[ ] spec complete
[ ] no unresolved functional ambiguity
[ ] plan consistent
[ ] tasks complete
[ ] analyze has zero CRITICAL findings
[ ] implementation matches spec
[ ] canonical vocabulary respected
[ ] permissions implemented
[ ] object scope implemented
[ ] permission-before-validation respected
[ ] client/server ownership respected
[ ] DB invariants enforced
[ ] concurrency handled
[ ] audit implemented where required
[ ] outbox implemented where required
[ ] error codes preserved
[ ] unit tests pass
[ ] PostgreSQL tests pass
[ ] race tests pass where applicable
[ ] deny tests pass
[ ] migration checks pass
[ ] API contract updated
[ ] generated frontend contract updated
[ ] lint passes
[ ] type check passes
[ ] frontend build passes
[ ] backend checks pass
[ ] CI passes
```

---

# 20 — Quy trình thực tế từ đầu đến cuối

Cuối cùng, thứ tự bạn thực sự gõ sẽ là:

```text
specify init .

/speckit.constitution


# FEATURE 001
/speckit.specify
/speckit.clarify
/speckit.plan
/speckit.tasks
/speckit.analyze
/speckit.implement


# FEATURE 002
/speckit.specify
/speckit.clarify
/speckit.plan
/speckit.tasks
/speckit.analyze
/speckit.implement


# FEATURE 003
/speckit.specify
/speckit.clarify
/speckit.plan
/speckit.tasks
/speckit.analyze
/speckit.implement


# FEATURE 004
/speckit.specify
/speckit.clarify
/speckit.plan
/speckit.tasks
/speckit.analyze
/speckit.implement


# FEATURE 005
/speckit.specify
/speckit.clarify
/speckit.plan
/speckit.tasks
/speckit.analyze
/speckit.implement


# FEATURE 006
/speckit.specify
/speckit.clarify
/speckit.plan
/speckit.tasks
/speckit.analyze
/speckit.implement


# FEATURE 007
/speckit.specify
/speckit.clarify
/speckit.plan
/speckit.tasks
/speckit.analyze
/speckit.implement


# FEATURE 008
/speckit.specify
/speckit.clarify
/speckit.plan
/speckit.tasks
/speckit.analyze
/speckit.implement


# FEATURE 009
/speckit.specify
/speckit.clarify
/speckit.plan
/speckit.tasks
/speckit.analyze
/speckit.implement


# FEATURE 010
/speckit.specify
/speckit.clarify
/speckit.plan
/speckit.tasks
/speckit.analyze
/speckit.implement


# FEATURE 011
/speckit.specify
/speckit.clarify
/speckit.plan
/speckit.tasks
/speckit.analyze
/speckit.implement


# FEATURE 012
/speckit.specify
/speckit.clarify
/speckit.plan
/speckit.tasks
/speckit.analyze
/speckit.implement


# FEATURE 013
/speckit.specify
/speckit.clarify
/speckit.plan
/speckit.tasks
/speckit.analyze
/speckit.implement


# FULL APPLICATION
/speckit.analyze

# Fix findings

# Full test / E2E / security / staging
```

## Nguyên tắc quan trọng nhất

Không làm:

```text
specify 001
specify 002
specify 003
...
specify 013

→ plan cả hệ thống
→ implement cả hệ thống
```

Mà làm:

```text
001
specify → clarify → plan → tasks → analyze → implement

002
specify → clarify → plan → tasks → analyze → implement

003
specify → clarify → plan → tasks → analyze → implement

...

013
specify → clarify → plan → tasks → analyze → implement

→ Full-System Analyze
→ E2E
→ Security
→ Staging
→ Production Readiness
```

Đây là workflow chính cho toàn bộ ứng dụng.
