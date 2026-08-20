# Feature Specification: Task Management Core

**Feature Branch**: `feature/007-task-management-core` *(planned; no branch hook is configured)*

**Created**: 2026-08-20

**Status**: Draft

**Input**: User description: "Complete Feature 007 Task Management, including balanced and maintainable role-aware UI across every page, responsive Tasks/Attendance navigation and layouts, distinct typography/status badges, and field completion with photo/GPS evidence upload."

## Clarifications

### Session 2026-08-20

- Q: How much assignee-management authority should a HELPDESK user have on a task within their creator-or-assignee scope? → A: A Helpdesk-created task is automatically assigned only to its creator; only MANAGER may add or remove assignees.
- Q: What should happen when an authorized user submits the task’s current status again? → A: Return the current task successfully with no write, TaskUpdate, audit, outbox event, or version change.
- Q: Which user-facing completion paths should Feature 007 provide? → A: Implement both governed FIELD_EVIDENCE and Manager override as distinct methods; ordinary status updates cannot target COMPLETED.
- Q: When two status requests read the same initial task state and race, what should happen to the request that acquires the task lock second? → A: Re-read the latest state under lock and commit only if the transition remains valid; otherwise apply same-state no-op or reject without side effects.
- Q: After a Task moves to COMPLETED, which changes remain allowed? → A: None; the completed Task is read-only for status, content, expected Location, and assignees, while reads and reports remain available.
- Q: How is the former photo/GPS deferral resolved? → A: Feature 007 now implements the already-governed FIELD_EVIDENCE flow from CHOT §6.2 while retaining Manager override as a distinct completion method.
- Q: What UI scope is included? → A: Every existing application page uses one responsive role-aware shell, shared typography/form/action primitives, and clearly differentiated statuses and supporting text.
- Q: Does MANAGER_OVERRIDE accept optional evidence photos? → A: No. MANAGER_OVERRIDE accepts neither photos nor GPS; it requires a non-empty completion note and audit evidence.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create and assign work (Priority: P1)

A MANAGER creates a task for one or more active HELPDESK employees, chooses the work date, and may identify an expected Location. A HELPDESK employee can also record an arising task for themselves so unplanned work is visible and governed by the same lifecycle.

**Why this priority**: Work cannot be tracked until planned and arising tasks can be recorded with clear ownership and scheduling.

**Independent Test**: Create one Manager-assigned task with multiple active assignees and an expected Location, then create one Helpdesk arising task without a Location; verify the creator, assignees, original assigned date, initial status, and optional Location on each task.

**Acceptance Scenarios**:

1. **Given** a MANAGER and two active HELPDESK users, **When** the Manager creates a task assigned to both users for a selected date, **Then** one task is created in `TODO` with both users as assignees and with the selected `assigned_date`.
2. **Given** an active Location, **When** the Manager includes it as the expected Location, **Then** the task retains that Location as optional planning information.
3. **Given** a HELPDESK user encounters unplanned work, **When** they create an arising task, **Then** the task is created by and assigned to that same user in `TODO`.
4. **Given** a HELPDESK user attempts to create an arising task for another user, **When** the request is evaluated, **Then** it is rejected and no task or assignment is created.
5. **Given** any create request without at least one effective assignee, **When** it is evaluated, **Then** it is rejected and no task is created.
6. **Given** a HELPDESK user is the creator or an assignee of an existing task, **When** they attempt to add, remove, or replace an assignee, **Then** the entire request is rejected and the assignee set remains unchanged.

---

### User Story 2 - Progress work through one canonical lifecycle (Priority: P1)

An authorized task participant records when work starts or becomes blocked, including the reason for a block. Every task follows one shared state machine, and completion cannot be reversed.

**Why this priority**: A single enforceable lifecycle prevents contradictory task status, lost blockers, and accidental reopening of completed work.

**Independent Test**: Exercise every cell in the canonical transition matrix under an authorized self-scope actor and under a Manager with any-scope; verify allowed changes, rejected changes, required block reasons, and terminal completion behavior.

**Acceptance Scenarios**:

1. **Given** a `TODO` task in the actor's scope, **When** the actor starts it, **Then** its state becomes `IN_PROGRESS`.
2. **Given** a non-completed task in the actor's scope, **When** the actor changes it to `BLOCKED` with a non-empty reason, **Then** the task becomes `BLOCKED` and retains the reason.
3. **Given** a non-completed task, **When** an authorized actor requests `BLOCKED` without a non-empty reason, **Then** the request is rejected and task state is unchanged.
4. **Given** a `BLOCKED` task, **When** an authorized actor resumes it, **Then** the task becomes `IN_PROGRESS` without creating a replacement task.
5. **Given** a task reaches `COMPLETED` through an authorized completion workflow, **When** any actor, including a MANAGER with any-scope update authority, requests another state, **Then** the request is rejected and the task remains `COMPLETED`.
6. **Given** a MANAGER updates a task outside their creator/assignee relationship, **When** the requested transition is not allowed by the matrix, **Then** it is rejected despite the Manager's any-scope authority.
7. **Given** a non-completed task, **When** a MANAGER completes it through Manager override with a non-empty completion note, **Then** exactly one `COMPLETED` lifecycle update, completion snapshot, and audit record commit together without GPS or photos.
8. **Given** an actor submits `COMPLETED` to the ordinary status operation, **When** the request is evaluated, **Then** it is rejected without changing task state, even if the actor has self-scope or Manager any-scope update authority.
9. **Given** two ordinary status requests race from the same observed state, **When** they serialize on the task, **Then** the second request is evaluated from the first request's committed state and commits only if that resulting transition is still allowed.
10. **Given** a completed task, **When** any actor attempts to change its status, title, description, expected Location, or assignees, **Then** the request is rejected with no business side effects while the task remains readable.

