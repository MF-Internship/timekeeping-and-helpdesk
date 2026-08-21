# Timekeeping and Helpdesk Foundation

Feature 001 cung cấp Django/DRF + PostgreSQL foundation, Next.js shell, contract
OpenAPI sinh tự động và các merge gate. Feature chưa chứa authentication hoặc
nghiệp vụ chấm công/helpdesk.

## Entry points

- Backend composition: [backend/config/settings.py](backend/config/settings.py),
  [backend/config/urls.py](backend/config/urls.py), và [backend/manage.py](backend/manage.py).
- Pure shared kernel: [backend/core](backend/core).
- Approved Django owner: [backend/operations](backend/operations). `config` và
  `core` không phải Django app; chỉ `operations` sở hữu cache migration và command
  `verify_restore`.
- Frontend shell: [frontend/src/app](frontend/src/app).

## Contracts và transport

[contracts/openapi.yaml](contracts/openapi.yaml) được sinh từ backend và không
được sửa tay. [frontend/src/shared/api/schema.ts](frontend/src/shared/api/schema.ts)
được sinh từ contract đó. Wrapper viết tay
[frontend/src/shared/api/client.ts](frontend/src/shared/api/client.ts) phải mỏng
và đi qua [authenticated-fetch.ts](frontend/src/shared/transport/authenticated-fetch.ts).

Generated exclusions chỉ áp dụng cho `contracts/openapi.yaml` và
`frontend/src/shared/api/schema.ts`; `client.ts` vẫn chịu thin-client gate.

## Commands và gates

- Runtime chuẩn: Python 3.12, Node.js 22, uv và npm (không dùng pnpm/yarn).
- Cài dependency bất biến: `uv sync --project backend --locked` và
  `npm --prefix frontend ci`.
- Chạy toàn bộ local release gate: `scripts/check_all.sh`.
- Kiểm tra/ghi format frontend: `npm --prefix frontend run format:check` /
  `npm --prefix frontend run format`.
- Kiểm tra/ghi format backend: `uv run --project backend ruff format --check backend scripts` /
  `uv run --project backend ruff format backend scripts`.
- Django system/deployment checks với giá trị phát triển có phạm vi:
  `scripts/check_backend.sh`.
- Migration safety: `uv run --project backend python scripts/migration_check.py check`.
- Environment isolation: `uv run --project backend python scripts/deployment_check.py isolation`.
- Recovery verification: `uv run --project backend python backend/manage.py verify_restore`.
- Capacity measurement: `uv run --project backend python scripts/capacity_check.py measure ...`.

CI được chia thành [quality workflow](.github/workflows/quality.yml) và
[contract workflow](.github/workflows/contract.yml). CI chỉ chạy migration
safety và environment isolation trong nhóm operator controls.
`production-ready` và `recovery-ready` cố ý non-green khi manifest/evidence còn
`UNRESOLVED`; `smoke` và capacity là operator commands, không phải merge gates.

Xem [quickstart](specs/001-project-api-foundation/quickstart.md),
[architecture](docs/ARCHITECTURE.md) và [runbook](docs/TRIEN_KHAI.md).
