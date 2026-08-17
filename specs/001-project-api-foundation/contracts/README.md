# Foundation Contract Design

These design contracts define the observable boundaries that implementation and tests must satisfy. They do not replace the generated `contracts/openapi.yaml`; that root artifact is produced during implementation from backend source.

- [API boundary](./api.md)
- [Frontend boundary](./frontend.md)
- [Tooling and CI boundary](./tooling.md)
- [Recovery boundary](./recovery.md)
- [Shared cache boundary](./cache.md)

Authentication, RBAC, business resources, audit/outbox persistence, and provider infrastructure are deliberately absent.
