# Implementation Plan: In-App Notifications and Web Push

**Branch**: `feature/009-notifications` | **Date**: 2026-08-21 | **Spec**: `specs/009-notifications/spec.md`

**Input**: Feature specification from `/specs/009-notifications/spec.md`

## Summary

Feature 009 validates and formalizes the already implemented notification slice from `specs/008-in-app-web-push`: authoritative in-app notifications, read/unread state, opt-in Web Push, quiet hours/TTL/dedupe/suppression, and authorization-safe deep links. No new notification event types, email, SMS, or outbox relay architecture are introduced here.

## Technical Context

**Language/Version**: Python/Django REST Framework backend, TypeScript/Next.js frontend

**Primary Dependencies**: Existing Django, DRF, PostgreSQL, Next.js, generated OpenAPI client, `pywebpush`, `cryptography`

**Storage**: PostgreSQL

**Testing**: pytest, PostgreSQL integration tests, Vitest, Playwright, contract/schema checks

**Target Platform**: Web application

**Performance Goals**: MVP scale of 50 internal users; scheduled notification jobs are idempotent and bounded

**Constraints**: CHOT/R-97 exact five events; in-app authoritative; push generic and best-effort; no sensitive payload; quiet hours 21:00-07:00 Asia/Ho_Chi_Minh; 24-hour TTL

**Scale/Scope**: Internal Helpdesk attendance/task workflow, no email/SMS/native app push

## Constitution Check

- Source authority: CHOT/R-97 controls notification semantics; PRD is used only for UX detail.
- Architecture: notification business logic remains in `backend/notifications/domain` and `application`; API/views and management commands are thin.
- Authorization: backend RBAC/object-scope is required before target resolution.
- Server authority: read time, schedule time, TTL, and push lifecycle state are server-owned.
- Persistence: dedupe, constraints, and leases are PostgreSQL-backed where correctness requires it.
- Privacy: push payloads and persisted payloads exclude sensitive Task/employee/GPS/photo/map/subscription data.
- Contracts: OpenAPI and TypeScript schema are generated and committed.

## Project Structure

```text
backend/notifications/
├── domain/
├── application/
├── ports/
├── adapters/
├── management/commands/
└── migrations/

frontend/src/features/notifications/
├── api/
├── adapters/
├── model/
└── ui/

specs/008-in-app-web-push/
specs/009-notifications/
```

**Structure Decision**: Reuse the existing Feature 008 implementation structure and add Feature 009 trace artifacts rather than duplicating notification code.

## Phase 0: Research

- **Decision**: Treat existing `specs/008-in-app-web-push` as the implemented source slice for Feature 009.
  **Rationale**: Branch history and checked tasks show notifications were implemented as Feature 008, while the new roadmap asks to begin remaining work at Feature 009 with the same scope.
  **Alternatives considered**: Reimplement a duplicate notification module; rejected because it would violate module ownership and create duplicate event infrastructure.

- **Decision**: Add `docs/DEFERRED_WORK.md` entry for real Web Push permission/delivery.
  **Rationale**: CI can verify policy and fake transport behavior, but real browser permission and provider delivery require staging HTTPS and a supported browser.
  **Alternatives considered**: Claim fake-provider delivery as real browser evidence; rejected by governance.

## Phase 1: Design and Contracts

- Data model and API contracts are already implemented in `Notification`, `PushSubscription`, `PushDelivery`, `contracts/openapi.yaml`, and generated frontend schema.
- Feature 009 validation focuses on automated notification suites and deferred real-provider evidence.
- No outbox relay changes are made; Feature 012 owns reliable transactional outbox relay.
