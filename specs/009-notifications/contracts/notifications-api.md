# Contract: Notifications API

Feature 009 uses the generated canonical contract in `contracts/openapi.yaml`.

Relevant operation IDs:

- `notifications_list`
- `notifications_mark_read`
- `notifications_resolve_target`
- `push_subscriptions_upsert`
- `push_subscriptions_revoke`

The generated TypeScript schema in `frontend/src/shared/api/schema.ts` must remain synchronized with `contracts/openapi.yaml`.
