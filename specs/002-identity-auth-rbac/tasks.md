---

description: "Implementation tasks for Identity, Authentication and Canonical RBAC"
---

# Tasks: Identity, Authentication and Canonical RBAC

**Input**: Design documents from `/specs/002-identity-auth-rbac/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Tests are mandatory for this security-sensitive feature. In each phase, add the listed test first, confirm that it fails for the prohibited or missing behavior, and then implement the corresponding behavior.

**Organization**: Shared architecture, policy, persistence, and audit foundations are completed first. The remaining tasks are grouped by the five P1 user stories and keep tests beside the behavior they verify.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Genuinely independent after the preceding phase checkpoint; it changes different files and does not depend on another incomplete task in the same phase.
- **[Story]**: User story traceability label used only in story phases.
- Every checklist item names the concrete files that own its verifiable outcome.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the approved module and dependency surface without introducing business behavior.

- [X] T001 Pin `djangorestframework-simplejwt==5.5.1` and regenerate the locked dependency graph without adding any other package in `backend/pyproject.toml` and `backend/uv.lock`
- [X] T002 [P] Create importable `identity` layer packages and Django app metadata in `backend/identity/__init__.py`, `backend/identity/apps.py`, `backend/identity/domain/__init__.py`, `backend/identity/application/__init__.py`, `backend/identity/ports/__init__.py`, and `backend/identity/adapters/{__init__.py,api/__init__.py,persistence/__init__.py,security/__init__.py}`
- [X] T003 [P] Create importable `audit` layer packages and Django app metadata in `backend/audit/__init__.py`, `backend/audit/apps.py`, `backend/audit/domain/__init__.py`, `backend/audit/application/__init__.py`, `backend/audit/ports/__init__.py`, and `backend/audit/adapters/{__init__.py,persistence/__init__.py}`
- [X] T004 [P] Add identity and audit test-package markers under `backend/tests/unit/{identity,audit}/`, `backend/tests/integration/api/identity/`, `backend/tests/integration/postgres/{identity,audit}/`, `backend/tests/contract/identity/`, `frontend/tests/unit/identity/`, and `frontend/tests/contract/identity/`

**Checkpoint**: Both approved business modules and all test locations are importable; no endpoint or schema has been implemented.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the canonical policy, model, transaction, error, audit/outbox, and composition foundations required by every story.

**Critical**: No user-story phase starts until this phase passes.

### Canonical domain and ports

- [X] T005 [P] Add failing parameterized tests for the three roles, 25 actions, exact direct-grant matrix, exactly five implication pairs, grant provenance, assignable roles, Leader mutation denial, and Manager check-in/out denial in `backend/tests/unit/identity/test_authorization.py`
- [X] T006 [P] Add failing boundary tests for trimmed nonblank account data and the 12-character/username-difference password rules in `backend/tests/unit/identity/test_accounts.py` and `backend/tests/unit/identity/test_passwords.py`
- [X] T007 Implement the closed `Role`, `PermissionAction`, direct grants, `PERMISSION_IMPLIES`, `ASSIGNABLE_ROLES`, effective capabilities, and `PermissionDecision.granted_by` required by T005 in `backend/identity/domain/authorization.py`
- [X] T008 Implement framework-free `AccountSnapshot` normalization and pure password rules required by T006 in `backend/identity/domain/accounts.py` and `backend/identity/domain/passwords.py`
- [X] T009 [P] Define typed request/result DTOs with a non-repr `GeneratedPasswordDisplayResult` and no refresh-token field in `backend/identity/application/dto.py`
- [X] T010 [P] Define user query/locking repository protocols in `backend/identity/ports/users.py` and password-hashing/validation protocols in `backend/identity/ports/credentials.py`
- [X] T011 [P] Define issue/rotate/revoke session protocols and canonical revocation reasons in `backend/identity/ports/sessions.py`
- [X] T012 [P] Define the caller-owned unit-of-work protocol covering user, blacklist, audit, and outbox changes in `backend/identity/ports/unit_of_work.py`
- [X] T013 [P] Add failing tests for immutable audit/event input models, closed identity vocabularies, allowed exact keys, forbidden nested secret/URL values, and path-only diagnostics in `backend/tests/unit/audit/test_records.py`
- [X] T014 Define immutable audit/outbox input types and the identity action/event vocabularies required by T013 in `backend/audit/domain/records.py`
- [X] T015 Define transaction-joining `append_audit_entry` and `append_outbox_event` protocols with no commit/publish surface in `backend/audit/ports/recording.py`

### Database schema and migration safety

- [X] T016 [P] Add failing model metadata tests for canonical User fields/defaults and the exact eight AuditLog fields in `backend/tests/unit/identity/test_model_contract.py` and `backend/tests/unit/audit/test_model_contract.py`
- [X] T017 Define the custom `AbstractBaseUser` model, manager, canonical fields, and password-hash-only persistence boundary in `backend/identity/models.py`
- [X] T018 Define `AuditLog` and `OutboxEvent` with only the approved columns, indexes, uniqueness, and check constraints in `backend/audit/models.py`
- [X] T019 Configure `AUTH_USER_MODEL`, installed auth/blacklist/identity/audit apps, DRF bearer authentication, and the single 15-minute/7-day rotation settings block in `backend/config/settings.py` and `backend/tests/unit/config/test_identity_settings.py`
- [X] T020 Add the additive User migration with nonblank/role checks, DDL defaults, exact username uniqueness, and a PostgreSQL username-immutability trigger in `backend/identity/migrations/0001_initial.py` and `backend/identity/migrations/__init__.py`
- [X] T021 Add the additive audit migration with swappable User dependency, audit indexes/immutability trigger, outbox checks/uniqueness/defaults, and pending-order index in `backend/audit/migrations/0001_initial.py` and `backend/audit/migrations/__init__.py`
- [X] T022 [P] Add failing PostgreSQL tests for User uniqueness, duplicate phone/email allowance, nonblank username/full_name, closed role, DDL defaults, and immutable username in `backend/tests/integration/postgres/identity/test_user_constraints.py`
- [X] T023 [P] Add real PostgreSQL tests for the database-backed AuditLog/OutboxEvent invariant set: eight-column AuditLog shape, update/delete rejection, protective actor FK, OutboxEvent checks/uniqueness/defaults/indexes, and a `transaction=True` competing-worker proof that concurrent events for one User allocate unique monotonically serialized aggregate versions and persist the expected final rows without mocks in `backend/tests/integration/postgres/audit/test_audit_outbox_constraints.py` and `backend/tests/integration/postgres/audit/test_aggregate_version_concurrency.py`
- [X] T024 Add a feature-001-to-feature-002 `MigrationExecutor` test proving additive compatibility, custom-user auth/blacklist foreign keys, and one local leaf per app in `backend/tests/integration/postgres/identity/test_migration_compatibility.py`
- [X] T025 Extend allowed migration owners from only operations to exactly operations/identity/audit while retaining leaf, DDL-default, and contraction checks in `scripts/migration_check.py` and `backend/tests/contract/test_migration_safety.py`

### Framework configuration, persistence, and canonical failures

- [X] T026 [P] Add the five identity error codes and centralized Vietnamese messages, preserving the canonical envelope and deprecated mirrors, in `backend/core/error_codes.py`, `backend/core/messages.py`, `backend/core/errors.py`, and `backend/tests/unit/core/test_identity_errors.py`
- [X] T027 Implement User snapshot/query/save/`SELECT FOR UPDATE` adapters and deterministic directory filtering/order in `backend/identity/adapters/persistence/users.py`
- [X] T028 [P] Implement Django password hashing/configured-validator adapters and security-grade generated-password retry logic in `backend/identity/adapters/security/passwords.py`
- [X] T029 Implement the Django atomic unit-of-work adapter without nested audit/outbox commits in `backend/identity/adapters/persistence/unit_of_work.py`
- [X] T030 Add failing persistence-adapter tests proving filtered AuditLog/OutboxEvent inserts, ambient correlation ownership, per-user aggregate ordering, and absence of `atomic()`/`on_commit()` in `backend/tests/unit/audit/test_recording_adapter.py`
- [X] T031 Implement audit/outbox append adapters required by T030 using `core.event_payload` in `backend/audit/adapters/persistence/recording.py`
- [X] T032 Add a PostgreSQL rollback test proving a rejected append or later exception removes User, blacklist, AuditLog, and OutboxEvent writes together in `backend/tests/integration/postgres/audit/test_atomic_recording.py`
- [X] T033 Define the typed identity service-container interface without constructing incomplete services or importing concrete adapters in `backend/identity/application/container.py`
- [X] T034 Extend architecture fixtures/checks to recognize only identity/audit/operations apps, classify business `models.py` as persistence boundaries, ban framework imports from domain, and enforce port-only cross-module imports in `scripts/check_architecture.py`, `backend/tests/architecture/test_django_app_registry.py`, `backend/tests/architecture/test_module_boundaries.py`, and `backend/tests/architecture/fixtures/module_boundaries/`
- [X] T035 Update scope-exclusion regressions so identity/audit are allowed owners while Identity is forbidden from calling or writing Task, Attendance, Reporting, location/config/photo, or other future business modules in `backend/tests/architecture/test_scope_exclusions.py` and `backend/tests/architecture/test_module_boundaries.py`

**Checkpoint**: Canonical policy and ports pass unit tests; additive migrations pass real-PostgreSQL invariant and compatibility tests; composition and architecture boundaries are ready for story work.

---

## Phase 3: User Story 1 — Sign In and Maintain a Revocable Session (Priority: P1) — MVP

**Goal**: Active users can log in, rotate a protected refresh credential, and globally revoke refresh sessions with current account state enforced on every request.

**Independent Test**: Log in, rotate twice, reject the consumed token, use two device cookies, log out once, and prove both refresh sessions are revoked while access-token behavior still follows expiry and current account gates.

### Tests for User Story 1

- [X] T036 [P] [US1] Add failing application tests for non-enumerating login, locked-user issuance, exact token claims, refresh rechecks/rotation, refresh failure with no replacement, and global logout revocation in `backend/tests/unit/identity/test_authentication_services.py`
- [X] T037 [P] [US1] Add failing controlled-time API tests for login success/failure equivalence, access success before and `INVALID_TOKEN` after the 15-minute boundary, protected 7-day cookie attributes, no JSON refresh, no-store headers, and current-role/capability responses in `backend/tests/integration/api/identity/test_login.py` and `backend/tests/integration/api/identity/test_access_expiry.py`
- [X] T038 [P] [US1] Add failing API tests for refresh success, rotation, missing/malformed/expired/signature-invalid/revoked/reused denies, JSON credential/body injection, inactive/forced-change outcomes, and no replacement cookie on failure in `backend/tests/integration/api/identity/test_refresh.py`
- [X] T039 [P] [US1] Add failing API tests proving logout requires same-user valid access plus valid refresh cookie, globally revokes two-device refresh sessions on success, returns `INVALID_TOKEN` with no success evidence for missing/malformed/expired/mismatched/already-revoked cookie or injected JSON body, clears client cookie as specified, issues no replacement, and leaves unexpired access usable in `backend/tests/integration/api/identity/test_logout.py`
- [X] T040 [P] [US1] Add a real PostgreSQL `transaction=True` competing-worker test proving at most one rotation succeeds for the same refresh credential and the consumed credential cannot become usable in `backend/tests/integration/postgres/identity/test_refresh_rotation_concurrency.py`
- [X] T041 [P] [US1] Add failing API tests proving every bearer request reloads current active/role state and returns `ACCOUNT_INACTIVE` immediately after deactivation in `backend/tests/integration/api/identity/test_account_state.py`

### Implementation for User Story 1

- [X] T042 [US1] Implement exact-claim SimpleJWT issuance, cookie-token parsing, one-time rotation, conflict-safe global blacklist insertion, and shared User-row locking in `backend/identity/adapters/security/sessions.py`
- [X] T043 [US1] Implement custom bearer authentication that validates access then reloads the authoritative User without trusting role/capability claims in `backend/identity/adapters/security/authentication.py`
- [X] T044 [US1] Implement login, refresh, and logout orchestration with current-state rechecks and no audit noise for login/routine refresh in `backend/identity/application/authentication.py`
- [X] T045 [US1] Implement login/refresh/logout serializers, same-user dual-credential logout validation, secure refresh-cookie helpers, canonical errors, and thin views in `backend/identity/adapters/api/serializers.py` and `backend/identity/adapters/api/views.py`
- [X] T046 [US1] Register exact slashless auth routes and explicit operation IDs beneath the single version prefix in `backend/identity/adapters/api/urls.py` and `backend/config/urls.py`
- [X] T047 [US1] Add logout session-revocation audit/outbox records with reason `LOGOUT` in the same unit of work in `backend/identity/application/authentication.py`

**Checkpoint**: US1 passes unit, API, and PostgreSQL race tests without relying on another business feature.

---

## Phase 4: User Story 2 — Complete a Required or Voluntary Password Change (Priority: P1)

**Goal**: Forced-change users can reach only password change; a successful self change revokes every old refresh session before issuing a replacement session.

**Independent Test**: Repeatedly log in with a generated password, verify all protected endpoints except change-password are blocked, change it successfully, reject every old refresh, and use the replacement session immediately.

### Tests for User Story 2

- [X] T048 [P] [US2] Add failing precedence tests proving unauthorized plus forced-change is `PERMISSION_DENIED`, authorized plus forced-change is `PASSWORD_CHANGE_REQUIRED`, unauthorized plus invalid payload is `PERMISSION_DENIED`, protected Manager target plus invalid payload is `PERMISSION_DENIED`, inactive authentication wins first, and all denied paths have zero side effects in `backend/tests/unit/identity/test_request_permissions.py` and `backend/tests/integration/api/identity/test_authorization_precedence.py`
- [X] T049 [P] [US2] Add failing application tests for actor-derived self reads/updates, server-owned identity rejection, password validation, failure atomicity, revoke-before-issue ordering, and audit/event payload minimization in `backend/tests/unit/identity/test_self_service.py`
- [X] T050 [P] [US2] Add failing API tests for `/me/` read/update success, Manager self-update allowance, `user_id`/username/server-owned denies, and authenticated-context targeting in `backend/tests/integration/api/identity/test_self_profile.py`
- [X] T051 [P] [US2] Add failing controlled-time API tests for repeated generated-password login, action-before-forced-change ordering, wrong-current/noncompliant password rollback, old access remaining usable until its original expiry, every old refresh being revoked, and the new access/refresh pair working immediately in `backend/tests/integration/api/identity/test_change_password.py`
- [X] T052 [P] [US2] Add a PostgreSQL test proving self password change atomically updates the hash/flag, revokes all prior refresh rows, appends consecutive audit/outbox versions, and issues only the new session in `backend/tests/integration/postgres/identity/test_password_change_transaction.py`

### Implementation for User Story 2

- [X] T053 [US2] Implement ordered authentication/action/target/forced-change permission adapters and the change-password exemption in `backend/identity/adapters/api/permissions.py`
- [X] T054 [US2] Implement actor-derived self profile query/update and password-change orchestration in `backend/identity/application/self_service.py`
- [X] T055 [US2] Add operation-specific self-profile/password serializers with server-owned-field precedence in `backend/identity/adapters/api/serializers.py`
- [X] T056 [US2] Add thin GET/PATCH `/me/` and POST `/change-password` views with exact route shapes and operation IDs in `backend/identity/adapters/api/views.py` and `backend/identity/adapters/api/urls.py`
- [X] T057 [US2] Record profile/password/session-revocation audit and outbox entries in the caller transaction without password/hash/token values in `backend/identity/application/self_service.py`

**Checkpoint**: US2 independently proves first-login enforcement, self ownership, failure rollback, and immediate replacement-session usability.

---

## Phase 5: User Story 3 — Administer Eligible User Accounts (Priority: P1)

**Goal**: Managers can list and mutate eligible Leader/Helpdesk accounts while Manager targets and Manager role assignment remain protected.

**Independent Test**: List every role/state, combine each supported filter, create/update/role/status/reset eligible users, and prove every Manager-target write loses before DTO validation with no state/audit/event side effect.

### Tests for User Story 3

- [X] T058 [P] [US3] Add failing query-service tests for unfiltered visibility, combined q/role/is_active filters, stable full_name/username/id order, fixed page size, and out-of-range page details in `backend/tests/unit/identity/test_user_queries.py`
- [X] T059 [P] [US3] Add failing application tests for create/profile/role/status/reset allow paths, nonassignable Manager role denial, Manager target recheck under lock, deactivation revocation, and audit/outbox rollback in `backend/tests/unit/identity/test_user_admin.py`
- [X] T060 [P] [US3] Add failing API tests for Manager list/detail success, inactive/Manager visibility, all valid filter combinations, invalid role/is_active/page inputs, pagination shape, invalid/nonexistent route user ids after action authorization, and Leader/Helpdesk denial without data disclosure in `backend/tests/integration/api/identity/test_user_queries.py`
- [X] T061 [P] [US3] Add failing API tests for create required fields, no default role, duplicate username, optional duplicate contacts, invalid email, unknown role syntax, `MANAGER` assignment denial, and server-owned-field failures with no partial evidence in `backend/tests/integration/api/identity/test_user_create.py`
- [X] T062 [P] [US3] Add failing API tests for eligible profile/role/status allow paths, invalid email, missing target after action authorization, and endpoint-specific forbidden/extra/empty/malformed/body-injection outcomes in `backend/tests/integration/api/identity/test_user_mutations.py`
- [X] T063 [P] [US3] Add failing API tests proving all four writes to existing Manager targets—including self-target, empty body, malformed body, and forbidden fields—return `PERMISSION_DENIED` before DTO validation with no success evidence in `backend/tests/integration/api/identity/test_manager_target_protection.py`
- [X] T064 [P] [US3] Add failing PostgreSQL tests proving one winner for concurrent duplicate usernames and rollback of the losing User/audit/outbox transaction in `backend/tests/integration/postgres/identity/test_concurrent_user_create.py`
- [X] T065 [P] [US3] Add failing PostgreSQL TOCTOU tests proving a concurrent promotion to Manager prevents a later profile/role/status/reset mutation after the locked target recheck in `backend/tests/integration/postgres/identity/test_manager_target_concurrency.py`
- [X] T066 [P] [US3] Add a real PostgreSQL `transaction=True` competing-worker test for login/session issuance racing with logout; assert final User/blacklist/audit/outbox state, no racing refresh escapes a completed logout, every revoked refresh is unusable, and an already-issued access credential retains only its canonical remaining lifetime in `backend/tests/integration/postgres/identity/test_login_vs_logout.py`
- [X] T067 [P] [US3] Add a real PostgreSQL `transaction=True` competing-worker test for login/session issuance racing with Manager password reset; assert final password/flag/blacklist/audit/outbox state, no racing refresh escapes a completed reset, every revoked refresh is unusable, and an already-issued access credential is constrained by the forced-password gate in `backend/tests/integration/postgres/identity/test_login_vs_password_reset.py`
- [X] T068 [P] [US3] Add a real PostgreSQL `transaction=True` competing-worker test for login/session issuance racing with self password change; assert final password/flag/blacklist/audit/outbox state, no old or racing refresh escapes completed revocation, old/racing access retains only its original lifetime, and the post-revocation replacement pair works in `backend/tests/integration/postgres/identity/test_login_vs_self_password_change.py`
- [X] T069 [P] [US3] Add a real PostgreSQL `transaction=True` competing-worker test for login/session issuance racing with account deactivation; assert final inactive User/blacklist/audit/outbox state, no issuance escapes completed deactivation, and every resulting credential is blocked by current account state in `backend/tests/integration/postgres/identity/test_login_vs_deactivation.py`
- [X] T070 [P] [US3] Add a real PostgreSQL `transaction=True` competing-worker test for refresh issuance racing with logout; assert final blacklist/audit/outbox state, no replacement refresh escapes a completed logout, every revoked old or racing refresh is unusable, and any already-issued access retains only its canonical remaining lifetime in `backend/tests/integration/postgres/identity/test_refresh_vs_logout.py`
- [X] T071 [P] [US3] Add a real PostgreSQL `transaction=True` competing-worker test for refresh issuance racing with Manager password reset; assert final password/flag/blacklist/audit/outbox state, no replacement refresh escapes a completed reset, every revoked old or racing refresh is unusable, and any already-issued access is constrained by the forced-password gate in `backend/tests/integration/postgres/identity/test_refresh_vs_password_reset.py`
- [X] T072 [P] [US3] Add a real PostgreSQL `transaction=True` competing-worker test for refresh issuance racing with self password change; assert final password/flag/blacklist/audit/outbox state, no old or racing refresh escapes completed revocation, already-issued access retains only its original lifetime, and the post-revocation replacement pair works in `backend/tests/integration/postgres/identity/test_refresh_vs_self_password_change.py`
- [X] T073 [P] [US3] Add a real PostgreSQL `transaction=True` competing-worker test for refresh issuance racing with account deactivation; assert final inactive User/blacklist/audit/outbox state, no rotation escapes completed deactivation, and every resulting credential is blocked by current account state in `backend/tests/integration/postgres/identity/test_refresh_vs_deactivation.py`
- [X] T074 [P] [US3] Add a real PostgreSQL `transaction=True` competing-worker test for simultaneous global revocations of one User; assert both workers serialize safely, the final blacklist covers every outstanding refresh exactly once, persisted evidence satisfies database uniqueness/ordering, and no revoked credential is usable without inventing an unspecified duplicate-success or idempotency contract in `backend/tests/integration/postgres/identity/test_concurrent_global_revocation.py`

### Implementation for User Story 3

- [X] T075 [US3] Implement list/detail query services with optional filters, deterministic ordering, fixed page pagination, and canonical invalid-page mapping in `backend/identity/application/queries.py`
- [X] T076 [US3] Implement create/profile/role/status/reset application services with assignable-role policy, Manager target recheck under lock, narrow field ownership, deactivation revocation, and one UoW per mutation in `backend/identity/application/user_admin.py`
- [X] T077 [US3] Add list/filter and operation-specific admin serializers that reject server-owned fields before allowed-field validation in `backend/identity/adapters/api/serializers.py`
- [X] T078 [US3] Add action-before-DTO and route-target Manager guards to admin views without reading request bodies in `backend/identity/adapters/api/permissions.py` and `backend/identity/adapters/api/views.py`
- [X] T079 [P] [US5] Add backend API/capability agreement tests proving login and `/me/` effective strings match the pure T005 policy matrix for all roles, unknown future strings remain schema-compatible, and direct unauthorized identity requests remain denied in `backend/tests/integration/api/identity/test_capability_agreement.py`
- [X] T080 [US3] Register the seven exact user-admin operations with explicit stable operation IDs in `backend/identity/adapters/api/urls.py`
- [X] T081 [US3] Append minimal create/profile/role/status/reset and deactivation-session audit/outbox evidence, including consecutive aggregate versions, in `backend/identity/application/user_admin.py`

**Checkpoint**: US3 independently supports the complete Manager directory workflow and closes payload, target, uniqueness, and deactivation races.

---

## Phase 6: User Story 4 — Receive a Generated Password Exactly Once (Priority: P1)

**Goal**: Create/reset returns server-generated plaintext only in its immediate response/UI state and nowhere recoverable afterward.

**Independent Test**: Capture create/reset responses, dismiss the dialog, then prove subsequent reads, audit/outbox rows, exceptions, logs, browser storage, and rendered UI contain no plaintext or credential material.

### Tests for User Story 4

- [X] T082 [P] [US4] Add failing backend tests proving create/reset reject client passwords, `GeneratedPasswordDisplayResult` is non-repr and response-only, repeated login has no generated-password TTL, and plaintext is absent from reads/logs/errors/audit/outbox in `backend/tests/unit/identity/test_generated_password.py` and `backend/tests/integration/api/identity/test_generated_password_security.py`
- [X] T083 [P] [US4] Add failing API reset tests for empty-body ownership, immediate single-display response, must-change flag, all-device revocation, residual access gating, and the authoritative rule that a deliberate later reset generates a new replacement while no retry/idempotency-key recovery is promised in `backend/tests/integration/api/identity/test_reset_password.py`
- [X] T084 [P] [US4] Add failing frontend lifecycle tests proving plaintext exists only in dialog component state and clears on dismiss, unmount, logout, and account switch in `frontend/tests/unit/identity/generated-password-dialog.test.tsx`

### Implementation for User Story 4

- [X] T085 [US4] Restrict create/reset response serialization to dedicated generated-password result schemas and exclude the value from all ordinary user serializers in `backend/identity/adapters/api/serializers.py`
- [X] T086 [US4] Implement the response-scoped generated-password dialog with explicit clearing at every lifecycle boundary in `frontend/src/features/identity/ui/GeneratedPasswordDialog.tsx`
- [X] T087 [US4] Connect only immediate create/reset results to the generated-password dialog without placing plaintext in directory/auth/error state in `frontend/src/features/identity/ui/UserEditor.tsx` and `frontend/src/features/identity/ui/UserDirectory.tsx`

**Checkpoint**: US4 proves exactly-once display and zero recoverable plaintext across backend and frontend boundaries.

---

## Phase 7: User Story 5 — Enforce Canonical Role Capabilities and Permission Provenance (Priority: P1)

**Goal**: Backend and frontend use the effective canonical action map while generic permission decisions retain grant provenance, deny unauthorized/malformed identity requests before validation, and leave record ownership to the owning features.

**Independent Test**: Execute the entire direct/effective Role × Action matrix, five implications, grant-provenance and malformed-body precedence cases; prove that Identity exposes no Task/Attendance ownership helper or endpoint, compare frontend controls to backend capabilities, and keep forged identity requests denied.

### Tests for User Story 5

- [X] T088 [P] [US5] Add generic provenance tests proving direct-self and implied all/any decisions report the correct `granted_by`, exactly five implications open a gate, and no Task creator/assignee or Attendance ownership semantics exist in Identity in `backend/tests/unit/identity/test_permission_provenance.py` and `backend/tests/architecture/test_scope_exclusions.py`
- [X] T089 [P] [US5] Add identity-owned API precedence tests proving Leader and Helpdesk user-administration denies beat forced-change and malformed bodies with no user/audit/outbox side effects; verify Manager check-in/out and other future actions only through the pure policy matrix, without calling nonexistent Task/Attendance endpoints, in `backend/tests/integration/api/identity/test_authorization_matrix.py`
- [X] T090 [P] [US5] Add frontend tests for unknown-capability tolerance, exact-string capability controls, no role hierarchy inference, hidden Leader/Helpdesk admin entry, and disabled Manager-target mutations in `frontend/tests/unit/identity/capabilities.test.tsx`

### Implementation for User Story 5

- [X] T091 [US5] Expose sorted effective capability strings from login and self-user presenters while retaining `granted_by` only in backend decisions in `backend/identity/adapters/api/serializers.py`
- [X] T092 [US5] Wire the completed repositories, security adapters, unit of work, audit/outbox ports, and authentication/self/admin/query services into the typed container and injected identity route factory in `backend/config/composition.py`
- [X] T093 [US5] Implement capability-based route/action presentation without client-side role inheritance in `frontend/src/features/identity/model/AuthProvider.tsx` and `frontend/src/features/identity/ui/UserDirectory.tsx`

**Checkpoint**: US5 proves canonical authorization, denial precedence, generic permission provenance, and explicit owning-feature scope deferral without implementing out-of-scope business modules.

---

## Phase 8: API Contract and Frontend Integration

**Purpose**: Publish the generated additive contract and connect all five completed stories through the existing frontend transport.

- [X] T094 [P] Add failing backend contract tests for all 13 operation IDs, exact mixed trailing-slash paths, logout requiring same-user bearer access plus refresh cookie and using `INVALID_TOKEN` for every invalid-cookie variant, request/response/status schemas, bearer security, cookie descriptions, open-string role/capabilities, and canonical errors in `backend/tests/contract/identity/test_api_contract.py`
- [X] T095 [P] Extend the OpenAPI safety test and fixtures so exact structural `password` is permitted only in the login request while JSON refresh, credential examples, generated password outside create/reset success, and secret audit/event fields remain forbidden in `scripts/check_openapi.py`, `backend/tests/contract/test_openapi_safety.py`, and `backend/tests/contract/fixtures/openapi/`
- [X] T096 Annotate identity views/serializers to satisfy T094–T095, deterministically regenerate only `contracts/openapi.yaml` and `frontend/src/shared/api/schema.ts`, and type/static-check the handwritten thin `frontend/src/shared/api/client.ts` without listing it as generated output
- [X] T097 [P] Add frontend contract tests for generated identity operations, snake_case fields, error unions, and absence of JSON refresh/generated-secret leakage in `frontend/tests/contract/identity/api-client.test.ts`
- [X] T098 Preserve incoming slash shape in the same-origin proxy and pin slashless auth/change-password plus slashed me/users forwarding without POST redirects in `frontend/next.config.ts` and `frontend/tests/architecture/origin-proxy-boundary.test.ts`
- [X] T099 Add failing transport tests for in-memory bearer injection, cookie inclusion, one shared refresh across ten simultaneous failures, one replay maximum, endpoint recursion exclusions, and hard stops for inactive/forced/permission/validation errors in `frontend/tests/unit/identity/authenticated-fetch.test.ts`
- [X] T100 Extend the sole approved transport with memory-token hooks, single-flight refresh, and one-replay behavior required by T099 in `frontend/src/shared/transport/authenticated-fetch.ts`
- [X] T101 [P] Add canonical identity code parsing and user-facing messages with request-id preservation in `frontend/src/shared/errors/api-error.ts`, `frontend/src/shared/messages.ts`, `frontend/tests/unit/errors/api-error.test.ts`, and `frontend/tests/unit/messages.test.ts`
- [X] T102 Create typed API wrappers for login/refresh/logout/self/password and every distinct user-admin operation over the handwritten shared client and generated schema in `frontend/src/features/identity/api/identity-api.ts`
- [X] T103 Add failing session-store/provider tests for refresh-then-me bootstrap, anonymous/inactive/forced/authenticated states, memory-only data, logout/account-switch clearing, and no refresh loop in `frontend/tests/unit/identity/auth-provider.test.tsx`
- [X] T104 Implement the in-memory session store and AuthProvider state machine required by T103 in `frontend/src/features/identity/model/session-store.ts` and `frontend/src/features/identity/model/AuthProvider.tsx`
- [X] T105 [P] Add frontend behavior tests for login and change-password forms, field errors, forced-change routing, replacement access, and unavailable business UI during forced change in `frontend/tests/unit/identity/auth-forms.test.tsx`
- [X] T106 Implement login/change-password pages and forms using the typed identity wrappers, AuthProvider, AsyncState, and canonical errors in `frontend/src/app/login/page.tsx`, `frontend/src/app/change-password/page.tsx`, `frontend/src/features/identity/ui/LoginForm.tsx`, and `frontend/src/features/identity/ui/ChangePasswordForm.tsx`
- [X] T107 [P] Add frontend directory tests for unfiltered visibility, filter/page state, distinct mutations, Manager-target controls, denied errors, and generated-password handoff in `frontend/tests/unit/identity/user-directory.test.tsx`
- [X] T108 Implement the capability-guarded user directory page, filters, and distinct mutation controls required by T107 in `frontend/src/app/users/page.tsx`, `frontend/src/features/identity/ui/UserDirectory.tsx`, and `frontend/src/features/identity/ui/UserEditor.tsx`

**Checkpoint**: Generated backend/OpenAPI/frontend contracts agree; every UI call uses the existing authenticated transport and holds credentials only in approved memory/cookie channels.

---

## Phase 9: Polish and Cross-Cutting Verification

**Purpose**: Integrate the feature into repository-wide architecture, migration, static, security, and CI gates.

- [X] T109 [P] Document identity/audit ownership, action-before-forced-change ordering, generic permission provenance, Feature 004/006 scope deferrals, transaction boundaries, and outbox relay exclusion in `docs/ARCHITECTURE.md`
- [X] T110 [P] Expand authored-path formatting, Ruff, mypy, maintainability, architecture, migration, PostgreSQL, frontend, and generated-contract commands in `scripts/check_all.sh` and `.pre-commit-config.yaml`
- [X] T111 Extend the existing quality workflow to install the locked dependency and run identity/audit unit, API, PostgreSQL invariant/concurrency, migration, architecture, lint, mypy, frontend test/type/build, and secret-safety gates in `.github/workflows/quality.yml`
- [X] T112 Extend the existing contract workflow to run deterministic OpenAPI/generated-schema generation, handwritten-client type/static verification, identity contract/safety tests, drift checks, and merge-base compatibility in `.github/workflows/contract.yml`
- [X] T113 [P] Add contract assertions that Feature 002-owned artifacts, dependency lock, workflow changes, and quickstart contain no unapproved infrastructure, feature-owned unresolved marker, secret example, or out-of-scope relay/Task/Attendance behavior without scanning unrelated Constitution metadata in `backend/tests/contract/identity/test_delivery_contract.py`
- [X] T114 Execute and record a reproducible Manager happy-path usability session proving create, search/filter, eligible profile/role/status change, and password reset each complete within two minutes in `specs/002-identity-auth-rbac/evidence/usability.md` without recording generated plaintext
- [X] T115 Run the existing approved capacity tool with at least 50 test identities and concurrency 20, record measured p95 evidence without credentials in `specs/002-identity-auth-rbac/evidence/capacity.md`, and keep the real measurement outside CI
- [X] T116 Run the focused unit/API/PostgreSQL/frontend commands from `specs/002-identity-auth-rbac/quickstart.md` and record any reproducible command correction in that same file without weakening an assertion
- [X] T117 Run `scripts/migration_check.py check`, the feature-001-to-feature-002 PostgreSQL migration suite, and generated OpenAPI/schema drift plus compatibility checks; resolve every failure only in its owning migration/test/generator file
- [X] T118 Run the complete `scripts/check_all.sh` gate and verify formatting, lint, mypy, maintainability, unit/integration/contract tests, all enumerated PostgreSQL races, architecture, frontend type/test/build, migration safety, and sensitive-output scans are green

---

## Dependencies and Execution Order

### Phase dependencies

- **Phase 1 — Setup**: Starts immediately.
- **Phase 2 — Foundational**: Depends on Phase 1 and blocks all stories.
- **US1 (Phase 3)**: Depends only on the foundational phase; it is the suggested backend MVP.
- **US2 (Phase 4)**: Depends on US1 session issuance/revocation because successful password change replaces the session.
- **US3 (Phase 5)**: Depends on the foundation and US1 global revocation adapter; its directory/query work can begin once those interfaces are stable.
- **US4 (Phase 6)**: Depends on US3 create/reset responses and the generated-password result boundary.
- **US5 (Phase 7)**: Its matrix/scope tests depend only on the foundational policy, but final API/frontend evidence depends on US1–US3 presenters and permissions.
- **Phase 8 — Contract/frontend integration**: Depends on all desired story behavior and schemas.
- **Phase 9 — Polish/verification**: Depends on the implemented scope selected for delivery; T114–T115 are human-triggered evidence tasks and not CI gates, then T116–T118 run sequentially.

### Within each story

1. Add each listed failing test before its corresponding production behavior.
2. Complete pure application behavior before HTTP/UI adapters.
3. Establish database constraints and locking before claiming concurrency guarantees.
4. Keep action and Manager-target authorization before the forced-password gate and serializer construction; owning Feature 004/006 modules enforce their object scope after typed DTO validation.
5. Commit state, blacklist, audit, and outbox in one UoW; assert absence of side effects on every deny/rollback path.
6. Regenerate OpenAPI and `schema.ts` only after backend annotations and runtime behavior are stable; type/static-check the handwritten `client.ts`.

### User-story completion order

```text
Setup -> Foundation -> US1 -> US2
                       |
                       +-> US3 -> US4
