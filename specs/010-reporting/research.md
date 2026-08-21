# Research: Reporting, Dashboard and Export

- **Decision**: Keep reporting read-only over source tables.
  **Rationale**: Avoids denormalized source-of-truth drift and matches CHOT's read-only reporting requirement.
  **Alternatives considered**: Persistent read models; rejected for MVP because no canonical requirement needs them.

- **Decision**: Exclude coordinates and private evidence from exports by default.
  **Rationale**: R-101 makes coordinate export explicit opt-in and audited.
  **Alternatives considered**: Always include coordinates for managers; rejected by CHOT.

- **Decision**: CSV export for current implementation.
  **Rationale**: It provides automated verification of authorization, no-store, and audit behavior without new dependencies.
  **Alternatives considered**: XLSX/PDF; can be added later with the same authorization/privacy controls.