#### Canonical State Transition Matrix

| From \ To | `TODO` | `IN_PROGRESS` | `BLOCKED` | `COMPLETED` |
|---|:---:|:---:|:---:|:---:|
| `TODO` | No change | Allowed | Allowed | Allowed |
| `IN_PROGRESS` | Rejected | No change | Allowed | Allowed |
| `BLOCKED` | Rejected | Allowed | No change | Allowed |
| `COMPLETED` | Rejected | Rejected | Rejected | Rejected |

For `TODO`, `IN_PROGRESS`, and `BLOCKED`, an unchanged-state request is not a lifecycle transition: after permission, input validation, and object scope succeed, it returns the current task successfully and creates no write, lifecycle update, audit, outbox event, or version change. A currently `BLOCKED` task does not require the reason to be resubmitted for this no-op. A completed task rejects every mutation request, including resubmitting `COMPLETED`. Every Rejected cell leaves the task and its history unchanged. The three allowed matrix transitions into `COMPLETED` are invoked only through the specialized FIELD_EVIDENCE or Manager override workflows; the ordinary status operation cannot target `COMPLETED`.

---

### User Story 3 - Focus on overdue and current work (Priority: P1)

An authorized user views tasks grouped as Overdue, Today, Upcoming, and Completed, with overdue work shown first and its lateness calculated from the current business date.

**Why this priority**: Staff and supervisors need an immediate, stable view of missed, current, future, and finished work without changing historical assignment dates.

**Independent Test**: Create incomplete tasks before, on, and after the current Asia/Ho_Chi_Minh date plus a completed task, then verify membership in exactly one group, ordering of groups, preservation of assigned dates, and derived overdue days across a date boundary.

**Acceptance Scenarios**:

1. **Given** an incomplete task with `assigned_date` before today, **When** the list is read, **Then** it appears in Overdue with its original date and `overdue_days = today - assigned_date`.
2. **Given** an incomplete task assigned today, **When** the list is read, **Then** it appears in Today.
3. **Given** an incomplete task assigned after today, **When** the list is read, **Then** it appears in Upcoming and is not counted as today's work.
4. **Given** a completed task with any assigned date, **When** the list is read, **Then** it appears in Completed and not in a date-based incomplete group.
5. **Given** an incomplete task remains open across midnight in Asia/Ho_Chi_Minh, **When** the list is read on the new day, **Then** its group and overdue days are recalculated without changing `assigned_date`.
6. **Given** a task list containing overdue and today tasks, **When** it is presented, **Then** Overdue appears before Today.

---

### User Story 4 - Preserve assignment history when accounts become inactive (Priority: P2)

A MANAGER cannot assign new work to an inactive employee, while tasks assigned before deactivation preserve their assignees, state, visibility, and historical reporting meaning.

**Why this priority**: Blocking new assignment protects operations, while retaining old relationships prevents account administration from rewriting business history.

**Independent Test**: Attempt a mixed active/inactive assignment, deactivate an existing assignee, and then read and edit the task without adding that user anew; verify atomic rejection for the new assignment and preservation of the historical assignment.

**Acceptance Scenarios**:

1. **Given** an assignment request containing one active and one inactive HELPDESK user, **When** the task is created, **Then** the entire request is rejected, identifies the inactive assignee, and creates neither the task nor any assignment.
2. **Given** a task already assigned to an active user, **When** that user becomes inactive, **Then** the assignment, task status, and list membership remain unchanged.
3. **Given** a non-completed task has a now-inactive historical assignee, **When** a Manager edits non-assignment details, **Then** the edit is not rejected merely because that historical assignee is inactive.
4. **Given** an existing task has a now-inactive historical assignee, **When** a request newly adds that same inactive user after removal or adds another inactive user, **Then** the entire assignment change is rejected.

---

### User Story 5 - Enforce task scope by role and relationship (Priority: P2)

HELPDESK users may read and update only tasks they created or were assigned. MANAGER users may read and update any task but remain bound by lifecycle and assignment invariants. LEADER users may inspect all tasks but cannot mutate them.

**Why this priority**: Relationship scope protects employee work data, while read-only oversight and Manager coordination remain possible without bypassing business rules.

**Independent Test**: For the same task, exercise creator, assignee, unrelated Helpdesk, Manager, Leader, and unauthenticated access across reads and mutations; verify action permission, object scope, and state invariants independently.

**Acceptance Scenarios**:

