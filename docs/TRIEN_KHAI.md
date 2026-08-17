# Triển khai và phục hồi

Tài liệu này là quy trình vận hành có thể lặp lại cho foundation. Provider, tên
resource thật và mọi phép đo operator vẫn là `UNRESOLVED`; source code và test
không được tự biến trạng thái đó thành bằng chứng production-ready.

## Topology và network

- Production chạy trên **≥2 AZ**. Một **public load balancer** là điểm vào công
  khai; các **private application instances** không nhận kết nối trực tiếp từ
  Internet.
- Mỗi AZ có **per-AZ egress** riêng. Chính sách chặn mặc định áp dụng cho
  **all outbound egress**; chỉ DNS, PostgreSQL, secret store, object storage và các
  endpoint vận hành đã phê duyệt được mở.
- Chạy **exactly one scheduler** cho mọi công việc định kỳ có single-owner.
  Worker có thể scale ngang, scheduler không được nhân bản ngoài cơ chế leader
  election đã được phê duyệt.
- APAC là lựa chọn latency: **APAC is not data residency**. Vị trí lưu dữ liệu
  chỉ được công bố sau quyết định pháp lý/provider riêng.
- **IaC is deferred** trong feature này. Không suy diễn resource provider từ
  manifest; `deploy/environments.yaml` tiếp tục ghi `UNRESOLVED`.

## Database, cache và rollout

1. Route ứng dụng chỉ nhận `DATABASE_URL`. Quyền migration chỉ được inject vào
   process migration qua `DATABASE_ADMIN_URL`; web process không được đọc key
   này và hai DSN phải có identity khác nhau.
2. Thực hiện **migration before rollout** bằng image/commit sẽ được triển khai.
   Chạy `uv run --project backend python scripts/migration_check.py check`, sau
   đó dùng migration principal để chạy migration trước khi thay application
   instances.
3. Xác nhận bảng cache `throttle_cache` đã được provision bởi migration của
   `operations`; staging/production dùng shared database cache, không dùng
   process-local cache.
4. Rollout dần, giữ tương thích N-1, kiểm tra status-only smoke và rollback
   application trước khi thực hiện bất kỳ contract migration phá hủy nào.

## Credential rotation và sự cố

- **Credential rotation**: tạo credential mới, cập nhật secret store, rollout
  consumer, xác nhận credential mới hoạt động rồi thu hồi credential cũ. Thực
  hiện riêng cho runtime DB, migration DB, origin credential và signing keys.
- Khi credential hoặc signing key bị lộ, thực hiện **session revocation**, rotate
  key, vô hiệu token liên quan và lưu bằng chứng operator bên ngoài log ứng dụng.
- Sau worker crash, liệt kê và xử lý **stale lease** theo owner/expiry đã commit;
  không ghi đè claim còn hiệu lực và không coi tiến trình chết là công việc đã
  hoàn tất.

## Isolated restore

1. Tạo **isolated restore** vào project/network không route tới runtime hoặc
   migration database. Inject duy nhất `RECOVERY_DATABASE_URL` vào process xác
   minh.
2. So sánh safe DSN identity với `DATABASE_URL` và `DATABASE_ADMIN_URL` trước
   khi mở socket. Bất kỳ collision nào phải dừng ngay.
3. Chạy `uv run --project backend python backend/manage.py verify_restore`.
   Command mở transaction read-only và xác minh đủ active users, audit rows,
   effective token state, unpublished outbox và schema version.
4. Chỉ operator mới ghi kết quả drill thật vào
   `deploy/recovery-evidence.yaml`. Test, stdout, smoke và capacity command không
   phải evidence. File giữ `UNRESOLVED` cho đến khi drill/measurement thật hoàn
   tất và được ký nhận.
5. Chạy `uv run --project backend python scripts/deployment_check.py recovery-ready`.
   Nonzero là trạng thái mong đợi khi evidence thiếu, stale, failed hoặc vượt
   target; không sửa file để làm gate xanh giả tạo.

## Capacity evidence

Danh sách identity thật được lưu dưới dạng JSON Lines trong file `*.identities`
bị Git ignore. Mỗi dòng phải chứa đúng `identity_id` ổn định của tài khoản và
`bearer_token` ngắn hạn của chính tài khoản đó, ví dụ cấu trúc
`{"identity_id":"<stable-account-id>","bearer_token":"<short-lived-access-token>"}`.
Không dùng token làm `identity_id`; nhiều token của cùng một tài khoản chỉ được
tính là một identity. Chạy
`capacity_check.py measure --identities <file> --concurrency 20 --target-url
<https-idempotent-api-probe> --remediation-owner <owner> --output <result.json>`.
Endpoint đo phải dùng HTTPS, thuộc `/api/v1/`, không tạo mutation và do operator
chọn từ deployment đang kiểm tra. Kết quả p95 tối đa 500 ms mới có thể pass. Output
không tự cập nhật `recovery-evidence.yaml`; operator review và ghi evidence qua
quy trình kiểm soát riêng.