Foundation -> US5 tests; US1-US3 -> US5 integration
US1-US5 -> Contract/frontend integration -> Repository gates
```

## Parallel Opportunities

- In Setup, T002–T004 touch independent module/test package trees after T001.
- In Foundation, pure policy/account/audit tests (T005, T006, T013), port definitions (T009–T012), model contract tests (T016), and PostgreSQL tests (T022–T023) can be prepared independently where their preceding contracts exist.
- US1 test files T036–T041 are independent specifications after Foundation; implementations T042–T047 then follow their dependency order.
- US2 tests T048–T052 can be authored in parallel after US1; implementation remains ordered permission → service → serializer/view → evidence.
- US3 tests T058–T065 cover independent query, HTTP, and PostgreSQL mechanisms; T066–T074 provide one real PostgreSQL competing-worker outcome per claimed issuance/revocation or concurrent-global-revocation invariant after all involved service interfaces are known and before T075–T081 make them pass. T023 separately includes the per-User aggregate-version competing-worker proof. T079 is the independent API/capability agreement test unlocked by the earlier authentication presenters and intentionally remains distinct from T005's pure policy matrix.
- US4 backend, reset API, and frontend lifecycle tests T082–T084 are independent once US3 schemas exist.
- US5 API agreement T079 and provenance/API-deny/frontend tests T088–T090 can be authored independently after their stated presenter prerequisites.
- Contract tests T094–T095 and frontend error/behavior tests marked `[P]` can proceed in parallel before their owning implementations; generated artifacts T096 remain a single deterministic step.
- Documentation and gate configuration T109–T113 touch separate concerns; usability/capacity evidence T114–T115 remains operator-run, and final validation T116–T118 is intentionally sequential.

## Parallel Examples

### User Story 1

```text
T036 application orchestration tests
T037 login HTTP contract tests
T038 refresh deny/rotation HTTP tests
T039 logout multi-device HTTP tests
T040 PostgreSQL rotation/revocation race tests
T041 per-request current-account tests
```

### User Story 3

```text
T058 directory query unit tests
T060 list/detail API tests
T063 Manager-target precedence API tests
T064 duplicate-username PostgreSQL race test
T065 Manager-target PostgreSQL TOCTOU test
T066–T074 one task per issuance-versus-revocation/global-revocation PostgreSQL race
```

### User Story 5

```text
T079 API/capability agreement against the pure T005 RBAC matrix
T088 generic permission provenance and ownership-exclusion proof
T089 identity-owned API deny/side-effect matrix
T090 frontend capability presentation
```

## Implementation Strategy

### MVP first

1. Complete Setup and Foundational phases.
2. Complete US1 through T047.
3. Stop and validate login, rotation/reuse denial, multi-device logout, current-account checks, cookie security, and PostgreSQL races.
4. This is the smallest trustworthy session MVP; it does not yet satisfy the complete feature Definition of Done.

### Incremental delivery

1. Add US2 to close the forced/generated-password login loop.
2. Add US3 for Manager directory and eligible account administration.
3. Add US4 for exactly-once generated-password delivery.
4. Complete US5 authorization/provenance evidence and scope-deferral boundary proof.
5. Complete generated contracts/frontend integration and all repository gates before declaring feature 002 done.

## Notes

- `[P]` never means “no dependency”; it means independent after its phase prerequisites are complete and safe to execute concurrently with the adjacent marked tasks.
- PostgreSQL tests must assert the PostgreSQL vendor and use real competing transactions/workers; SQLite or mocks are not evidence for constraints, locking, rollback, or races.
- Deny tests assert both the canonical response and absence of user, blacklist, audit-success, outbox, cookie, or plaintext side effects as applicable; Attendance/Task side effects are not asserted until their owning features exist.
- Feature 002 introduces no idempotency-key contract or automatic mutation retry. Each deliberate successful reset is a new reset; invalid/revoked-cookie logout fails without success evidence; other repeated state requests retain only semantics explicitly defined by CHOT.
- `contracts/openapi.yaml` and generated `frontend/src/shared/api/schema.ts` are regenerated, never hand-edited; `frontend/src/shared/api/client.ts` remains handwritten and type/static checked.
- Feature 002 ends with durable PENDING outbox rows; relay, broker, retry, publishing, and dead-letter execution remain out of scope.

## Phase 10: Convergence

**Purpose**: Close implementation gaps found by the post-implementation consistency audit. Tasks are ordered so enforcement foundations precede production refactors and the final repository gate.

- [X] T119 Correct `scripts/check_architecture.py` to distinguish same-module imports from forbidden cross-module internal imports, add positive and negative production-owner cases in `backend/tests/architecture/test_module_boundaries.py`, and make that test scan the real `backend/identity`, `backend/audit`, and `backend/config` trees so Constitution II violations fail against production code rather than fixtures alone
- [X] T120 Refactor production identity wiring until T119 passes: move audit command/input types behind `audit/ports/recording.py`, remove identity application imports of `audit.domain.records`, inject the typed container and target lookup at the identity route composition boundary instead of importing `config.composition` or `identity.models` from API adapters, and remove the sibling persistence-adapter import from `backend/identity/adapters/security/sessions.py`; retain behavior with focused unit/API tests beside the affected services and adapters
- [X] T121 [P] Enforce the complete protected audit/outbox payload contract in `backend/core/event_payload.py` by rejecting every exact secret key required by `contracts/events.md`, nested occurrences in maps/lists, and any string value containing `://` while preserving allowed exact keys such as `must_change_password` and session counts; extend `backend/tests/unit/core/test_event_payload.py`, `backend/tests/unit/audit/test_records.py`, and `backend/tests/integration/postgres/audit/test_atomic_recording.py` to assert path-only failures and whole-transaction rollback
- [X] T122 [P] Normalize blank optional `phone` and `email` inputs to database `NULL` across create, self-profile update, and Manager profile update in the owning DTO/application boundary, and prove create/update/read behavior plus invalid-email rejection in the corresponding identity unit and API tests
- [X] T123 Replace generic evidence copying with operation-specific audit and outbox builders in `backend/identity/application/authentication.py`, `backend/identity/application/self_service.py`, and `backend/identity/application/user_admin.py` so every create/profile/role/status/reset/password/session record exactly matches `contracts/events.md`, contains required `user_id`, before/after and reason/count fields, omits contact/generated-secret data from outbox payloads, and commits atomically; assert exact payload equality and rollback in unit and PostgreSQL integration tests
- [X] T124 Remove the unapproved PostgreSQL advisory-lock aggregate allocator from `backend/audit/adapters/persistence/recording.py` and allocate each next per-User `aggregate_version` only while the caller holds that User row lock as required by `plan.md`; rewrite `backend/tests/integration/postgres/audit/test_aggregate_version_concurrency.py` to drive real identity application services against a persisted User with competing workers and assert unique strictly consecutive versions and complete final rows
- [X] T125 [P] Complete the raw PostgreSQL invariant proof for `audit_outboxevent` in `backend/tests/integration/postgres/audit/test_audit_outbox_constraints.py`: bypass ORM defaults where necessary, assert DDL defaults for `schema_version`, `request_id`, `correlation_id`, and `publish_state`, prove unique `event_id`, retain positive/check/aggregate uniqueness and pending-index assertions, and add a migration only if the authoritative DDL is missing an asserted invariant
- [X] T126 Restore the canonical logout pipeline in `backend/identity/adapters/api/permissions.py`, `backend/identity/adapters/api/views.py`, and the logout service so same-user refresh-cookie target authorization and action RBAC precede body validation, the forced-password gate follows authorization and precedes execution, and logout is not password-change exempt; add API precedence cases for forced/unauthorized actors combined with missing, malformed, mismatched, revoked cookies and injected/invalid bodies, asserting canonical errors and no success evidence
- [X] T127 Route every user-admin target through authentication, action RBAC, Manager-target authorization, and only then integer identifier validation by replacing the early `<int:user_id>` conversion in `backend/identity/adapters/api/urls.py` with an injected raw-target guard; extend `backend/tests/integration/api/identity/test_user_admin_precedence.py` and list/detail contract tests for malformed and nonexistent IDs across detail/profile, role, status, and reset operations for unauthenticated, LEADER, HELPDESK, and MANAGER actors, including no-side-effect assertions
- [X] T128 [P] Clear the refresh cookie on successful logout with the same `Secure`, `HttpOnly`, `SameSite=Strict`, and `/api/v1/auth/` path attributes used when setting it in `backend/identity/adapters/api/views.py`, and pin the exact `Set-Cookie` contract in `backend/tests/integration/api/identity/test_logout.py` and `backend/tests/contract/identity/test_api_contract.py`
- [X] T129 Expand `backend/tests/integration/postgres/identity/test_manager_target_concurrency.py` into real competing-worker tests for profile, role, status, and password-reset mutations racing with target promotion to MANAGER; invoke production services and assert the promoted account is never mutated and no password, blacklist, audit, or outbox side effect escapes a completed protection transition
- [X] T130 Replace the manual state mutation in `backend/tests/integration/postgres/identity/session_race_helpers.py` and the eight `test_login_vs_*` / `test_refresh_vs_*` modules with production-service competing-worker races for logout, Manager reset, self password change, and deactivation; for every pair assert final User/password/active/forced-change state, blacklist rows, exact audit/outbox rows, no refresh issuance survives completed global revocation, surviving credentials obey current-account gates, and already-issued access tokens retain only the canonical expiry behavior
- [X] T131 Make failed refresh observable to the session state machine in `frontend/src/shared/transport/authenticated-fetch.ts` and `frontend/src/features/identity/model/AuthProvider.tsx`: one failed/reused refresh transitions to anonymous, `ACCOUNT_INACTIVE` transitions to inactive, and `PASSWORD_CHANGE_REQUIRED` transitions to forced-change without retry loops; cover single-flight concurrent failures, one notification, token clearing, and account-switch isolation in `frontend/tests/unit/identity/authenticated-fetch.test.ts` and `frontend/tests/unit/identity/auth-provider.test.tsx`
- [X] T132 Add a capability/session route boundary for `/login`, `/change-password`, and `/users` so anonymous-only login, authenticated change-password, `user.view` directory access, forced-change routing, and inactive lockout are enforced before business UI renders or list APIs fire; implement it in the identity provider/page boundary and prove redirect/render/no-request behavior in `frontend/tests/unit/identity/auth-provider.test.tsx`, `frontend/tests/unit/identity/auth-forms.test.tsx`, and `frontend/tests/unit/identity/user-directory.test.tsx`
- [X] T133 Integrate `parseApiFailure`, centralized `UI_MESSAGES`, field-detail binding, and request-id presentation into `frontend/src/features/identity/ui/LoginForm.tsx`, `ChangePasswordForm.tsx`, `UserDirectory.tsx`, `UserEditor.tsx`, and their typed API calls; add frontend behavior tests for canonical auth, permission, validation, protected-target, inactive, and forced-password errors without generic fallback replacing known semantics
- [X] T134 Replace the `window.prompt` profile mutation in `frontend/src/features/identity/ui/UserDirectory.tsx` with the existing typed `UserEditor` form pattern for `full_name`, optional `phone`, and optional `email`, preserve distinct role/status/reset actions and generated-password handoff, and extend `frontend/tests/unit/identity/user-directory.test.tsx` for happy paths, blank-to-null contacts, invalid email, cancellation, Manager-target disabled controls, and server denial
- [X] T135 Extend `.github/workflows/quality.yml`, `.pre-commit-config.yaml`, and `scripts/check_all.sh` so the owner-aware production architecture scan, maintainability check, migration safety, identity contract/secret-safety tests, all enumerated PostgreSQL races, frontend tests/type/build, and generated-contract drift are actually invoked by their documented gates; update `backend/tests/contract/test_workflow_contract.py` and `backend/tests/contract/test_precommit_contract.py` to fail when any required command is removed
- [X] T136 Run the complete Feature 002 verification after T119–T135: focused unit/API tests after each owning change, all PostgreSQL constraint/atomicity/concurrency tests with `transaction=True` where specified, backend format/Ruff/mypy/maintainability/architecture, migration and OpenAPI/schema compatibility checks, frontend tests/type/build, and finally `scripts/check_all.sh`; do not mark this task complete unless every gate exercises production paths and passes

### Convergence requirement mapping

- **Constitution II / XI and plan architecture gates**: T119–T120, T135–T136.
- **Constitution VI and FR-028 safe, minimal, atomic evidence**: T121, T123–T125.
- **FR-015, FR-034, FR-035 and canonical authorization precedence**: T126–T128.
- **FR-023 protected MANAGER target behavior**: T127, T129.
- **FR-043 PostgreSQL serialization proof**: T124–T125, T129–T130.
- **Frontend session, route, error, and administration contracts**: T131–T134.
- **Canonical nullable contact representation**: T122, T134.

### Convergence dependencies

1. T119 precedes T120; T120 establishes the enforced production dependency boundary used by later backend changes.
2. T121 and T122 are independent foundation corrections. T123 depends on T121–T122 so exact event payloads are both safe and canonical.
3. T124 depends on T120 and T123; T125 may run independently. T129–T130 depend on T123–T124 so their final-state evidence uses the canonical recorder and allocator.
4. T126–T128 may proceed after T120; T127 precedes the complete Manager-target API evidence in T129.
5. T131 precedes T132; T133 then applies the settled state/error semantics, and T134 builds on the guarded directory and canonical error handling.
6. T135 follows all owning implementation/test tasks. T136 is the final sequential verification task.