1. **Given** a HELPDESK user created a task but is not otherwise assigned, **When** they read or make an allowed core update, **Then** self scope grants access.
2. **Given** a HELPDESK user is an assignee but not the creator, **When** they read or make an allowed core update, **Then** self scope grants access.
3. **Given** a HELPDESK user is neither creator nor assignee, **When** they attempt to read or mutate the task, **Then** access is denied without changing the task.
4. **Given** a MANAGER is neither creator nor assignee, **When** they read or request an allowed update, **Then** any-scope grants access; an invalid transition or inactive new assignment is still rejected.
5. **Given** a LEADER reads any task, **When** authorization is evaluated, **Then** read access succeeds.
6. **Given** a LEADER attempts any create, update, assignment, status, or completion mutation, **When** authorization is evaluated, **Then** it is denied before business mutation and no task data changes.

---

### User Story 6 - Complete work with field evidence (Priority: P1)

An authorized creator or assignee selects one to five photos, uploads each photo safely, captures a fresh device position, and completes the task with durable photo and location evidence. A partially failed upload can resume without re-uploading successful photos.

**Why this priority**: Staff currently have no usable path to prove that assigned field work was completed, so the primary operational lifecycle is incomplete.

**Independent Test**: Prepare two valid images for an in-scope task, upload both through private staging, capture a fresh position, and finalize completion; verify one terminal lifecycle update, bound photo records, location evidence, completion snapshot, idempotent retry, and authorized read access.

**Acceptance Scenarios**:

1. **Given** an authorized creator or assignee and one to five valid photos, **When** upload intents are created and every declared object is uploaded, **Then** each private staging object remains bound to that actor and task without changing task status.
2. **Given** one photo upload fails after other photos succeed, **When** the user retries, **Then** already successful uploads are retained and only incomplete uploads need retrying.
3. **Given** one to five verified uploads and a fresh valid position, **When** the actor finalizes with an idempotency key, **Then** the task, completion update, photos, and bound upload intents commit atomically as `FIELD_EVIDENCE`.
4. **Given** the same idempotency key and normalized payload after a committed completion, **When** the request is retried, **Then** the original result is returned without duplicate lifecycle or photo evidence; a different payload with that key is rejected.
5. **Given** good-quality GPS inside more than one active Location, **When** no valid Location is selected, **Then** completion is not committed and the current candidates are returned for user selection.
6. **Given** low-accuracy or unreliable GPS with otherwise valid evidence, **When** the actor confirms completion, **Then** the task may complete with a warning and without falsely assigning a verified Location.
7. **Given** an out-of-scope actor, a reused upload, an upload owned by another actor/task, an invalid file, or an already completed task, **When** finalize is attempted, **Then** no partial task, photo, binding, or audit side effect is committed.
8. **Given** an authorized viewer of a completed task, **When** they open its history, **Then** they see evidence metadata, a protected photo-access action, the stored coordinates and accuracy, an address-resolution label, and a safe Google Maps link built from captured coordinates.
9. **Given** a supported JPEG, PNG, WebP, or readable HEIC source image, **When** the client prepares field evidence, **Then** HEIC is converted to JPEG when necessary, every image is compressed to at most 5 MB, and neither client nor server uses EXIF GPS.
10. **Given** compressed photos and an optional note before finalization, **When** the user leaves and returns to the same Task under the same account, **Then** the local draft can be restored without persisting GPS, tokens, or presigned URLs.
11. **Given** a MANAGER uses the override completion path, **When** a non-empty completion note is submitted without photos or GPS, **Then** the Task completes as `MANAGER_OVERRIDE` with mandatory audit evidence; any photo or GPS field is rejected.

---

### User Story 7 - Use every page comfortably on mobile and desktop (Priority: P1)

Each authenticated role sees a clear current-page header and only the navigation appropriate to that role. Inputs, actions, statuses, descriptions, and content columns remain visually distinct and balanced at phone and desktop widths.

**Why this priority**: Crowded actions, undifferentiated text, and overflowing navigation currently hide Attendance from the Tasks tab and make routine work hard to scan.

**Independent Test**: Visit every existing route as each supported role at 360 px and 1280 px viewport widths; verify the page identity, role-appropriate navigation, zero horizontal page overflow, readable typography, consistent field/action spacing, and stable content widths.

**Acceptance Scenarios**:

1. **Given** a phone viewport on Tasks, **When** the employee navigation is shown, **Then** Tasks and Attendance are both visible within the viewport without horizontal scrolling.
2. **Given** any supported desktop viewport, **When** lists, forms, cards, and page content render, **Then** columns use consistent constraints and no page or card is uneven because an input or action exceeds its container.
3. **Given** a task or attendance status plus supporting description, **When** it is presented, **Then** status uses a semantic badge and supporting text uses a visually secondary typography style.
4. **Given** any form, **When** actions render below fields, **Then** reusable spacing separates buttons from input controls and touch targets remain accessible.
5. **Given** an authenticated user opens any route, **When** the page renders, **Then** a shared header names the current page and the available destinations reflect that role's effective capabilities.

---

### User Story 8 - Correct task entry and field completion failures (Priority: P1)

Task creators can describe any expected workplace, successful creation clears the form, and Helpdesk can remove a mistaken self-created task without destroying its audit trail. Field evidence accepts normal browser GPS precision and returns safe validation errors instead of an internal error.

