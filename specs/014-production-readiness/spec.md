# Feature 014: Deployment, Environment Isolation, Migration Safety, Backup and Recovery Readiness

**Branch**: `feature/014-production-readiness`  
**Status**: Specified  
**Authority**: `docs/CHOT_YEU_CAU.md` §9.7–§9.8, `docs/RA_SOAT_YEU_CAU.md` R-107/R-108/R-109

## Requirements

- Deployment inventory must remain committed and contain identities, not secrets.
- Production readiness must fail while mandatory production inventory remains `UNRESOLVED`.
- Runtime config must fail closed for invalid environment, DB, cache, Redis/TLS, origin credential, and web-push values.
- Application and admin/migration database identities must remain separated.
- Migration safety must enforce one leaf per app and unsafe expansion/contraction rules.
- Restore verification must reject DSN identity collisions before connecting and run read-only probes only.
- Recovery readiness must fail without passed restore/capacity evidence.
- Capacity measurement must require at least 50 distinct identities and concurrency at least 20.
- No production/staging value or evidence may be fabricated.

## Out of Scope

- Actual cloud provisioning, real backup execution, real restore drill, production smoke, and real capacity run.
