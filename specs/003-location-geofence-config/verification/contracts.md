# Contract verification

Verified 2026-08-18:

- deterministic OpenAPI generation/check: pass;
- Location PATCH generated request requires `version`; every Feature 003 operation documents
  its success and canonical error/conflict responses;
- Location filter and warning enums are constrained in the generated contract;
- protected coordinate values/examples safety: pass;
- generated `frontend/src/shared/api/schema.ts` drift check: pass;
- frontend typed integration and production build: pass.