**Independent Test**: Create a self-assigned task with a free-text expected place, verify the form resets, soft-delete it as its Helpdesk creator, then complete another task using high-precision browser coordinates and verify either a known place or stored coordinates plus a Google Maps link is shown.

**Acceptance Scenarios**:

1. **Given** a creator enters an expected place outside the registered Location catalog, **When** the task is created, **Then** the exact normalized planning text is retained without creating or requiring a registered Location.
2. **Given** task creation succeeds, **When** the refreshed list is shown, **Then** all create-form fields are cleared while failed submissions retain user input.
3. **Given** a non-completed Task created and self-assigned by the current HELPDESK actor, **When** they delete it, **Then** it disappears from normal reads, remains durably retained, and one privacy-safe audit record is committed.
4. **Given** another person's, Manager-created, or completed Task, **When** HELPDESK requests deletion, **Then** it is denied with no Task or audit delta.
5. **Given** valid browser coordinates with up to 15 decimal places, **When** field completion is submitted, **Then** boundary validation accepts their supported precision and completion continues normally.
6. **Given** invalid protected GPS input, **When** validation fails, **Then** the API returns a canonical 400 response without coordinates, protected field names, or a secondary error-handler failure.
7. **Given** completion GPS does not resolve to a known Location name, **When** history is viewed, **Then** the stored coordinates, accuracy context, resolution label, and Google Maps action remain available.

### Edge Cases

