# Implementation Plan: Reporting, Dashboard and Export

**Branch**: `feature/010-reporting` | **Date**: 2026-08-21 | **Spec**: `specs/010-reporting/spec.md`

## Summary

Add read-only reporting APIs and frontend views for attendance and task reports, plus audited CSV exports. Reporting uses application query services with repository/authorization ports; `config` owns cross-module ORM reads so business modules do not import each other's internals.

## Technical Context

**Language/Version**: Python/Django REST Framework backend, TypeScript/Next.js frontend

**Primary Dependencies**: Existing Django, DRF, PostgreSQL, Next.js, generated OpenAPI client

**Storage**: PostgreSQL source tables only; no denormalized reporting tables

**Testing**: pytest, PostgreSQL API tests, Vitest, OpenAPI/client checks, architecture checks

**Target Platform**: Web application

**Performance Goals**: MVP scale of 50 internal users and date-range filtered read models

**Constraints**: Reporting is read-only; export is audited; sensitive coordinates excluded by default; canonical failure-rate and task metrics remain separate.

## Constitution Check

- Architecture: `reporting.application` uses ports; `config.reporting_adapters` performs cross-module ORM reads as composition/infrastructure.
- Authorization: report permission is checked before filter validation in DRF permission classes.
- Server authority: report scope comes from authenticated actor and backend RBAC.
- Privacy: exports are no-store and do not include coordinate values by default.
- Contracts: OpenAPI and frontend schema are regenerated.

## Project Structure

```text
backend/reporting/
├── application/
├── ports/
└── adapters/api/

backend/config/reporting_adapters.py
frontend/src/features/reports/
frontend/src/app/reports/page.tsx
```

**Structure Decision**: `reporting` is a business module without Django persistence ownership; it is not added to `INSTALLED_APPS` and has no migrations.

## Phase 0: Research

- **Decision**: Use read-time queries over source tables.
  **Rationale**: CHOT does not require denormalized reporting state and source-of-truth drift would be higher risk.
  **Alternatives considered**: Reporting tables/materialized views; rejected for MVP scope.

- **Decision**: Implement CSV export now.
  **Rationale**: It satisfies machine-verifiable export privacy and no-store behavior without new dependencies.
  **Alternatives considered**: XLSX/PDF; deferred because they add format complexity and are not required for current automated proof.

## Phase 1: Design and Contracts

- Endpoints:
  - `GET /api/v1/reports/attendance/`
  - `GET /api/v1/reports/tasks/`
  - `GET /api/v1/reports/attendance/export/`
  - `GET /api/v1/reports/tasks/export/`
- Frontend route: `/reports`
- Export audit action: `report.exported`