- Duplicate assignee identifiers in one request resolve to one task-assignee relationship per user and do not create duplicate history.
- A Manager assignment may use a future `assigned_date`; it belongs to Upcoming until that local date arrives.
- Expected Location is nullable and is planning context only; it does not assign a user to a permanent workplace and does not affect attendance.
- An expected Location later becoming inactive does not rewrite the task's historical assignment date or assignees; behavior for changing that Location is outside this feature unless already governed by Location management rules.
- Leading and trailing whitespace does not satisfy the required reason for `BLOCKED`.
- Moving from `BLOCKED` to `IN_PROGRESS` ends the active block but preserves the prior block reason in lifecycle history.
- A completed task always belongs to Completed even when its assigned date would otherwise make it Overdue, Today, or Upcoming.
- A completed task remains readable but rejects every attempt to change status, content, expected Location, or assignees; corrections require a separately governed future workflow.
- Date classification and overdue days use the Asia/Ho_Chi_Minh business date, including reads around UTC/local-midnight boundaries.
- Concurrent ordinary status attempts serialize and re-evaluate the latest committed state: both may create ordered lifecycle updates when the resulting sequence is valid; otherwise the later request becomes a same-state no-op or is rejected without side effects. A completed task always rejects later transitions.
- Removing every assignee from a Manager-assigned task is rejected so every task retains at least one assignee.
- Account deactivation never removes old task-assignee relationships or silently reassigns work.
- A browser that denies location permission or cannot provide a fresh position cannot use FIELD_EVIDENCE; the UI explains the problem and Manager override remains a separately authorized fallback.
- Staged uploads that remain unbound for seven days expire and are cleaned with their private staging objects; cleanup must never delete an object already bound to a Task Photo.
- A local field-evidence draft is isolated by account and Task, expires seven days after its last edit, and is purged after verified finalize, explicit discard, logout, or account switch. Storage unavailability, quota exhaustion, or eviction must be shown truthfully; purge is best-effort and not an operating-system secure erase.
- A viewport as narrow as 360 CSS pixels must not require horizontal page scrolling; long titles and names wrap within their own cards.
- Deleting a self-created Task after it has completed is forbidden; evidence and terminal history remain readable.
- Free-text expected-place input is trimmed; whitespace-only input becomes absent and is never interpreted as a registered geofence.
- GPS validation diagnostics must not echo protected coordinate names or values.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow a MANAGER to create a task for one or more HELPDESK assignees.
- **FR-002**: A new task MUST contain a title, creator, `assigned_date`, at least one assignee, and initial status `TODO`; it MAY contain a description and one expected Location.
- **FR-003**: The system MUST allow `assigned_date` to be today, a past date, or a future date.
- **FR-004**: `assigned_date` MUST be immutable after task creation; no user action or scheduled process may overwrite it.
- **FR-005**: The system MUST allow a HELPDESK user with self-create authority to create an arising task for themselves.
- **FR-006**: A Helpdesk self-created arising task MUST set the authenticated user as both creator and sole initial assignee; the user MUST NOT use self-create to assign another person.
- **FR-006A**: Only a MANAGER with assignment authority MAY add, remove, or replace task assignees; `task.update.self` MUST NOT grant HELPDESK assignee-management authority even when creator-or-assignee scope succeeds.
- **FR-007**: The system MUST support multiple assignees on a single task while keeping one task-level status as the sole lifecycle source of truth.
- **FR-008**: The system MUST prevent duplicate relationships between the same task and assignee.
- **FR-009**: Every newly added assignee MUST be an active HELPDESK user at the time of assignment.
- **FR-010**: If any newly requested assignee ID is missing, inactive, or not a HELPDESK user, the entire create or assignment change MUST fail with `422 INACTIVE_ASSIGNEE`; `details.assignee_ids` MUST identify every violating ID in de-duplicated ascending order and no partial change may persist.
- **FR-010A**: Assignment eligibility MUST be revalidated while the relevant User rows are locked inside the Task write transaction, so concurrent deactivation or role change and assignment serialize and the later operation observes the committed account state.
- **FR-010B**: HELPDESK self-create MUST lock and re-authorize the actor inside the create transaction before self-assignment; a concurrently deactivated actor MUST receive `401 ACCOUNT_INACTIVE`, an actor whose changed role lost `task.create.self` MUST receive `403 PERMISSION_DENIED`, and neither failure may create Task data.
- **FR-011**: Deactivating a previously assigned user MUST NOT remove or alter any existing task-assignee relationship, task status, assigned date, list classification, or historical report result.
- **FR-012**: An edit to a non-completed task MUST validate only newly added assignees for active-account eligibility; a retained historical assignee who later became inactive MUST NOT block unrelated edits. FR-017 still rejects every edit after completion.
- **FR-013**: The system MUST use exactly four task states: `TODO`, `IN_PROGRESS`, `BLOCKED`, and `COMPLETED`.
- **FR-014**: The system MUST enforce the Canonical State Transition Matrix in this specification for every actor and every task scope.
- **FR-015**: A transition into `BLOCKED` MUST include a non-empty `block_reason` or note; whitespace-only content MUST be treated as missing, and rejection MUST leave state and history unchanged.
- **FR-016**: Resuming a `BLOCKED` task MUST transition the same task to `IN_PROGRESS`; the system MUST NOT create a replacement task.
- **FR-017**: `COMPLETED` MUST be terminal and fully read-only. No role, broad scope, ordinary update authority, retry, or concurrent request may change its status, title, description, expected Location, or assignees; rejected requests MUST create no business side effects, while reads and reports remain available.
- **FR-018**: After authorization, input validation, and object scope succeed, a request that names the current non-terminal state MUST return the current task successfully as a no-op and MUST NOT write the Task, create lifecycle history, create audit/outbox evidence, or change an aggregate version; a currently `BLOCKED` task MUST NOT require its reason to be resubmitted. A request naming `COMPLETED` on an already completed task MUST instead be rejected under FR-017.
- **FR-019**: Every successful state transition MUST retain the actor, resulting state, time, and applicable reason as append-only lifecycle history while updating the task's current state as the canonical snapshot.
- **FR-020**: Concurrent status requests MUST serialize on the Task and each MUST evaluate the latest committed state. A later request MUST commit with its own lifecycle update when its target remains a valid transition from that state, follow FR-018 when its target now equals that state, or be rejected without side effects when invalid or terminal; the system MUST NOT use unchecked last-write-wins or require a Task version in this feature.
- **FR-021**: Authorized task lists MUST classify each task into exactly one group using the current Asia/Ho_Chi_Minh date: Overdue for incomplete tasks before today, Today for incomplete tasks on today, Upcoming for incomplete tasks after today, and Completed for every `COMPLETED` task.
- **FR-022**: Task-list presentation MUST order Overdue before Today; each overdue task MUST display its original `assigned_date` and derived overdue days.
- **FR-023**: `overdue_days` MUST equal the current Asia/Ho_Chi_Minh date minus `assigned_date` at read time for Overdue tasks and MUST NOT be persisted or reported as positive for other groups.
- **FR-024**: Future tasks MUST NOT be counted as today's assigned or completed-work outcome merely because they already exist.
- **FR-025**: Self scope for task read and core update MUST mean the authenticated user is the task creator or an assignee.
- **FR-026**: A HELPDESK user MUST be denied task read or mutation when they are neither creator nor assignee.
- **FR-027**: A MANAGER with all-task read or any-task update authority MAY operate without creator/assignee scope, but MUST still satisfy assignment validation, the canonical state machine, terminal completion, and all other business invariants.
- **FR-028**: A LEADER MAY read all tasks but MUST be denied every task mutation, including creation, reassignment, status change, and completion.
- **FR-029**: Authorization MUST be enforced before task data is mutated; a rejected action MUST produce no task, assignment, lifecycle-history, or other business side effect.
- **FR-029A**: Task responses MUST represent creators, assignees, lifecycle actors, and completers with only `id` and `full_name`; they MUST NOT expose username or account-active state to roles that lack user-directory authority.
- **FR-030**: The expected task Location MUST remain optional planning information distinct from any actual completion evidence and MUST NOT be used as a permanent user work-location assignment or an attendance rule.
- **FR-031**: This feature MUST implement photo upload, fresh GPS capture, governed geofence resolution, and FIELD_EVIDENCE completion while retaining Manager override as a separate completion method.
- **FR-032**: Only a MANAGER with `task.complete.override` MAY use Manager override. The operation MUST require a non-empty `completion_note`, require neither creator/assignee scope nor GPS, reject photo and GPS input, record `MANAGER_OVERRIDE`, the completing Manager and server completion time, and atomically create the `COMPLETED` lifecycle update, Task completion snapshot, and AuditLog.
- **FR-032A**: The ordinary status operation MUST reject target `COMPLETED` for every actor and scope; allowed domain transitions into `COMPLETED` MUST be invoked only by an authorized completion workflow.
- **FR-032B**: An allowed transition into `COMPLETED` MUST succeed at most once; subsequent completion or transition attempts MUST be rejected without duplicate history or audit evidence.
- **FR-032C**: The completion AuditLog payload MUST contain only Task ID, previous/resulting status, completion method, completing actor ID, and server time; free-text `completion_note` MUST remain on Task/TaskUpdate and MUST NOT be copied, sanitized, or rejected through AuditLog payload filtering.
- **FR-033**: The core task write operations and their invariant-bound lifecycle history and audit evidence MUST succeed or fail together.
- **FR-034**: Tests MUST cover every allowed, rejected, and unchanged-state cell in the canonical matrix for applicable self and any-scope authorization, including `BLOCKED` reason validation and every attempted exit from `COMPLETED`.
- **FR-035**: FIELD_EVIDENCE completion MUST require `task.complete.field`, creator-or-assignee object scope, one to five verified photos, latitude, longitude, horizontal accuracy, and a client capture time; zero photos or more than five photos MUST be rejected. MANAGER broad update scope MUST NOT bypass the field-evidence relationship scope.
- **FR-036**: The client MUST convert a readable HEIC source to JPEG when needed, compress each image before upload, and accept only JPEG, PNG, or WebP output no larger than 5 MB per image. The backend MUST independently verify supported MIME, size, and SHA-256 checksum and MUST reject unreadable, unsupported, oversized, or mismatched objects.
- **FR-036A**: Each photo MUST use a private staging `EvidenceUpload` intent bound to exactly one authenticated actor and Task. Its presigned `PUT` MUST be limited to the declared key, MIME, checksum, and size and expire within 15 minutes; neither the URL nor a token may be persisted as business data. Creating or uploading an intent MUST NOT create `TaskUpdate` history or change Task status.
- **FR-037**: Finalization MUST revalidate object existence and metadata, checksum, MIME, size, upload owner, Task binding and creator-or-assignee scope, expiry/bound state, terminal Task state, photo count, and fresh valid GPS before committing. A staging upload MUST bind at most once and only to its declared actor and Task.
- **FR-037A**: FIELD_EVIDENCE MUST use a newly requested device sample with `maximumAge=0`; the server MUST reject a sample received more than 60 seconds after `captured_at`. Client capture time is retained only for audit/debug and MUST NOT replace server completion time.
- **FR-038**: FIELD_EVIDENCE finalization MUST atomically create exactly one append-only `COMPLETED` Task Lifecycle Update, one to five immutable Task Photos, the Task completion snapshot, all upload bindings, and invariant-bound audit evidence, or create none of them.
- **FR-039**: Finalization MUST require an idempotency key. The same key and normalized payload MUST return the original committed result; the same key with a different payload MUST return `409 IDEMPOTENCY_CONFLICT`; validation and Location-choice responses before commit eligibility MUST NOT consume the key.
- **FR-040**: Task GPS quality MUST be derived using only Task-specific configured thresholds as `GOOD`, `LOW_ACCURACY`, or `UNRELIABLE`. `LOW_ACCURACY` and `UNRELIABLE` MUST warn but MUST NOT block completion, run geofence matching, auto-assign a Location, or reuse Attendance's quality gate or threshold.
- **FR-041**: Only `GOOD` Task GPS MAY be compared with active Location geofences. Zero candidates MUST complete with `GPS_ONLY`; one candidate MUST resolve as `AUTO_SINGLE`; multiple candidates MUST return `409 LOCATION_CHOICE_REQUIRED` until the user selects a candidate that the backend recomputes and verifies, otherwise returning `422 INVALID_LOCATION_CHOICE`.
- **FR-041A**: Every committed Task Lifecycle Update with GPS MUST persist the complete Location-candidate ID snapshot calculated at completion time. The snapshot MUST be empty for non-`GOOD` GPS or zero candidates, contain the sole auto-selected candidate, and retain every candidate for `USER_SELECTED`; it MUST never be recalculated when Locations later change.
- **FR-042**: Evidence reads MUST expose stored capture coordinates, accuracy, quality, resolution method, selected Location when any, immutable Location candidates, and protected photo metadata without exposing object keys or presigned URLs in list/detail payloads. `resolved_address` MUST derive only from the selected Location's name and address and be null without a selected Location; no external reverse-geocoding call is allowed. `maps_url` MUST use the exact stored capture coordinates of that Task Lifecycle Update, never the selected Location coordinates.
- **FR-043**: Photo bytes MUST remain private. A photo access URL MUST be short-lived and issued only after `photo.view.self` creator-or-assignee scope or `photo.view.all` authorization succeeds.
- **FR-043A**: Image EXIF GPS MUST NOT be read, persisted, compared with device GPS, or used for Location resolution.
- **FR-043B**: Before finalization, the client MUST locally persist only the compressed photos and note in a namespace scoped by authenticated account and Task; the draft MUST contain no GPS sample, authentication token, upload token, object key, or presigned URL and MUST never be rendered for another account or Task.
- **FR-043C**: The client MUST purge the local draft after verified finalization, explicit discard, logout, account switch, seven days since the last edit, or the next confirmed account-state check after the account is disabled. It MUST report storage unavailability, quota failure, or eviction truthfully; this best-effort purge is not a secure erase guarantee.
- **FR-043D**: Unbound `EvidenceUpload` intents and their private staging objects MUST expire and be eligible for cleanup after seven days; cleanup MUST NOT delete or invalidate any object already bound to immutable Task Photo evidence.
- **FR-044**: Every existing application route MUST use a shared current-page header, role-appropriate navigation, reusable typography, form, card, badge, and action primitives, and consistent responsive content constraints.
- **FR-045**: At phone widths down to 360 CSS pixels and supported desktop widths, the shell, Tasks, Attendance, lists, forms, and cards MUST fit without horizontal page overflow; employee Tasks and Attendance destinations MUST both remain visible without horizontal scrolling.
- **FR-046**: Status values MUST use semantic badges, descriptions/supporting copy MUST use secondary typography, and form actions MUST be separated from inputs by reusable spacing rather than page-specific margins.
- **FR-047**: UI controls MUST preserve keyboard focus visibility, accessible labels, disabled/in-flight behavior, and minimum touch targets while wrapping long user-provided text inside its container.
- **FR-048**: Expected-place planning input MUST accept optional normalized free text independent of the registered Location catalog; catalog entries MAY be presented as suggestions but MUST NOT restrict creation or create a Location implicitly.
- **FR-049**: After a successful create response and list refresh, the create form MUST reset every control; validation/network failures MUST retain the entered values.
- **FR-050**: HELPDESK with `task.delete.self` MAY soft-delete only a non-completed Task for which they are the creator and sole assignee; MANAGER-created, other-user, and completed Tasks MUST be rejected without side effects.
- **FR-051**: Task deletion MUST retain all rows, set a server-owned deletion timestamp atomically with a privacy-safe AuditLog, and exclude the Task from normal list, detail, update, completion, upload, and photo-access scope.
- **FR-052**: FIELD_EVIDENCE latitude and longitude MUST accept finite browser measurements through 15 decimal places within canonical ranges and persist without unintended precision loss.
- **FR-053**: Validation of protected input MUST return a canonical `400 VALIDATION_FAILED` envelope whose details contain neither coordinate values nor protected field names; error-envelope construction MUST NOT raise a secondary exception.
- **FR-054**: Evidence history MUST always retain and present captured coordinates plus a safe Google Maps action. The link MUST preserve the exact stored coordinate values in `https://www.google.com/maps?q={latitude},{longitude}` and open with `rel="noopener noreferrer"`; it MUST not use a Location's coordinates, an embedded map, or an external map SDK.

### Authorization Matrix

| Capability | HELPDESK | MANAGER | LEADER |
|---|:---:|:---:|:---:|
| Create arising task for self | Allowed | Denied | Denied |
| Create and assign task to HELPDESK users | Denied | Allowed | Denied |
| Add, remove, or replace assignees | Denied | Allowed | Denied |
| Read task in self scope | Allowed | Allowed through all-task read | Allowed through all-task read |
| Read any task | Denied | Allowed | Allowed |
| Core update in self scope | Allowed | Allowed through any-task update | Denied |
| Core update on any task | Denied | Allowed | Denied |
| Complete with field evidence in creator/assignee scope | Allowed | Allowed | Denied |
| Complete through Manager override | Denied | Allowed | Denied |
| Soft-delete own mistaken self-created non-completed task | Allowed | Denied | Denied |

This table summarizes the applicable task-core capabilities. Field evidence and Manager override are separate completion operations.

### Key Entities *(include if feature involves data)*

- **Task**: A unit of planned or arising work. Key attributes are title, optional description, creator, immutable assigned date, current canonical status, optional expected Location, and completion snapshot fields populated only by an authorized completion workflow.
- **Task Assignee**: The historical relationship between one Task and one HELPDESK user, including when the assignment was made. It has no independent task status, remains present after account deactivation, and is unique per task and user.
- **Task Lifecycle Update**: Append-only evidence of a successful task-state change, including the task, actor, resulting status, time, optional note/block reason, GPS quality and resolution fields, and an immutable Location-candidate snapshot when the update completes field work.
- **Evidence Upload Intent**: A short-lived private staging reservation bound to one actor and Task, with declared MIME, size, SHA-256 checksum, expiry, and `ISSUED`/`UPLOADED`/`BOUND`/`EXPIRED` one-time binding state; it is not business completion evidence until finalized.
- **Task Photo**: One of one to five immutable metadata records that bind verified private JPEG, PNG, or WebP objects to one completed Task Lifecycle Update without exposing storage keys in ordinary Task responses.
- **Completion Idempotency Record**: The committed relationship between one actor-provided finalization key, its normalized request fingerprint, and the resulting completion update.
- **Local Field-Evidence Draft**: Best-effort client-only state containing compressed photos and a note, isolated by account and Task and governed by the purge rules in FR-043B–FR-043C.
- **User**: An authenticated MANAGER, HELPDESK, or LEADER whose role, active status, task relationship, and granted capability determine whether an operation is permitted.
- **Location**: An optional expected place for the task. It is planning context and is separate from actual completion evidence.
- **Task List Projection**: A read-time view that places an authorized task in Overdue, Today, Upcoming, or Completed and derives overdue days without persisting them.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In acceptance testing, a MANAGER can create a task with one or more active assignees and an optional expected Location in under 2 minutes without assistance.
- **SC-002**: In acceptance testing, a HELPDESK user can record an arising self-assigned task in under 1 minute without assistance.
- **SC-003**: One hundred percent of canonical state-matrix cases produce the specified allowed, rejected, or unchanged outcome for both applicable self-scope and Manager any-scope tests.
- **SC-004**: One hundred percent of attempts to enter `BLOCKED` without a meaningful reason are rejected without changing task state or history.
- **SC-005**: One hundred percent of mutation attempts against `COMPLETED`, including status, content, expected-Location, assignee, competing, and repeated requests, are rejected without changing the historical record or duplicating completion.
- **SC-006**: One hundred percent of create or assignment-change requests containing any missing, wrong-role, or inactive new assignee fail atomically with all violating IDs, while one hundred percent of pre-existing inactive-assignee relationships remain visible and unchanged.
- **SC-007**: For representative tasks spanning past, current, future, and completed dates, one hundred percent appear in exactly one correct list group and every overdue-day value matches the current Asia/Ho_Chi_Minh business date.
- **SC-008**: Across a simulated local-date change, zero task records have `assigned_date` modified while list classification and overdue days update correctly on the next read.
- **SC-009**: One hundred percent of tested HELPDESK access attempts outside creator-or-assignee scope are denied, and one hundred percent of LEADER mutation attempts are denied with no business side effects.
- **SC-010**: With the MVP population of approximately 50 users and representative task histories, at least 95% of authorized task-list reads present all four groups and derived values within 2 seconds.
- **SC-011**: In a usability review with at least 10 representative users, at least 9 correctly identify their overdue, today, upcoming, and completed work without assistance.
- **SC-012**: One hundred percent of tested FIELD_EVIDENCE completions either commit exactly one Task completion with all declared photos and GPS evidence or leave the Task and all business evidence unchanged.
- **SC-013**: In tested partial-upload failures, one hundred percent of already successful photos remain reusable and no successful photo is uploaded a second time unless the user explicitly replaces it.
- **SC-014**: Every existing route passes automated 360 px and 1280 px overflow, page-title, role-navigation, focus, label, and semantic-status checks with zero critical accessibility violations.
- **SC-015**: In acceptance testing, an authorized employee can select photos, capture position, resolve any Location choice, and submit field completion in under 3 minutes without assistance on a supported phone browser.
- **SC-016**: One hundred percent of tested free-text expected places, including values outside the registered catalog, are retained as planning text and do not alter Location configuration.
- **SC-017**: One hundred percent of successful creates clear the form, while failed creates retain input.
- **SC-018**: One hundred percent of deletion authorization cases either commit exactly one soft-delete plus audit record or leave all business and audit rows unchanged.
- **SC-019**: One hundred percent of tested high-precision valid GPS payloads avoid internal errors, and invalid protected payloads return canonical redacted 400 responses.
- **SC-020**: One hundred percent of the field-evidence validation matrix rejects zero or more than five photos, unsupported MIME, files over 5 MB, checksum mismatch, wrong owner or Task, expired or already-bound uploads, stale GPS, and invalid Location selection without partial business evidence.
- **SC-021**: One hundred percent of local-draft tests prove account-and-Task isolation, restore only compressed photos and note, contain no GPS/token/presigned URL, purge on every documented trigger, and report storage failure without claiming the draft was saved.
- **SC-022**: One hundred percent of Manager-override tests require a meaningful completion note, reject photo/GPS input, require Manager override authority, and atomically commit one distinct `MANAGER_OVERRIDE` completion and AuditLog.
- **SC-023**: One hundred percent of evidence-presentation tests derive `resolved_address` only from the selected Location and derive the Google Maps URL from the exact stored Task capture coordinates without external reverse geocoding or EXIF GPS.

## Assumptions

- The authoritative business rules are `docs/CHOT_YEU_CAU.md` §4, §6.1–§6.3, §8, §8.1, §9.2.2, and §10, followed by `docs/QUY_TAC_CLEAN_CODE.md`; the project constitution supplies global authorization, transaction, audit, architecture, storage, and test invariants.
- The existing identity and authorization foundation supplies authenticated roles, account active status, task permission actions, and the creator-or-assignee scope policy.
- A HELPDESK arising task is self-assigned on creation, only MANAGER may change its assignee set, and MANAGER creates only through assignment mode, per R-135/R-140.
- Every task has at least one assignee. Manager-created work may have one or many; Helpdesk self-created work begins with exactly the creator as assignee.
- Same-state requests follow the Task-specific idempotent no-op semantics in R-136.
- `assigned_date` is the single scheduling date; no separate due date, carried-over date, or nightly rollover field is introduced.
- Business-date calculations use Asia/Ho_Chi_Minh and server-authoritative time.
- Account deactivation is managed by the existing identity feature; this feature consumes that state but does not add account-management behavior.
- Photo/GPS `FIELD_EVIDENCE` is now in Feature 007 and invokes, rather than weakens or duplicates, the same terminal-state invariant as Manager override.
- Notifications and task reporting/export remain outside this feature. Protected photo access required to inspect completed Task evidence is included.
