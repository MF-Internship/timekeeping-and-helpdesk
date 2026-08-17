# Quy tắc Clean Code — Chấm công & Helpdesk

Áp dụng cho frontend Next.js, backend Django REST Framework và PostgreSQL của dự
án. Quy tắc nghiệp vụ tham chiếu
[CHOT_YEU_CAU.md](CHOT_YEU_CAU.md); tài liệu này quy định cách thể hiện chúng
trong mã và kiểm thử.

Mức độ: **BẮT BUỘC** phải qua CI; **NÊN** là mặc định, ngoại lệ ghi rõ lý do
trong PR; **CÂN NHẮC** phụ thuộc bối cảnh.

## 1. Từ vựng bắt buộc

| Khái niệm | Tên trong code | Không dùng |
|---|---|---|
| Trung tâm/cửa hàng có tọa độ và geofence | `Location` | `BusinessLocation`, `PhysicalLocation`, `Site` |
| Phân loại địa điểm | `LocationKind` | `type`, `category` |
| Kết quả kiểm tra GPS | `LocationValidationResult` | `status`, `state` |
| Cách chọn địa điểm | `LocationResolutionMethod` | `match_method` |
| Bất thường chấm công | `AttendanceAnomaly` | `is_late`, `is_off_assignment` |
| Lý do bất thường | `AttendanceAnomalyReason` | chuỗi tự do |
| Lần bấm chấm công / nhật ký request chấm công | `AttendanceAttempt` | ghi log text, `failed_attendance`, `rejected_attempt` |
| Kết quả lần bấm | `AttendanceAttemptOutcome` | `error_code`, chuỗi tự do |
| Upload ảnh staging chưa bind | `EvidenceUpload` | `temp_photo`, presigned URL, multipart blob |
| Thông báo trong app | `Notification` | push payload làm nguồn sự thật |
| Lần chạy job vận hành | `JobRun` | suy health từ việc không có anomaly |
| Trạng thái Task | `TaskStatus` | `NOT_COMPLETED`, chuỗi tự do |
| Cách hoàn thành task | `CompletionMethod` | chuỗi tự do |
| Chất lượng GPS của bằng chứng Task | `TaskGpsQuality` | `is_gps_good`, boolean flag |
| Quyền nghiệp vụ | `PermissionAction` | kiểm trực tiếp `role` trong view |

`Location` là tên duy nhất và rõ nghĩa vì mô hình chỉ còn một loại địa điểm.
Mọi định danh code dùng tiếng Anh; UI, comment và tài liệu dùng tiếng Việt.

Quy ước: Python dùng `snake_case`, TypeScript dùng `camelCase`, class/enum/type
dùng `PascalCase`, hằng dùng `UPPER_SNAKE_CASE`, JSON API giữ `snake_case` ở cả
hai đầu. Đại lượng đo phải có hậu tố đơn vị: `_m`, `_seconds`, `_mb`, `_px`.
Chuỗi UI gom tại `core/messages.py` hoặc `shared/messages.ts`, không viết thẳng
trong logic.

`camelCase` của TypeScript áp cho **định danh do người viết** (biến, hàm, thuộc
tính của kiểu nội bộ). Trường trên dây thì không: **không tồn tại lớp ánh xạ
`snake_case ↔ camelCase` nào trong MVP** (R-103). Kiểu response sinh từ schema
giữ nguyên tên trường của server, và code frontend đọc thẳng `full_name`,
`is_active`, `must_change_password`. Một lớp ánh xạ sẽ là bản khai báo thứ hai
của cùng hợp đồng, phải sửa hai chỗ mỗi lần thêm trường, và làm mọi form/DOM name
hiện có lệch tên với payload nó gửi đi. Nếu về sau thật sự cần ánh xạ, chỗ duy
nhất được phép đặt là `frontend/src/shared/api/` — không rải ở `features/`.

## 2. Quy tắc mô hình và GPS

```python
class LocationValidationResult(models.TextChoices):
    INSIDE_GEOFENCE = "INSIDE_GEOFENCE", "Trong vùng"
    OUTSIDE_GEOFENCE = "OUTSIDE_GEOFENCE", "Ngoài vùng"

class LocationResolutionMethod(models.TextChoices):
    AUTO_SINGLE = "AUTO_SINGLE", "Một địa điểm"
    USER_SELECTED = "USER_SELECTED", "Người dùng chọn"
    GPS_ONLY = "GPS_ONLY", "Chỉ có GPS"
```

`LocationValidationResult` chỉ có **hai** giá trị. `UNCERTAIN` đã bị bỏ (CHOT
§4.2); cấm thêm lại giá trị thứ ba dưới bất kỳ tên nào.

- Seed đúng 76 `Location` từ hai file CSV; không gộp, dẫn xuất hay thay tọa độ.
  `parent` suy từ tiền tố mã theo CHOT §2; tiền tố không khớp TTKD nào thì
  `parent = NULL`, không đoán theo tên hay khoảng cách.
- Hai CSV **khác header** (`Mã TTKD`/`Tên` với `SHOP_CODE`/`NAME`). Khai báo hai
  mapping tường minh theo bảng CHOT §2, mỗi mapping gắn với một file; cấm dùng
  chung một mapping, cấm dò kiểu `row.get("SHOP_CODE") or row.get("Mã TTKD")`.
  Validate header trước khi đọc dòng đầu, thiếu cột thì raise nêu rõ file và cột;
  cuối seed assert đúng 7 `BUSINESS_CENTER` + 69 `SHOP`. Đọc hụt file TTKD làm
  toàn bộ cửa hàng mất `parent` mà không có lỗi nào — nên đây là assert bắt buộc,
  không phải log cảnh báo. Cột `STT` bị bỏ qua.
- Chỉ `Location.parent` là nullable. `Location.is_active` khai báo
  `BooleanField(default=True, null=False)` — cho phép `NULL` là lỗi review: mọi
  truy vấn ứng viên lọc `is_active = True`, nên một dòng `NULL` sẽ âm thầm biến
  mất khỏi chấm công và khỏi đối chiếu địa chỉ mà không báo lỗi ở đâu. Cả 76 dòng
  seed có `is_active = True`.
- `Location.radius_m`, `Config.max_attendance_accuracy_m`,
  `Config.task_gps_good_accuracy_m`, `Config.task_gps_low_accuracy_m` và các
  ngưỡng phải đọc từ DB/config; không hardcode trong service.
- Cấm dùng EXIF để lấy/so khớp vị trí. Không tạo các field `exif_lat`, `exif_lng`,
  `exif_offset_m`, hay dependency đọc EXIF.
- Client gửi GPS điện thoại: `latitude`, `longitude`, `accuracy_m`, `captured_at`.
  `captured_at` chỉ audit/debug; service tạo `Attendance.recorded_at` bằng giờ
  server UTC và dùng nó để tính `work_date`/anomaly theo `Asia/Ho_Chi_Minh`.
- Boundary/serializer phải reject trước domain mọi GPS không hữu hạn, latitude
  ngoài `[-90, 90]`, longitude ngoài `[-180, 180]`, hoặc `accuracy_m < 0`.
  Domain chỉ nhận `ValidatedPosition`, không nhận JSON/raw number.
- Config validator phải enforce đầy đủ bảng bất biến ở CHOT §4.3:
  `radius_m > 0`, `default_radius_m <= max_radius_m`,
  `max_attendance_accuracy_m > 0`, `task_gps_good_accuracy_m > 0`,
  `task_gps_low_accuracy_m > 0`, `task_gps_good_accuracy_m <=
  task_gps_low_accuracy_m`, `late_checkout_grace_minutes >= 0`,
  `shift_start < shift_end`. Ranh giới “dừng hay cảnh báo” theo đúng bảng §4.3;
  `radius_m < max_attendance_accuracy_m` **chỉ cảnh báo**, không chặn.
- Hàm hình học thuần, không gọi DB/HTTP. Luật geofence là **hai cổng độc lập**:
  cổng chất lượng `accuracy_m <= threshold` và cổng vị trí `distance_m <=
  radius_m`. `accuracy_m` không bao giờ bị trừ vào `radius_m`.

```python
def classify_geofence(distance_m: float,
                      radius_m: float) -> LocationValidationResult:
    if distance_m <= radius_m:
        return LocationValidationResult.INSIDE_GEOFENCE
    return LocationValidationResult.OUTSIDE_GEOFENCE
```

  `classify_geofence` **không nhận `accuracy_m`**: cổng chất lượng nằm ở service,
  chạy trước và có ngưỡng riêng theo từng nghiệp vụ
  (`Config.max_attendance_accuracy_m` cho Attendance,
  `Config.task_gps_good_accuracy_m` cho Task). Thêm lại tham số `accuracy_m` vào
  hàm này là lỗi review.
- Chấm công chỉ chấp nhận ứng viên `INSIDE_GEOFENCE`.
- `accuracy_m > max_attendance_accuracy_m` chặn **Attendance** trước geofence;
  Task `FIELD_EVIDENCE` vẫn hoàn thành với `TaskGpsQuality.LOW_ACCURACY` hoặc
  `.UNRELIABLE`, nhưng không tự gán Location khi chất lượng không phải `GOOD`.
  Task phân loại `gps_quality` trước, chỉ chạy geofence khi `GOOD`.
- Hai bộ ngưỡng **không dùng chéo**: code Attendance không được đọc
  `task_gps_good_accuracy_m`/`task_gps_low_accuracy_m`, code Task không được đọc
  `max_attendance_accuracy_m` (CHOT §4). Trùng giá trị mặc định (25/100) là
  trùng ngẫu nhiên, không phải lý do gộp thành một hằng số hay một hàm chung.
  Attendance cũng **không** có nhánh `LOW_ACCURACY`: chỉ đạt hoặc `WEAK_GPS`.
- Có một ứng viên: `AUTO_SINGLE`; từ hai ứng viên trở lên thì cả Attendance và
  `complete-field` trả `409 LOCATION_CHOICE_REQUIRED` và bắt người dùng chọn
  (CHOT §5.1, §6.2). Cấm `min()` hoặc luật “gần nhất”, ngữ cảnh task hay lịch sử
  để tự chọn ở cả hai luồng.
- Backend nhận `selected_location_id` phải kiểm lại nó thuộc các ứng viên INSIDE
  ở chính mẫu GPS đó. Lựa chọn nằm ngoài tập vừa tính lại bị từ chối
  `422 INVALID_LOCATION_CHOICE` ở cả hai luồng; cấm im lặng bỏ qua lựa chọn sai
  rồi rơi về `AUTO_SINGLE`/`GPS_ONLY`.
- Mọi request chấm công **đã qua xác thực + phân quyền** ghi đúng một
  `AttendanceAttempt` với `outcome` thuộc `AttendanceAttemptOutcome` (CHOT §5.2),
  kể cả request thành công (`outcome = ACCEPTED`). Đây là **nhật ký request chấm
  công của Helpdesk**, không phải bảng “lần bị từ chối” và cũng không phải access
  log; đặt tên biến, docstring, tên report theo nghĩa nhật ký. Chỉ log lần bị từ
  chối là lỗi review: không có mẫu số `ACCEPTED` thì không tính được tỉ lệ thất
  bại theo người và theo địa điểm. Mẫu số của tỉ lệ thất bại là tổng số dòng
  `AttendanceAttempt` **trừ `LOCATION_CHOICE_REQUIRED`**, không phải số ca công;
  tử số là số dòng không thuộc `{ACCEPTED, LOCATION_CHOICE_REQUIRED}` (CHOT §5.2,
  R-77). `LOCATION_CHOICE_REQUIRED` bị loại khỏi **cả hai vế** vì nó là bước giữa
  của một luồng đúng — hệ thống hỏi lại địa điểm, user chọn, lượt sau `ACCEPTED`
  — nên đếm nó ở bất kỳ vế nào cũng làm tỉ lệ sai lệch. Cấm chỉ log text.
- Dòng `AttendanceAttempt` được ghi **ngoài transaction nghiệp vụ**, sau khi
  transaction đó đã kết thúc, ở **cả nhánh commit lẫn nhánh `except`** (CHOT §5.2,
  R-74). Lý do: `uniq_open_session_per_user` bắn `IntegrityError` làm abort
  transaction, nên attempt ghi bên trong sẽ bị rollback cùng — mất đúng dòng cần
  nhất cho `SESSION_ALREADY_OPEN`. Viết `attempt = ...create(...)` bên trong
  `with transaction.atomic():` của luồng chấm công là lỗi review, kể cả khi test
  đang xanh.
- Ngược lại, request chết **trước** cổng nghiệp vụ (bước 1–2 của CHOT §5.1) thì
  **không** ghi attempt: `401`, `403 PERMISSION_DENIED` (`MANAGER` gọi check-in),
  `403 PASSWORD_CHANGE_REQUIRED`, `400 SERVER_OWNED_FIELD` do payload mang `kind`.
  Vị trí gọi `AttendanceAttempt.objects.create(...)` phải nằm **trong** service
  nghiệp vụ, không nằm ở middleware/decorator bọc view — đặt ở ngoài là tự động
  sinh ra những dòng attempt không có `outcome` hợp lệ để điền. Ai thấy cần ghi
  các ca đó thì sửa enum ở CHOT §5.2 trước; cấm tự thêm giá trị `outcome` mới
  trong code, và càng cấm tái dùng một giá trị gần đúng cho có.
- Với mọi request đã qua boundary bước 3, lớp quan trắc tính nearest metadata
  trước khi ghi attempt, kể cả outcome ở bước 3-5. Hàm này không được gọi
  `classify_geofence`, không tạo candidates và không thay thứ tự gate. Serializer
  gắn `nearest_is_approximate` cho `WEAK_GPS`; `candidate_count` của nhánh chưa
  chạy candidate matching giữ `NULL`, không giả thành `0`.
- Mã lỗi API khi không có ứng viên INSIDE là `OUTSIDE_RADIUS` — trùng tên với
  `AttendanceAttemptOutcome.OUTSIDE_RADIUS`. `OUTSIDE_GEOFENCE` chỉ là giá trị
  của `LocationValidationResult`; trả nó ra `error_code` là lỗi review.
- `TaskUpdate.location_candidates` được **lưu vào DB** ngay lúc ghi nhận, kể cả
  khi rỗng, và không bao giờ tính lại khi đọc (CHOT §6.2). Suy “ngoài mọi địa
  điểm” chỉ từ `location IS NULL` là sai: phải xét `gps_quality` **trước**
  (`!= GOOD` → “GPS không đủ tin cậy”, mảng rỗng ở nhánh này không có nghĩa gì),
  còn `GOOD + []` nghĩa là ngoài mọi địa điểm. Nhánh `GOOD` có từ hai candidates
  chỉ được commit khi đã có `location` và `USER_SELECTED`; không gán Location sau.

## 3. Phân tầng và cấu trúc

```text
backend/
  config/                    # Django composition root và environment settings
  shared/                    # shared kernel hẹp và technical primitives
  identity/                  # users, roles, JWT lifecycle
  locations/                 # locations và pure geofence rules
  attendance/                # sessions, attempts, anomalies, end-of-day use case
  tasks/                     # tasks, assignments, updates, evidence binding
  notifications/             # inbox, subscriptions, delivery policy
  audit/                     # immutable business audit owner
  reporting/                 # read-only queries, dashboard, exports
  operations/                # outbox relay và job-health adapters
frontend/
  src/app/                   # App Router layouts và route composition
  src/features/              # auth, attendance, tasks, locations, reports, notifications
  src/shared/                # generated API transport, UI primitives, design tokens
```

Mỗi module nghiệp vụ backend có `domain/`, `application/`, `ports/` và `adapters/`;
Django models, serializers, views và Celery tasks nằm trong adapters. Phụ thuộc đi vào
trong: view/API chỉ parse request và gọi application service; application điều phối
transaction/permission; domain giữ quy tắc thuần; model/repository không chứa chính sách UI.

Pipeline bắt buộc cho mọi mutation/read có scope:

```text
Authentication -> action permission RBAC -> DTO/input validation
-> object scope/ownership ABAC -> business invariant/state transition
-> atomic transaction/DB constraint -> audit log/event
```

View chỉ orchestration; policy authorization, validation domain và persistence
invariant phải tách thành các module/hàm riêng.

**RBAC đứng trước DTO validation, không hoán đổi được** (CHOT §8.2, R-72). Actor
vừa thiếu quyền vừa gửi body sai phải nhận `403 PERMISSION_DENIED`, không phải
`400`: mô tả lỗi body cho người không có quyền gọi endpoint là rò rỉ schema nội
bộ. Ở DRF nghĩa là kiểm quyền nằm trong `permission_classes`/`check_permissions`
— chạy trước `serializer.is_valid()` — chứ không nhét vào `serializer.validate()`
hay `perform_create()`. Đặt `require_permission(...)` ở giữa thân view sau khi đã
gọi `is_valid(raise_exception=True)` là lỗi review.

## 4. Quy tắc hàm và service

- Hàm tối đa 30 dòng, tối đa **4** tham số. Gom request phức tạp vào dataclass.
- Một hàm một trách nhiệm, trả về sớm, lồng tối đa **3 tầng**.

Hai con số này khớp đúng cấu hình tooling ở §9 (`max-args = 4`, ESLint
`max-params` 4 và `max-depth` 3); khi đổi một bên phải đổi cả hai.

- Hàm có tác dụng phụ có tên động từ: `check_in`, `complete_field_task`.
  Hàm hỏi có tên mệnh đề: `can_complete`, `find_inside_locations`.
- Transaction bao trọn kiểm tra chống trùng và ghi Attendance/Task/AuditLog.
- Bất biến chấm công ở database là **partial unique index một phiên mở mỗi user**
  (`AttendanceSession`, CHOT §5.3), không phải `UNIQUE(user_id, work_date, kind)`.
  Một ngày được phép nhiều lượt Check In/Out; đừng khôi phục ràng buộc cũ dưới
  dạng validate ở service.
- Phiên đang mở có **đúng một** định nghĩa: `check_out IS NULL AND
  closed_by_job = False`. Điều kiện của partial unique index, truy vấn tìm phiên
  mở, kiểm tra `SESSION_ALREADY_OPEN`/`NO_OPEN_SESSION` và cờ `has_open_session`
  đều phải dùng nguyên cả hai vế. Rút gọn thành `check_out IS NULL` là lỗi
  review: job cuối ngày đóng phiên nhưng vẫn giữ `check_out = NULL`, nên bản ghi
  đó sẽ bị hiểu nhầm là còn mở và chặn Check In hôm sau. `closed_by_job` là
  `BooleanField(default=False)` không nullable vì nằm trong index.
- Ghi `Attendance`, mở/đóng `AttendanceSession` và ghi/gỡ anomaly nằm trong **một**
  transaction; đóng phiên phải `SELECT ... FOR UPDATE` phiên đang mở.
  `AttendanceAttempt` **nằm ngoài** transaction đó (§2, R-74) — nó là dữ liệu
  quan trắc, không phải bất biến nghiệp vụ.
- Complete Task dùng compare-and-set/row lock; chỉ request thắng được tạo
  `TaskUpdate COMPLETED`.
- Upload object storage không nằm trong DB transaction. Backend HEAD/kiểm
  metadata trước khi lock; trong transaction finalize phải khóa Task và các
  EvidenceUpload, kiểm lại owner/Task/status chưa bind, ghi TaskUpdate/TaskPhoto
  rồi chuyển slot sang BOUND. `Idempotency-Key` cùng payload trả cùng kết quả;
  cùng key khác payload trả conflict **chỉ sau khi key đã bind vào một request
  commit-eligible**. Các response pre-commit (Location choice/invalid choice,
  validation GPS/file) không bind key; resend cùng key với lựa chọn/fix mới được
  phép. Không consume slot ở endpoint upload.
- `TaskUpdate` là lịch sử chỉ-`INSERT`; sáu trường ảnh chụp trên `Task`
  (`status`, `completed_by`, `completed_at`, `completion_method`,
  `completion_note`, `block_reason`) **chỉ được ghi trong cùng transaction với
  `TaskUpdate` sinh ra chúng** (CHOT §7, R-84). Không có đường nào ghi thẳng
  `Task.status` mà không kèm `TaskUpdate` — `MANAGER_OVERRIDE` cũng phải tạo
  `TaskUpdate`. TaskUpdate chỉ `INSERT`; Location mơ hồ phải được chọn trước khi
  completion transaction tạo bản ghi.
- Anomaly ca làm tính theo **ngày công**, không theo từng lượt bấm: hàm quyết định
  nhận danh sách lượt trong ngày, không nhận một `Attendance` đơn lẻ.
- Không dùng boolean flag thay enum/trạng thái nghiệp vụ.
- Log/audit không chứa presigned URL hay dữ liệu ảnh nhạy cảm.
- Port ghi audit và ghi outbox (`append_audit_entry`, `append_outbox_event`)
  **tham gia** transaction của caller và không tự mở commit riêng: bên trong port
  không có `transaction.atomic()`, không có `transaction.on_commit()`. Ghi nghiệp
  vụ + `AuditLog` + `OutboxEvent` của một hành động cùng commit hoặc cùng
  rollback (CHOT §9.4, R-104). Thêm atomic vào port là hồi quy, không phải sửa
  lỗi — nó tách vết kiểm toán và sự kiện khỏi số phận của dữ liệu chúng mô tả.
- `request_id`/`correlation_id` của `OutboxEvent` đọc từ **context ambient** do
  middleware bind theo vòng đời request, không thêm tham số vào DTO sự kiện và
  không bắt use case chuyền tay qua các tầng. Chuỗi rỗng khi không có request là
  trạng thái bình thường, không raise và không chặn append. `AuditLog` **không**
  nhận hai cột này: hình dạng của nó đã chốt ở CHOT §7.
- Bộ lọc payload dùng chung nằm ở shared kernel (`backend/core/`) và chạy **tại
  port, trước khi tạo dòng**, cho cả `OutboxEvent.payload` lẫn
  `AuditLog.before`/`after`. Bộ lọc khớp **tên khóa chính xác**, không khớp chuỗi
  con — `must_change_password`, `active_refresh_sessions` phải ghi được bình
  thường — và từ chối mọi giá trị chuỗi chứa `://`. Thông báo lỗi nêu **đường
  dẫn** khóa vi phạm, tuyệt đối không nêu giá trị. Đừng lọc lại ở từng call
  site: sửa ở port thì mọi publisher tương lai được bảo vệ, sửa ở call site thì
  publisher tiếp theo quên.
- Relay outbox **tự sở hữu transaction ngắn của nó** và đó không phải ngoại lệ
  của luật trên (CHOT §9.5, R-105): luật “port không tự commit” ràng buộc các
  port `append_*` vì chúng chạy bên trong unit of work của một thay đổi nghiệp
  vụ. Relay không có thay đổi nghiệp vụ nào để đi cùng. Vì vậy **không** đặt tên
  hàm relay theo dạng `append_*` — vừa sai nghĩa, vừa làm test gác AD-4 hiểu
  nhầm. Transaction claim phải **ngắn** và tuyệt đối không ôm lời gọi transport
  bên trong: giữ khóa dòng suốt một request mạng là cách biến một broker chậm
  thành một database treo.
- Mọi quyết định của relay ghi xuống **dòng đã commit**: `attempt_count`,
  `next_attempt_at`, `lease_expires_at`, `leased_by`, `last_error`,
  `publish_state`. Không giữ hàng đợi, bộ đếm hay “danh sách đang xử lý” trong bộ
  nhớ tiến trình — tiến trình chết là chúng biến mất, còn công việc thì không.
- Mọi lệnh ghi của relay lên một dòng đã claim đều **kèm điều kiện danh tính của
  claim** (`leased_by` và `lease_expires_at` mà worker đã claim theo) trong mệnh
  đề `WHERE`. Lease hết hạn là chuyện bình thường chứ không phải lỗi: worker thứ
  hai được quyền claim lại một cách hợp lệ, và nếu worker cũ ghi đè vô điều kiện
  thì nó đặt lại một dòng `PUBLISHED` về `PENDING` (lần gửi thứ ba) hoặc
  `DEAD_LETTER` một sự kiện đã gửi thành công. Ghi hụt **không** phải là thành
  công, không phải retry, không phải dead-letter: không đụng vào instance trong
  bộ nhớ, ghi một log record và đếm riêng trong kết quả lô.
- Một transport ném ra thứ không phải `TransportError` là **defect của adapter**,
  không phải sự cố hạ tầng, nên không được biến thành lịch backoff — nhưng cũng
  không được làm hỏng cả lô: bắt theo từng sự kiện, `logger.exception`, **trả
  claim** để dòng đó không bị treo tới khi lease hết hạn, rồi chạy tiếp các sự
  kiện còn lại. Lần thử đã tiêu **không được hoàn lại** (số đếm là “đã chạm vào
  bao nhiêu lần”, không phải “đã gọi mạng bao nhiêu lần”).
- Backoff là **hàm thuần** nhận số lần đã thử và cấu hình, trả khoảng chờ. Số mũ
  bị **kẹp trần trước khi luỹ thừa** để một bộ đếm chạy loạn không sinh ra số
  nguyên khổng lồ, rồi kết quả nhân đôi mới đi qua `min(..., trần)` — kẹp số mũ
  giữ cho phép tính hữu hạn, `min` giữ cho khoảng chờ đúng bằng trần đã công bố.
  Không có nhánh `if` nào trong relay quyết định “lần này bỏ qua backoff”.
- Bộ số backoff mặc định là **một lời hứa vận hành có thể kiểm chứng**, không
  phải ba con số chọn cho đẹp: tổng các khoảng chờ trong ngân sách thử lại phải
  phủ hết **cửa sổ gián đoạn đã cam kết** (hiện tại: một giờ), và trần phải thực
  sự chạm tới trong ngân sách đó — một trần không bao giờ với tới chỉ là trang
  trí. Lý do đặt cùng chỗ với con số (comment ở `settings.py`) và có test giữ,
  vì hệ quả của việc chọn sai không hiện ra lúc chạy bình thường: nó hiện ra khi
  một sự cố ngắn đẩy toàn bộ backlog vào `DEAD_LETTER`, nơi chưa có đường quay
  lại (DW-42).
- Cấu hình relay đi vào hàm dưới dạng **một dataclass frozen**, không phải sáu
  tham số rời — vừa để hàm không vượt `max-args`, vừa để thêm một tuỳ chọn không
  phải sửa chữ ký của cả chuỗi lời gọi. Đọc cấu hình bằng helper có kiểu, fail
  ngay lúc khởi động: tên transport ngoài danh sách thì `RuntimeError` **nêu tên
  biến môi trường**, và các số đếm phải dương.
- Consumer khử trùng lặp bằng **ràng buộc `UNIQUE(consumer, event_id)`**, không
  bằng “đọc xem đã xử lý chưa rồi ghi”. `IntegrityError` được hấp thụ trong một
  `atomic()` lồng (savepoint) rồi trả về “đã xử lý rồi”: thiếu savepoint thì
  transaction của caller hỏng hẳn sau câu lệnh lỗi, và nhánh “bỏ qua” trở thành
  sự cố. Dấu khử trùng lặp ghi **trong** transaction làm việc, không phải trước
  hay sau nó.
- Lý do lỗi lưu xuống và phát ra cảnh báo phải đi qua bộ làm sạch dùng chung ở
  shared kernel và **bị chặn độ dài**. Cảnh báo mang `event_id`, danh tính
  aggregate, số lần đã thử và lý do đã làm sạch — dataclass cảnh báo **không có
  trường payload**, để chuyện “vô tình log payload” không có chỗ mà xảy ra.
- Management command chạy relay là **shim**: chỉ quyết định chạy bao nhiêu lô và
  in tổng kết. Mọi quyết định nghiệp vụ nằm ở tầng application, nơi test chạm
  được — không ai test một management command kỹ như test một hàm. Số lô không
  dương bị từ chối bằng `CommandError` (một biến shell chưa nở ra thành số là
  cách `--batches 0` xuất hiện, và một lần chạy “thành công” không relay gì cả
  là lỗi không ai nhìn thấy), và tổng kết đi ra **cả log lẫn stdout** — stdout
  thuộc về người đang ngồi xem, còn cron lúc ba giờ sáng thì không có ai xem.
- Module nghiệp vụ chỉ chạm state của nhau qua application port (AD-2); production
  không `import` `models`/`domain`/`adapters` của module khác. Test được phép
  import ORM model của module khác để khẳng định kết quả — miễn trừ này áp cho
  `*/tests/*`, `*/migrations/*` và **duy nhất** package composition root
  `config/` (nối adapter của mọi module vào project đúng là việc của nó, và nó
  không sở hữu state nghiệp vụ nào để bảo vệ). Ba miễn trừ này là danh sách
  đóng và phải ghi rõ lý do ngay trong file gác.

Ví dụ request rõ nghĩa:

```python
@dataclass(frozen=True)
class CapturePosition:
    latitude: float
    longitude: float
    accuracy_m: float
    captured_at: datetime | None = None

@dataclass(frozen=True)
class AttendanceRequest:
    position: CapturePosition
    selected_location_id: int | None = None
```

`AttendanceRequest` **không có `kind`**: `kind` suy từ route
(`/check-in` → `IN`, `/check-out` → `OUT`) và được service truyền vào riêng, ví
dụ `check_in(actor, request)` gọi `_record(actor, request, AttendanceKind.IN)`.
Serializer nhận `kind` trong payload phải trả `400 SERVER_OWNED_FIELD`.

Service nhận `actor: User` từ authentication context riêng với DTO.
`user_id`, `kind`, `recorded_at`, `work_date`, `validation_result`,
`resolution_method`, `distance_m`, anomaly, `device_metadata`, `request_ip` và
authorization scope không nằm trong request DTO; client gửi các field này phải bị
reject. `device_metadata` là dữ liệu audit/risk, không phải định danh thiết bị
đáng tin cậy.

| Client-owned/client-reported | Server-owned/authoritative |
|---|---|
| GPS, `captured_at`, `selected_location_id`, photo, note, `block_reason`, input nghiệp vụ được phép | authenticated `user_id`, `kind`, `recorded_at`, `work_date`, `validation_result`, `resolution_method`, `gps_quality`, `distance_m`, permission/object scope, completion actor, transition result, anomaly, audit timestamp |

Serializer/DTO input chỉ expose cột client-owned. Cấm thêm field server-owned
dưới dạng optional để “tiện dùng”.

## 5. RBAC

```python
PERMISSION_IMPLIES = {
    PermissionAction.TASK_VIEW_ALL: {PermissionAction.TASK_VIEW_SELF},
    PermissionAction.TASK_UPDATE_ANY: {PermissionAction.TASK_UPDATE_SELF},
    PermissionAction.ATTENDANCE_VIEW_ALL: {PermissionAction.ATTENDANCE_VIEW_SELF},
    PermissionAction.REPORT_VIEW_ALL: {PermissionAction.REPORT_VIEW_SELF},
    PermissionAction.PHOTO_VIEW_ALL: {PermissionAction.PHOTO_VIEW_SELF},
}

def has_permission(user: User, action: PermissionAction) -> bool:
    granted = ROLE_PERMISSIONS[user.role]
    return action in granted or any(action in PERMISSION_IMPLIES.get(item, set())
                                    for item in granted)

def require_permission(user: User, action: PermissionAction) -> None:
    if not has_permission(user, action):
        raise PermissionDenied(action)
```

- Khai báo map Role × `PermissionAction` ở một module duy nhất, khớp đúng ma trận
  canonical CHOT §8.
- `PERMISSION_IMPLIES` có đúng **5** cặp; chỉ dùng implication trong map này,
  không suy diễn kế thừa action khác. `view.all`/`update.any` không thay thế
  business validation.
- `LEADER` chỉ đọc: role map của Leader không được chứa bất kỳ action mutation
  nào, kể cả `task.create.assign` và `task.update.any`.
- Mọi service/API public kiểm quyền trước khi đọc/ghi dữ liệu.
- Không dùng `if user.role == Role.MANAGER` ngoài module phân quyền.
- Frontend chỉ dùng capability từ API để điều khiển UI; backend là nguồn thực thi.

RBAC không phải ownership. `task.view.self`, `task.update.self` và
`task.complete.field` phải kiểm object scope sau action permission: Task do actor
tạo hoặc actor là assignee. Ưu tiên scope trong query/policy, ví dụ
`Task.objects.filter(id=task_id).filter(Q(created_by=actor) | Q(assignees=actor))`.
`task.update.any` không bỏ qua state transition; Leader luôn bị từ chối mutation.

`user.assign_role` chỉ gán được `LEADER` và `HELPDESK` (CHOT §8). Khai báo tập
này thành một hằng số ở module phân quyền (`ASSIGNABLE_ROLES`), dùng nó cho cả
validate serializer lẫn kiểm ở service; gán `MANAGER` trả `403 PERMISSION_DENIED`
kể cả khi target là chính actor. Không có nhánh “nếu actor là superuser thì cho
qua” ở tầng API — `MANAGER` chỉ sinh từ seed hoặc `manage.py`. Mọi thay đổi vai
trò ghi `AuditLog` kèm role cũ và role mới.

`user.manage` cũng bị chặn y hệt, không chỉ `user.assign_role` (CHOT §8). Cấm
kiểm `MANAGER` riêng ở serializer gán vai trò rồi để create user tự do — đó là
cửa sau kinh điển. Nhưng hai luật có **phạm vi khác nhau**, đừng nhét chung một
guard rồi tưởng đã xong (CHOT §10):

- `target.role` không được là `MANAGER` — áp cho **mọi** thao tác ghi (sửa hồ sơ,
  `is_active`, reset mật khẩu, đổi vai trò), kể cả khi `target == actor`.
- `role` trong payload phải thuộc `ASSIGNABLE_ROLES` — chỉ áp cho **hai** endpoint
  thực sự khai báo trường `role`: `POST /api/users/` và `PATCH /api/users/{id}/role`.

Cả hai trả `403 PERMISSION_DENIED`, không phải `422` — đây là giới hạn quyền chứ
không phải dữ liệu sai định dạng. `PATCH /api/users/{id}/` (sửa hồ sơ) không nằm
trong luật thứ hai vì serializer của nó không có trường `role`; nó trả
`400 SERVER_OWNED_FIELD` do trường *có mặt*, không do giá trị. Thứ tự chạy là
action → target → payload, nên target `MANAGER` + payload có `role` ra `403`, không
ra `400`. `user.view` không bị guard này chạm tới: queryset danh sách người dùng
**không** lọc bỏ `MANAGER`.

Hai bước **action** và **target** cùng thuộc cổng phân quyền và cài trong
`permission_classes`/`has_object_permission`, chạy **trước** `serializer
.is_valid()` (CHOT §8.2, R-87). Cấm đặt luật target trong `serializer
.validate()` hay `perform_update()`: làm vậy thì DTO validation chạy trước và
một actor không đủ quyền nhận `400 SERVER_OWNED_FIELD` — vừa sai thứ tự, vừa rò
hình dạng payload. Kiểm chứng nhanh khi review: gửi body **rỗng** lên target
`MANAGER` mà không ra `403` là đặt guard sai chỗ. Ngược lại, `SERVER_OWNED_FIELD`
**không** phải ngoại lệ chạy trước RBAC — nó nằm trong DTO validation, sau cổng
quyền.

`role` ở serializer tạo user khai báo `required=True`, **không** `default=`
(CHOT §10). Thiếu `role` để DRF trả `400` lỗi theo trường; cấm viết
`validated_data.get("role", Role.HELPDESK)` hay bất kỳ biến thể nào âm thầm điền
vai trò hộ client. Cũng cấm đặt mã lỗi riêng `ROLE_REQUIRED`: mã riêng dành cho
ràng buộc **có điều kiện** (như `BLOCK_REASON_REQUIRED`), còn trường bắt buộc vô
điều kiện thì dùng lỗi validate mặc định — nếu không, bảng mã lỗi sẽ phình ra
bằng đúng số trường trong serializer.

Endpoint self (`/api/change-password/`, `/api/me/`) tách khỏi nhánh quản trị
`/api/users/`, không gộp chung ViewSet và **từ chối** `user_id` trong payload
bằng `400 SERVER_OWNED_FIELD` (CHOT §10, R-76) — luôn thao tác trên
`request.user`. "Từ chối" chứ không phải "bỏ qua": bỏ qua im lặng khiến client
gửi `user_id` của người khác nhận `200` và tin rằng nó vừa đổi mật khẩu hộ người
đó. Gộp hai nhánh làm một view rồi rẽ bằng `if` là lỗi review vì hai nhánh có
policy khác nhau, sửa một bên rất dễ hở bên kia.

`POST /api/change-password/` là endpoint **duy nhất** vừa gọi
`revoke_all_refresh_tokens()` vừa trả token trong response (CHOT §9.2.1, R-78).
Thứ tự bắt buộc: thu hồi toàn bộ trước, cấp cặp `access` + `refresh` mới sau —
viết ngược thì cặp vừa cấp cũng bị blacklist ngay. Ba chỗ gọi helper còn lại
(logout, Manager reset, `is_active = False`) **không** cấp token mới.

Ba thao tác nhạy cảm có endpoint riêng (`PATCH /api/users/{id}/role`,
`PATCH .../status`, `POST .../reset-password`, CHOT §10), mỗi cái nhận đúng một
trường. `PATCH /api/users/{id}/` chỉ sửa hồ sơ; serializer của nó **không khai
báo** `role`, `password`, `is_active`, và nhận các trường này thì trả
`400 SERVER_OWNED_FIELD` chứ không im lặng bỏ qua — bỏ qua im lặng khiến client
tưởng đã khóa được tài khoản. Cấm gộp lại thành một `PATCH` đa năng rồi rẽ nhánh
theo trường có mặt trong payload.

`MANAGER` không có `attendance.check_in.self`/`check_out.self` (CHOT §8). Không
được “tiện tay” thêm vào role map để test cho nhanh; muốn Manager chấm công thì
sửa CHOT trước. Ngược lại, cấm hardcode `role == HELPDESK` trong service chấm
công — vẫn kiểm bằng action như mọi chỗ khác.

Mật khẩu ban đầu **server sinh**, cả lúc tạo user lẫn lúc reset (CHOT §9.2).
Serializer của hai endpoint này không khai báo trường `password`; sinh bằng
`secrets.token_urlsafe` chứ không phải `random`, qua **một** helper dùng chung
cho cả hai chỗ. Mật khẩu bản rõ chỉ tồn tại trong response của đúng request đó:
không gán vào thuộc tính model, không đưa vào `AuditLog`, không `logger.info`,
không đính vào exception message. Cấm thêm “tính năng xem lại mật khẩu” dưới mọi
hình thức — muốn xem lại thì reset.

Danh sách người dùng chỉ mở cho `MANAGER`: `user.view` **không** cấp cho `LEADER`
(CHOT §8). Picker chọn người nhận việc gọi đúng `GET /api/users/` với query
`is_active=true` (thêm `role=HELPDESK` nếu muốn thu hẹp); cấm mở một endpoint
“lite” trả tên nhân viên mà bỏ kiểm quyền cho tiện frontend. Chỉ tồn tại **một**
`GET /api/users/` với query **tùy chọn** (CHOT §10, R-81): không truyền filter
thì nó trả cả user đang khóa, vì màn quản trị cần nhìn thấy tài khoản đã khóa để
mở lại. Vì thế **cấm** hardcode `is_active=True` vào queryset mặc định của view
để "cho an toàn" — làm vậy là lặng lẽ phá màn quản trị. Lọc `is_active` ở picker
là việc của client; server chặn hậu kiểm bằng `422 INACTIVE_ASSIGNEE` khi tạo/sửa
task.

Khóa tài khoản (`is_active = False`) **không được** đụng vào `TaskAssignee` hay
`Task.status` (CHOT §6.1). Không viết signal/`post_save` gỡ assignee khi khóa —
một cú bấm nút sửa hàng loạt bản ghi nghiệp vụ là thứ không hoàn nguyên được. Ràng
buộc nằm ở chiều ngược lại: serializer tạo/sửa task validate `assignee_ids`, gặp
user đã khóa thì `422 INACTIVE_ASSIGNEE` cho **toàn bộ** request kèm danh sách id
vi phạm, không lặng lẽ lọc bớt phần tử rồi trả `201`. Khi `PATCH` task, chỉ
validate id **mới thêm**; validate lại toàn bộ assignee cũ sẽ khóa cứng mọi task
có người đã nghỉ việc. Tương ứng, queryset báo cáo và lịch sử **không** lọc
`is_active` — lọc vào là số liệu quá khứ tự đổi mỗi lần có người nghỉ.

**Xác thực (CHOT §9.2.1).** Authentication trả lời “anh là ai”, RBAC ở trên trả
lời “anh được làm gì”; giữ hai tầng tách bạch.

- Cấu hình `SIMPLE_JWT` nằm ở **một** khối duy nhất trong settings, đúng năm tham
  số đã chốt (15 phút / 7 ngày / `ROTATE_REFRESH_TOKENS` / `BLACKLIST_AFTER_ROTATION`
  / `UPDATE_LAST_LOGIN`). Cấm hardcode thời hạn token ở view hay client.
- Bật app `token_blacklist`; refresh token **phải có trạng thái ở server**. Cấu
  hình refresh stateless là lỗi review vì mất khả năng thu hồi.
- Thu hồi đi qua **một** helper (ví dụ `revoke_all_refresh_tokens(user, reason)`),
  gọi ở đúng bốn chỗ: logout, Manager reset mật khẩu, user tự đổi mật khẩu, và
  `is_active = False`. Helper tự ghi `AuditLog`; cấm mỗi view tự blacklist một
  kiểu. **Logout không phải ngoại lệ**: nó cũng thu hồi toàn bộ refresh token của
  user chứ không chỉ token gửi kèm request — view logout gọi đúng helper này,
  không tự `RefreshToken(token).blacklist()`.
- Mô tả hành vi thu hồi ở docstring/comment/tài liệu phải dùng đúng câu canonical
  ở CHOT §9.2.1: thu hồi toàn bộ refresh token, access token không blacklist
  riêng, trừ request bị chặn bởi `is_active`/`must_change_password`. Viết “mọi
  thiết bị bị đăng xuất ngay lập tức” là sai — chỉ đúng với `is_active = False`.
- Payload token chỉ có `user_id`, `exp`, `jti`, `token_type`. **Không** thêm
  claim `role`/permission — RBAC luôn đọc role từ DB ở từng request.
- Sau khi giải mã token, mọi request vẫn nạp user và kiểm `user.is_active` cùng
  `must_change_password`. Token hợp lệ không phải là giấy thông hành. Việc access
  token không có blacklist riêng **không** cho phép bỏ các truy vấn này: cái bị
  cấm là dựng thêm bảng blacklist cho access token, không phải kiểm trạng thái
  user. Bỏ kiểm để “tiết kiệm một query” là lỗi review.
- Token không bao giờ vào log, `AuditLog`, query string hay URL ảnh; client giữ
  access token trong bộ nhớ ứng dụng, không `localStorage`/`sessionStorage`.
  Refresh token chỉ ở cookie host-only `Secure; HttpOnly; SameSite=Strict`, không
  `Domain`, `Path=/api/v1/auth/`; endpoint không nhận hoặc trả refresh trong JSON.
  Test kiểm chính xác thuộc tính cookie và `Cache-Control: private, no-store`.
- Mã lỗi xác thực tách bạch, không gộp: thiếu/sai/hết hạn token là
  `401 INVALID_TOKEN`; token hợp lệ nhưng `is_active = False` là
  `401 ACCOUNT_INACTIVE` (client dừng vòng lặp refresh và báo “tài khoản đã bị
  khóa”); `must_change_password = True` gọi endpoint khác endpoint đổi mật khẩu
  là `403 PASSWORD_CHANGE_REQUIRED`; thiếu quyền là `403 PERMISSION_DENIED`.
  Riêng `/api/v1/auth/login` giữ chung `401 INVALID_CREDENTIALS` cho cả sai mật khẩu
  lẫn tài khoản khóa, không tiết lộ tài khoản có tồn tại hay không.

## 6. Ảnh và dữ liệu nhạy cảm

- Ảnh hoàn thành là bằng chứng hình ảnh, không phải nguồn GPS.
- Client nén trước upload; backend kiểm MIME, kích thước và số lượng ảnh theo
  `completion_method`: `FIELD_EVIDENCE` bắt buộc **1-5** ảnh, `MANAGER_OVERRIDE`
  cho phép **0-5** ảnh, cập nhật trạng thái thường 0-5 ảnh. Giới hạn tối đa 5 MB
  mỗi ảnh áp dụng cho mọi luồng.
- Presigned URL chỉ sinh sau `photo.view.self` hoặc `photo.view.all`.
- Không log tọa độ chính xác hoặc URL ảnh ở mức info; giới hạn truy cập theo RBAC.
- FIELD_EVIDENCE dùng presigned PUT từng ảnh vào private staging, không dùng một
  multipart request chứa ảnh + GPS. Slot ràng buộc actor/Task/key/MIME/size/SHA-256,
  sống ngắn; finalize kiểm lại toàn bộ và cleanup idempotent chỉ xóa slot/object
  chưa bind đã hết hạn. Cấm object key staging chứa `TaskUpdate.id`.
- Draft IndexedDB namespace theo account + Task, chỉ giữ ảnh đã nén/note/upload
  state; không giữ GPS, token hoặc presigned URL. Xóa sau verified completion,
  logout/account switch, user xóa hoặc quá 7 ngày. Storage/quota failure phải
  thành UI state; không được báo “đã lưu” trước khi transaction IndexedDB commit.
- Push subscription là secret vận hành: mã hóa khi lưu, endpoint không vào log;
  vô hiệu hóa khi logout/account switch/account inactive. Push payload lock-screen
  không chứa tên Task/người, tọa độ, note hay ảnh; deep-link luôn kiểm lại RBAC.

**Địa chỉ và link bản đồ (CHOT §6.2.1).**

- `maps_url` và `resolved_address` là giá trị **dẫn xuất**, sinh ở serializer từ
  tọa độ và `location` đã lưu; không thêm cột DB, không cache vào bảng nghiệp vụ.
- Dựng `maps_url` bằng một helper duy nhất, tọa độ đi qua `urlencode`; cấm nối
  chuỗi tay ở nhiều chỗ và cấm nhận URL bản đồ từ client rồi hiển thị lại.
- Link ra ngoài luôn có `target="_blank"` kèm `rel="noopener noreferrer"`.
- **Không gọi API geocoding bên ngoài** trong bất kỳ luồng nào; xác nhận địa chỉ
  chỉ đối chiếu bảng `Location`. Không nhúng iframe/SDK bản đồ.
- `maps_url` chỉ trả cho người có quyền xem bản ghi đó; nó phơi bày vị trí nhân
  viên nên đi cùng RBAC như ảnh, và không được log ở mức info.
- Thứ tự xét để chọn nhãn hiển thị là `location` → `gps_quality` →
  `location_candidates` (CHOT §6.2.1). Khi `location IS NULL`: `gps_quality !=
  GOOD` hiện “GPS không đủ tin cậy để đối chiếu địa điểm” và **dừng ở đó**; chỉ
  khi `gps_quality = GOOD` mới được đọc `location_candidates`, và bản ghi đã
  commit chỉ có mảng rỗng, nghĩa là “ngoài mọi địa điểm đã đăng ký”. Đọc mảng
  trước là lỗi review:
  bản ghi `gps_quality != GOOD` không chạy geofence nên mảng **luôn** rỗng, nhìn
  mảng rỗng rồi kết luận sẽ dán nhãn “ngoài mọi địa điểm” cho bản ghi chưa hề
  được kiểm tra.

## 7. Kiểm thử chấp nhận bắt buộc

| Ca | Kỳ vọng |
|---|---|
| Seed | Đúng 76 `Location`, mã/tọa độ CSV giữ nguyên, `parent` suy theo mã, `HCM000079.parent IS NULL`, cả 76 dòng `is_active = True` và cột không nhận `NULL`, chạy hai lần idempotent |
| Seed header hai file | Sau seed có đúng **7** `BUSINESS_CENTER` và **69** `SHOP`; đọc file TTKD bằng mapping của file cửa hàng phải **raise** ở bước validate header (nêu tên file + cột thiếu), không được seed 69 dòng rồi im lặng bỏ 7 TTKD |
| Một geofence INSIDE | Chấm công thành công, `AUTO_SINGLE` |
| Hai geofence INSIDE (Attendance) | API yêu cầu chọn; không tạo bản ghi trước khi chọn |
| Hai geofence INSIDE (`complete-field`) | Không chọn trả `409 LOCATION_CHOICE_REQUIRED`, không tạo `TaskUpdate`; chọn hợp lệ trả `201`, `USER_SELECTED`, lưu Location và toàn bộ candidates |
| Chọn location ngoài tập INSIDE | Từ chối `422 INVALID_LOCATION_CHOICE` ở cả Attendance lẫn `complete-field`, không tạo `Attendance`/`TaskUpdate`; **response** trả danh sách ứng viên mới nhất; riêng Attendance ghi `AttendanceAttempt(INVALID_LOCATION_CHOICE)` với `candidate_count`, `nearest_location`, `nearest_distance_m` — **không** lưu mảng ứng viên vào attempt |
| Hai cổng độc lập | `d=40, a=20, r=50, t=25` → `INSIDE_GEOFENCE`; `d=60, a=5, r=50` → `OUTSIDE_GEOFENCE`; `classify_geofence` không nhận `accuracy_m` |
| Enum kết quả | `LocationValidationResult` có đúng hai giá trị; không tồn tại `UNCERTAIN` |
| `accuracy_m > max_attendance_accuracy_m` | Attendance từ chối trước khi tìm ứng viên; ghi `AttendanceAttempt(WEAK_GPS)` |
| Lần bấm bị từ chối | Mỗi nhánh từ chối ghi đúng một `AttendanceAttempt` với `outcome` tương ứng, `attendance IS NULL` |
| Lần bấm thành công | Request thành công cũng ghi đúng một `AttendanceAttempt` với `outcome = ACCEPTED` và `attendance` trỏ tới bản ghi vừa tạo |
| Mã lỗi ngoài bán kính | Response body dùng `OUTSIDE_RADIUS`; chuỗi `OUTSIDE_GEOFENCE` không xuất hiện trong bất kỳ `error_code` nào |
| Payload có `kind` | Trả `400 SERVER_OWNED_FIELD`; `kind` lưu trong DB luôn khớp route |
| Không còn `OFF_ASSIGNMENT` | Check In/Out ở bất kỳ Location đang hoạt động nào cũng thành công và **không** sinh anomaly; `len(AttendanceAnomalyReason.choices) == 4`, chuỗi `OFF_ASSIGNMENT` không có trong enum/migration/response (R-73) |
| Check Out muộn | Quá `late_checkout_grace_minutes` sinh `LATE_CHECK_OUT` |
| Ngày nghỉ | Job `MISSING_CHECK_OUT` **chạy mọi ngày**, kể cả Chủ nhật và ngày có `Holiday`: phiên mở từ ngày làm việc phải bị đóng khi job chạy vào ngày nghỉ kế tiếp (R-82) |
| Anomaly không xét ngày | Phiên mở có `work_date` rơi vào Chủ nhật/ngày lễ vẫn nhận `AttendanceAnomaly(MISSING_CHECK_OUT)`; sau mỗi lần job chạy, số phiên `closed_by_job = True` bằng đúng số anomaly `MISSING_CHECK_OUT`; grep thân job không thấy `working_weekdays` lẫn `Holiday` (R-85) |
| Attempt sống sót rollback | Check In khi đang có phiên mở: transaction nghiệp vụ rollback vì `IntegrityError`, nhưng dòng `AttendanceAttempt(SESSION_ALREADY_OPEN)` **vẫn còn** trong DB sau request (R-74) |
| Tỉ lệ thất bại | `LOCATION_CHOICE_REQUIRED` không nằm trong tử số lẫn mẫu số; dataset có đủ 7 `outcome` cho ra đúng tỉ lệ đã tính tay (R-77) |
| `punch_index` | Một ngày bấm `IN → OUT → IN → OUT` cho `punch_index` `1 → 2 → 3 → 4` trong **một** dãy chung, không phải hai dãy riêng cho IN và OUT; không có cột `punch_index` trong migration (R-79) |
| `Task` là ảnh chụp | Sau mỗi lần đổi trạng thái (kể cả `MANAGER_OVERRIDE`), sáu trường ảnh chụp trên `Task` bằng đúng giá trị của `TaskUpdate` mới nhất; không có đường ghi `Task.status` nào không kèm `TaskUpdate` (R-84) |
| Ảnh không EXIF | Hoàn thành hiện trường vẫn xử lý bình thường |
| Hoàn thành hiện trường | Có GPS điện thoại mới, 1-5 ảnh; 0 ảnh hoặc 6 ảnh bị từ chối |
| Upload staging từng ảnh | Cross-user/cross-Task/expired/bound/tampered slot bị từ chối; retry chỉ gửi file lỗi; same idempotency key không tạo completion thứ hai; cleanup không xóa object đã bind |
| Draft ảnh nhạy cảm | Namespace account+Task; không GPS/token/presigned URL; xóa khi logout/account switch/finalize/7 ngày; quota/private-mode failure hiện đúng trạng thái |
| Manager override | Chỉ Manager, bắt buộc ghi chú, có AuditLog, chấp nhận 0 ảnh và không cần GPS |
| Assignee | `TaskAssignee` không có cột `status`; một người đóng task thì cả hai assignee thấy `COMPLETED`, báo cáo tách “được giao đã đóng” và “tự tay hoàn thành” |
| Task tương lai | Nhóm `UPCOMING`, không tính KPI hôm nay |
| Task quá hạn không đổi ngày | Task `assigned_date = today - 3` để qua ngày vẫn giữ nguyên `assigned_date`, nằm ở nhóm Quá hạn, response mang nhãn trễ `3` ngày tính lúc đọc; không job/endpoint nào `UPDATE assigned_date`; báo cáo của ngày `today - 3` vẫn đếm task đó (R-86) |
| RBAC | Mỗi action có test allow và deny ở backend |
| Token hết hạn | Access token quá 15 phút trả `401`; refresh hợp lệ đổi được cặp token mới |
| Xoay vòng refresh | Refresh token đã dùng một lần bị blacklist; dùng lại trả `401`, không cấp token mới |
| Thu hồi truy cập | Logout, Manager reset mật khẩu, user tự đổi mật khẩu, `is_active = False` — mỗi trường hợp blacklist toàn bộ refresh token của user và ghi `AuditLog`; refresh sau đó `401` |
| Logout thu hồi toàn bộ | User đăng nhập trên hai thiết bị rồi logout ở thiết bị A: refresh token của **cả hai** thiết bị đều `401`, không chỉ token gửi kèm request logout |
| Access token sau khi thu hồi | Sau logout/đổi mật khẩu, access token cũ **vẫn** gọi được endpoint nghiệp vụ cho tới khi hết 15 phút (hành vi đã chốt, không phải bug); nhưng sau `is_active = False` thì request kế tiếp trả ngay `401 ACCOUNT_INACTIVE` |
| Khóa tài khoản giữa chừng | Access token còn hạn nhưng `is_active = False`: request tiếp theo trả đúng `401 ACCOUNT_INACTIVE` (không phải `INVALID_TOKEN`, không phải `403`); server kiểm `is_active` sau khi giải mã |
| Bắt đổi mật khẩu | `must_change_password = True` gọi endpoint nghiệp vụ trả `403 PASSWORD_CHANGE_REQUIRED`; endpoint đổi mật khẩu vẫn gọi được và sau khi đổi thì cờ tắt, refresh token cũ bị thu hồi |
| Payload token | Không có claim `role`/permission; đổi role có hiệu lực ngay ở request kế tiếp, không cần phát lại token |
| Token không rò rỉ | Không có token trong log, `AuditLog` hay query string; client không ghi token vào `localStorage` |
| Server time | Client đổi `captured_at` không làm đổi `work_date`, late/early; giờ server UTC đổi đúng sang `Asia/Ho_Chi_Minh` |
| Nhiều lượt trong ngày | `IN → OUT → IN → OUT` đều thành công, tạo **hai** `AttendanceSession`, giờ công = tổng thời lượng phiên |
| Rời geofence trong ca | Check In tại A, làm Task ngoài 76 Location rồi Check Out tại B: session không tự đóng; `check_in_location_id=A`, `check_out_location_id=B`; duration không trừ thời gian ngoài geofence |
| Không còn unique cũ | Migration không có `UNIQUE(user_id, work_date, kind)`; Check In lượt hai trong ngày không lỗi unique |
| Check In khi đang mở phiên | Trả `409 SESSION_ALREADY_OPEN`, không tạo Attendance, ghi `AttendanceAttempt` |
| Check Out khi không có phiên mở | Trả `409 NO_OPEN_SESSION`, không tạo Attendance, ghi `AttendanceAttempt` |
| Duplicate Attendance | Hai Check In đồng thời: partial unique index chỉ cho một phiên mở, request thua nhận `SESSION_ALREADY_OPEN` |
| Anomaly theo ngày | `LATE_CHECK_IN` chỉ ở lượt IN đầu, `EARLY_CHECK_OUT`/`LATE_CHECK_OUT` chỉ ở lượt OUT cuối; lượt giữa ngày không sinh anomaly; bấm thêm cặp IN/OUT gỡ anomaly ra ca cũ |
| Vị trí mọi lượt | Lượt Check In thứ hai ngoài mọi bán kính vẫn bị `OUTSIDE_RADIUS` |
| Missing Check Out | Job cuối ngày đóng phiên mở: `MISSING_CHECK_OUT`, `check_out`/`duration_minutes` giữ `NULL`, `closed_by_job = True`, không cộng vào tổng giờ; hôm sau Check In được |
| Định nghĩa phiên mở | Sau job, `GET` trạng thái trả `has_open_session = false` và Check In hôm sau trả `201`, không dính partial unique index; điều kiện index trong migration có đủ `check_out IS NULL` **và** `closed_by_job = False` |
| Phiên không qua ngày | `AttendanceSession.work_date` luôn bằng `work_date` của Check In |
| Link bản đồ | `maps_url` dựng từ tọa độ bản ghi (không phải tọa độ `Location`), đúng dạng `https://www.google.com/maps?q={lat},{lng}` |
| Nearest cho early-gate attempt | `SESSION_ALREADY_OPEN`, `NO_OPEN_SESSION`, `WEAK_GPS` sau boundary có nearest; WEAK_GPS approximate; business gate không bị reorder |
| GPS foreground | watch chỉ khi Attendance visible, dừng ở hidden/rời màn/timeout/submit, không lưu fix, không auto chấm công, sample quá 60 giây không submit |
| Dashboard denominator | Trả numerator/eligible denominator/excluded choice/observed/nearest coverage; denominator 0 là `NULL`/`N/A` |
| Job health | Có last run/scanned/closed/anomaly/overdue-open/invariant; LEADER read-only không có account/AuditLog deep-link |
| Location concurrent edit | PATCH version cũ trả `409`; overlap recompute cùng transaction; reason giữ qua conflict; AuditLog before/after |
| Notification | Đúng recipient, dedupe, quiet-hours/TTL/suppression; logout/khóa revoke push; deep-link kiểm RBAC; không email/SMS |
| Export tọa độ | Mặc định loại tọa độ/Maps/photo/presigned URL; opt-in MANAGER/LEADER có audit metadata và `Cache-Control: no-store` |
| Địa chỉ xác nhận | `resolved_address` = tên + địa chỉ Location khi có `location`, `null` khi không; không có HTTP call ra dịch vụ geocoding |
| Task `BLOCKED` | Thiếu `block_reason` bị từ chối; chuyển lại `IN_PROGRESS` không tạo task mới |
| Task GPS thấp | `LOW_ACCURACY`/`UNRELIABLE` vẫn hoàn thành, giữ sai số và không tự gán Location |
| Lưu `location_candidates` | Hai ứng viên sau khi chọn: mảng lưu đủ hai id cùng Location được chọn; đổi `radius_m`/`is_active` sau đó không làm đổi lịch sử |
| Hai nhánh `location IS NULL` | Báo cáo và màn hình tách `gps_quality != GOOD` với `GOOD + []` (“ngoài mọi địa điểm”); không tồn tại completion `GOOD` có nhiều candidates nhưng chưa chọn |
| Thứ tự xét nhãn | Bản ghi `gps_quality = UNRELIABLE` với `location_candidates = []` hiện “GPS không đủ tin cậy”, **không** hiện “ngoài mọi địa điểm” — test này chốt thứ tự `gps_quality` trước mảng ứng viên |
| Complete Task đồng thời | Chỉ một request hoàn thành và tạo TaskUpdate COMPLETED |
| Permission implication | Đúng 5 cặp trong map, gồm `photo.view.all -> photo.view.self`; Leader `task.view.all` qua flow `task.view.self`; Manager `task.update.any` qua flow `.self`; action ngoài map không tự kế thừa |
| Leader read-only | Leader bị `403` trên mọi mutation, gồm `task.create.assign` và `task.update.any` |
| Gán vai trò | Manager gán `LEADER` và `HELPDESK` thành công kèm `AuditLog` (role cũ/mới); gán `MANAGER` trả `403 PERMISSION_DENIED` cả khi target là người khác lẫn khi target là chính actor; Leader/Helpdesk gọi endpoint gán vai trò đều `403` |
| Tạo/đổi vai trò không ra `MANAGER` | `POST /api/users/` và `PATCH /api/users/{id}/role` với `role = MANAGER` đều trả `403 PERMISSION_DENIED` (không phải `422`); sau request, DB không có thêm user `MANAGER` nào |
| Target `MANAGER` bất khả xâm phạm | Với target đang là `MANAGER`: update thông tin, đổi `is_active` (khóa lẫn mở khóa), reset mật khẩu, gán vai trò — cả bốn đều `403 PERMISSION_DENIED`, kể cả khi actor thao tác lên chính mình; nhưng `GET` danh sách và chi tiết vẫn trả tài khoản đó `200` |
| Payload lấn quyền ở sửa hồ sơ | `PATCH /api/users/{id}/` mang `role`, `password` hoặc `is_active` trả `400 SERVER_OWNED_FIELD`; `role = HELPDESK` (giá trị hợp lệ) gửi vào đây **cũng** `400` chứ không `403` — lỗi nằm ở *có mặt* trường, không ở giá trị; DB không đổi trường nào, không được im lặng bỏ qua rồi trả `200` |
| Kiểm quyền chạy trước kiểm trường | `PATCH /api/users/{id}/` lên target `MANAGER` mà payload có kèm `role` trả `403 PERMISSION_DENIED`, **không** phải `400 SERVER_OWNED_FIELD` (thứ tự action → target → payload, CHOT §8) |
| Luật target không đọc body | Cùng `PATCH` lên target `MANAGER` nhưng body **rỗng** cũng trả `403 PERMISSION_DENIED`: luật target nằm trong cổng phân quyền nên kết quả không phụ thuộc nội dung payload; guard đặt ở `permission_classes`/`has_object_permission`, không ở `serializer.validate()` (R-87) |
| Reset mật khẩu | `POST /api/users/{id}/reset-password` bật `must_change_password`, thu hồi toàn bộ refresh token của target, ghi `AuditLog` **không** chứa mật khẩu; target đăng nhập lại thì mọi endpoint nghiệp vụ trả `403 PASSWORD_CHANGE_REQUIRED` |
| Self tách khỏi quản trị | Manager đổi được mật khẩu và thông tin cá nhân của mình qua `/api/change-password/` và `/api/me/` dù mọi thao tác quản trị lên `MANAGER` bị chặn; hai endpoint self **từ chối** `user_id` gửi kèm payload bằng `400 SERVER_OWNED_FIELD` (không phải bỏ qua rồi trả `200`), luôn tác động đúng `request.user` (R-76) |
| Tự đổi mật khẩu cấp token mới | Sau `POST /api/change-password/`: refresh token **cũ** trả `401`, cặp `access` + `refresh` **mới** trong response dùng được ngay ở request kế tiếp; cả hai khẳng định trong cùng một test (R-78) |
| RBAC trước DTO | Actor thiếu quyền gửi body sai định dạng nhận `403 PERMISSION_DENIED`, **không** phải `400`: `HELPDESK` gọi `POST /api/users/` với body rỗng trả `403`, không trả lỗi `username field-required` (R-72) |
| Manager không chấm công | Manager gọi check in/check out trả `403 PERMISSION_DENIED`, không tạo `Attendance` lẫn `AttendanceAttempt`; nhưng `task.complete.field` (ảnh + GPS) vẫn `201`; bảng công và báo cáo §9 không có dòng nào của Manager |
| Không cấp trùng action | Role map của `MANAGER` **không** chứa trực tiếp `task.view.self`/`task.update.self`; `has_perm(manager, "task.view.self")` vẫn `True` nhờ `PERMISSION_IMPLIES` — kết quả giống hệt trước khi bỏ cấp trùng |
| Danh sách người dùng đóng với Leader | `LEADER` và `HELPDESK` gọi `GET /api/users/` và `GET /api/users/{id}/` đều `403 PERMISSION_DENIED`; chỉ `MANAGER` `200` |
| Mật khẩu do server sinh | `POST /api/users/` và `POST .../reset-password` trả mật khẩu đúng một lần trong response, hai lần gọi sinh hai chuỗi khác nhau; `GET` lại user không có trường mật khẩu; `AuditLog` và log ứng dụng không chứa chuỗi đó; gửi kèm `password` trong payload trả `400 SERVER_OWNED_FIELD` |
| Mật khẩu sinh bị chặn bởi cờ, không phải OTP | Đăng nhập bằng mật khẩu server sinh thành công **nhiều lần liên tiếp** (không bị vô hiệu sau lần đầu), nhưng mọi endpoint nghiệp vụ trả `403 PASSWORD_CHANGE_REQUIRED` cho tới khi đổi mật khẩu; `/api/change-password/` gọi được; sau khi đổi, đăng nhập bằng mật khẩu cũ trả `401 INVALID_CREDENTIALS` |
| Giao việc cho người đã khóa | `POST /api/tasks/` với `assignee_ids` chứa user `is_active = False` trả `422 INACTIVE_ASSIGNEE` kèm id vi phạm; sau request không có `Task` lẫn `TaskAssignee` nào được tạo — không được lọc bớt phần tử rồi trả `201` |
| Khóa không đụng task đang mở | Khóa một Helpdesk đang có task `TODO`/`IN_PROGRESS`: số dòng `TaskAssignee` và `Task.status` không đổi, task vẫn ở nhóm Quá hạn; báo cáo tháng trước của user đó giữ nguyên số liệu |
| Sửa task cũ có người đã nghỉ | `PATCH /api/tasks/{id}/` chỉ đổi tiêu đề/mô tả vẫn `200` dù trong assignee cũ có user đã khóa; chỉ id **mới thêm** bị validate |
| Picker lọc, danh sách không lọc | `GET /api/users/?role=HELPDESK&is_active=true` không trả user đã khóa; `GET /api/users/` không kèm filter vẫn trả đủ cả user đã khóa |
| Tạo user thiếu `role` | `POST /api/users/` không có `role` trả `400` với `{"role": ["This field is required."]}`; sau request DB không có user mới nào — đặc biệt không có user `HELPDESK` được điền mặc định |
| Chặn trước cổng thì không ghi attempt | Check In/Out không token, token hỏng, actor `MANAGER`, actor còn `must_change_password`, hoặc payload mang `kind`: đếm số dòng `AttendanceAttempt` trước và sau request phải bằng nhau (CHOT §5.1) |
| IDOR Task | Helpdesk đổi `task_id` sang task ngoài scope nhận `403`/`404`; anonymous bị chặn trước object query |
| Attendance self | Payload có `user_id` bị reject; bản ghi luôn thuộc authenticated actor |
| GPS input | NaN/Infinity, lat/lng ngoài miền, accuracy âm bị reject trước Haversine |
| GPS Config | Threshold/radius invalid bị reject; cấu hình Attendance nguy hiểm tạo warning rõ |
| Transition matrix | Test đủ transition hợp lệ; mọi `COMPLETED -> *` bị reject khi chưa có `task.reopen` |
| PostgreSQL race | `TransactionTestCase`/integration PostgreSQL chứng minh unique Attendance và chỉ một task completion thắng |
| Audit + outbox cùng rollback | Test PostgreSQL thật (`transaction=True`) chạy use case rồi ném lỗi **sau** khi cả hai port đã append: state nghiệp vụ không đổi, `AuditLog` không tăng dòng, `OutboxEvent` rỗng. Không được thay bằng mock hay SQLite (R-104) |
| Tương quan tới được sự kiện | Sự kiện sinh trong một request mang đúng `request_id` bằng header `X-Request-Id` của chính response đó; request kế tiếp không kế thừa id cũ; sự kiện sinh ngoài request có `request_id`/`correlation_id` rỗng mà vẫn append thành công |
| Payload cấm bị chặn ở port | Payload chứa token/mật khẩu/cookie/tọa độ/câu chữ push, khóa cấm lồng trong dict hay list, và chuỗi chứa `://` đều raise và **không** để lại dòng nào; thông báo lỗi chứa đường dẫn khóa nhưng không chứa giá trị; `must_change_password`/`active_refresh_sessions` vẫn ghi bình thường |
| Hai worker không sở hữu chéo | Test PostgreSQL thật (`transaction=True`) chạy **hai luồng** gặp nhau ở một `Barrier` rồi cùng claim: hai tập id **rời nhau**, mỗi bên đủ một lô, `leased_by`/`attempt_count`/`lease_expires_at` đọc lại từ DB đúng. Worker thứ hai **trả về ngay** chứ không xếp hàng sau khóa của worker thứ nhất — đó là chỗ phân biệt `SKIP LOCKED` với `FOR UPDATE` trần. SQLite không có `SKIP LOCKED` nên sẽ xanh sai (R-105) |
| Worker mất lease không ghi đè chủ mới | Worker A claim, dòng bị đẩy sang worker B (lease hết hạn, claim lại hợp lệ), rồi A mới ghi kết quả: lệnh ghi của A **không** vào được, state của B còn nguyên, kết quả lô đếm riêng một lần “mất claim” và có log record (R-105) |
| Transport ném defect không bỏ rơi lô | Transport thay thế ném thứ **không** phải `TransportError` giữa lô: các sự kiện sau vẫn được thử, dòng gặp defect được **trả claim** (`leased_by` rỗng, `lease_expires_at` rỗng, `next_attempt_at` không bị đẩy) chứ không bị chuyển thành lịch backoff, và defect vào log qua `logger.exception` (R-105) |
| Bộ số backoff phủ cửa sổ đã hứa | Tổng các khoảng chờ trong ngân sách thử lại `>=` cửa sổ gián đoạn đã cam kết, khoảng chờ cuối **bằng đúng** trần (trần có chạm tới, không phải trang trí), và dãy đơn điệu tăng (R-105) |
| Lease hết hạn thì phục hồi | Sự kiện đang có lease bị worker thứ hai claim **hụt**; đẩy `lease_expires_at` về quá khứ (đúng thứ xảy ra khi worker bị kill) thì worker thứ hai claim được ngay, `attempt_count` tăng — không thao tác vận hành nào ở giữa (R-105) |
| Transport hỏng thì không mất sự kiện | Transport thay thế hỏng có kiểm soát: sự kiện quay lại `PENDING`, `lease_expires_at` bị xóa, `last_error` có nội dung, `next_attempt_at` lùi đúng một bước backoff và **không bao giờ** vượt trần cấu hình; transport hồi phục thì sự kiện phát đúng một lần. Không đọc ngược state từ transport (R-105) |
| Hết lượt thì dead-letter thấy được | Thử tới hạn ngân sách: `publish_state = DEAD_LETTER`, dòng **vẫn còn** trong bảng, cảnh báo mang `event_id`, danh tính aggregate và số lần đã thử; `last_error` cùng bản ghi log **không** chứa `://`, giá trị token, mật khẩu hay tọa độ chính xác (R-105) |
| Phát lại thì consumer làm đúng một lần | Mô phỏng mất ack (sự kiện về `PENDING`, lease quá hạn) rồi chạy lại relay: transport nhận **hai** bản cùng `event_id`, lần đánh dấu thứ nhất trả `True`, lần thứ hai trả `False`, bảng khử trùng lặp có đúng một dòng; hai luồng chạy đua cũng cho đúng một `True` (R-105) |
| Cấu hình relay fail-closed | `OUTBOX_TRANSPORT` sai giá trị làm việc đọc cấu hình raise `RuntimeError` **nêu tên biến**; các số đếm bằng `0` cũng raise; mọi tên transport hợp lệ đều dựng được thật (R-105) |
| Ranh giới module có test gác | Test parse AST toàn cây production khẳng định không module nào import `models`/`domain`/`adapters` của module khác, kèm một test tự kiểm cho bộ gác một import vi phạm để nó không xanh vì không tìm thấy gì |
| `AuditLog` giữ nguyên hình dạng | Test pin đúng tập trường `{id, actor, action, target_type, target_id, before, after, recorded_at}` — thêm cột phải làm rơi test này trước khi rơi vào review |
| Bản ghi log mang tương quan | Bản ghi phát bên trong một binding mang đúng `request_id`/`correlation_id` của binding đó; bản ghi phát ngoài mọi binding mang **chuỗi rỗng** chứ không raise và không dựng id giả; cấu hình `LOGGING` thật sự gắn filter lên handler và khai báo đủ các logger đã đặt tên (R-106) |
| Metric ngoài từ vựng bị bỏ | Tên metric lạ, sai tập khóa nhãn, hoặc giá trị nhãn ngoài từ vựng đóng: hàm kiểm tra **raise**, còn hàm phát **không** để lại bản ghi metric nào và ghi đúng **một** cảnh báo chỉ nêu tên metric — không nêu giá trị nhãn đã bị từ chối (R-106) |
| Cảnh báo đã làm sạch | Text chẩn đoán chứa URL đã ký, `token=...` và tọa độ `10.785850` đi qua đường phát cảnh báo: bản ghi **không** còn URL, giá trị token hay tọa độ, nhưng **vẫn còn** phần chẩn đoán còn lại; kiểm cùng lúc trên `last_error`, bản ghi cảnh báo và `caplog.text` (R-106) |
| Dọn dẹp không chạm dòng cấm | Test PostgreSQL thật: dòng trong hạn sống sót, dòng quá hạn bị xóa đúng số lượng theo từng bảng, dòng `PENDING` **mọi tuổi** còn nguyên, dòng `AuditLog` còn nguyên, và tập lớn hơn kích thước lô vẫn bị xóa hết qua nhiều lô (R-106) |
| Thiếu quan trắc ra `unknown` | Chưa từng có dòng nhịp tim thì check là `unknown` **và** vẫn phát cảnh báo; nhịp tim cũ hơn ngưỡng là `alert`; nhịp tim mới là `ok`; trạng thái tổng hợp xếp `alert` > `unknown` > `ok`. Không trường hợp nào trong hai trường hợp đầu được báo `ok` (R-106) |
| Ghi quan trắc sống qua rollback | Test PostgreSQL thật (`transaction=True`): quan trắc đăng ký trong `business_transaction()` được ghi **sau** khi khối kết thúc ở cả nhánh commit lẫn nhánh exception, sống qua rollback của thay đổi nghiệp vụ, chạy **đúng một lần**, không sinh `OutboxEvent` và không sinh `AuditLog`; quan trắc tự ném lỗi thì được log mà **không** che exception nghiệp vụ gốc (R-106) |

## 8. Checklist review PR

- [ ] Không còn `BusinessLocation`, `PhysicalLocation`, `physical_location`,
  `exif_lat`, `exif_lng`, `exif_offset_m` trong mã mới.
- [ ] Không dùng GPS để tự chọn location khi có nhiều ứng viên INSIDE.
- [ ] `selected_location_id` được backend xác nhận lại.
- [ ] Attendance chặn accuracy trước geofence; Task classify quality trước và chỉ
  geofence khi `GOOD`.
- [ ] Cổng quality Attendance không áp lên Task completion; Task GPS thấp vẫn lưu
  đúng `gps_quality`, không bị đánh dấu GPS tốt hoặc tự gán Location.
- [ ] `recorded_at` do server tạo là nguồn tính công; client không gửi `work_date`.
- [ ] Bất biến “một phiên mở mỗi user” và atomic Task completion được kiểm ở
  database/transaction; không tái lập `UNIQUE(user_id, work_date, kind)`.
- [ ] Mọi chỗ hỏi “phiên đang mở” dùng đủ `check_out IS NULL AND
  closed_by_job = False`, kể cả điều kiện của partial unique index.
- [ ] Mọi request chấm công **đã qua xác thực/phân quyền** ghi một
  `AttendanceAttempt`, gồm cả `ACCEPTED`; `401`/`403`/payload sai **không** ghi
  attempt và chỗ gọi `create` nằm trong service, không ở middleware. Mã lỗi ngoài
  bán kính là `OUTSIDE_RADIUS`, lựa chọn sai là `INVALID_LOCATION_CHOICE`.
- [ ] `AttendanceAttempt` được ghi **ngoài** `transaction.atomic()` của nghiệp vụ,
  trên cả nhánh thành công lẫn nhánh `except`, nên rollback nghiệp vụ không xóa
  attempt (R-74).
- [ ] Tỉ lệ thất bại chấm công đếm đúng **năm** outcome từ chối (`WEAK_GPS`,
  `OUTSIDE_RADIUS`, `INVALID_LOCATION_CHOICE`, `SESSION_ALREADY_OPEN`,
  `NO_OPEN_SESSION`); `LOCATION_CHOICE_REQUIRED` bị loại khỏi **cả** tử số lẫn
  mẫu số (R-77).
- [ ] `TaskUpdate.location_candidates` được lưu lúc ghi nhận, không tính lại khi
  đọc; completion nhiều candidates bắt buộc đã có `location` + `USER_SELECTED`.
- [ ] AttendanceSession là ca làm: không theo dõi liên tục, không đóng khi rời
  geofence; API trả riêng `check_in_location_id`/`check_out_location_id` và
  duration là hiệu hai server timestamp, không trừ thời gian ngoài geofence.
- [ ] Anomaly ca làm tính theo ngày công (lượt IN đầu / lượt OUT cuối), không gắn
  vào từng lượt bấm.
- [ ] `maps_url`/`resolved_address` sinh ở serializer từ dữ liệu đã lưu; không cột
  DB mới, không gọi geocoding ngoài, link có `rel="noopener noreferrer"`.
- [ ] `BLOCKED` có lý do và mọi TaskStatus transition theo CHOT.
- [ ] `classify_geofence` chỉ so `distance_m <= radius_m`; không tham số
  `accuracy_m`, không cộng/trừ sai số vào bán kính.
- [ ] `LocationValidationResult` vẫn đúng hai giá trị; không có trạng thái thứ ba.
- [ ] Bất thường là `AttendanceAnomaly`, không thêm cờ boolean nguồn; nhật ký lần
  bấm chấm công là `AttendanceAttempt`, không trộn vào bảng anomaly.
- [ ] `kind` suy từ route, không có trong DTO/serializer input.
- [ ] Manager override có note + audit; báo cáo tách với field evidence.
- [ ] Permission được enforce trong backend service/API.
- [ ] Cấu hình `SIMPLE_JWT` ở một chỗ, refresh có blacklist ở server, thu hồi đi
  qua một helper duy nhất kèm `AuditLog`; token không chứa `role` và không xuất
  hiện trong log/URL/`localStorage`.
- [ ] Mọi request vẫn kiểm `is_active`/`must_change_password` sau khi giải mã
  token; mã lỗi tách đúng `401 INVALID_TOKEN` / `401 ACCOUNT_INACTIVE` /
  `403 PASSWORD_CHANGE_REQUIRED` / `403 PERMISSION_DENIED`.
- [ ] Ngưỡng GPS của Attendance và Task tách hẳn: không code nào đọc chéo hai bộ
  config, `Location.is_active` không nullable.
- [ ] Permission implication chỉ qua `PERMISSION_IMPLIES`; `*.self` luôn có
  object scope/ownership check sau RBAC.
- [ ] Attendance self lấy actor từ authentication; DTO/serializer reject mọi
  server-owned field client cố gửi.
- [ ] GPS input/config được validate ở boundary trước domain/Haversine.
- [ ] GPS event dùng `maximumAge=0`; mẫu quá 60 giây bị reject nhưng
  `captured_at` không được dùng thay server time.
- [ ] Ảnh camera/gallery chỉ JPEG/PNG/WebP, tối đa 5 MB/ảnh sau nén; backend kiểm
  lại type/size và không đọc EXIF cho nghiệp vụ.
- [ ] Password tối thiểu 12 ký tự, khác username, qua Django validators; sinh bằng
  `secrets`. Export quá 10.000 dòng bị từ chối và yêu cầu thu hẹp filter.
- [ ] Race condition quan trọng chạy `TransactionTestCase`/integration PostgreSQL,
  không chỉ mock hoặc SQLite.
- [ ] Kiểm quyền action chạy **trước** validate DTO: sai vai trò trả `403` kể cả
  khi body rỗng hay sai kiểu; kiểm quyền nằm ở `permission_classes`, không ở
  `serializer.validate()`/`perform_create()` (R-72).
- [ ] `AttendanceAnomalyReason` đúng **bốn** giá trị; không còn `OFF_ASSIGNMENT` ở
  enum, migration hay response (R-73).
- [ ] `PATCH /api/me/` và `POST /api/change-password/` trả
  `400 SERVER_OWNED_FIELD` khi payload mang `user_id`, không im lặng bỏ qua
  (R-76).
- [ ] Tự đổi mật khẩu thu hồi toàn bộ refresh token **rồi mới** cấp cặp token mới;
  test khẳng định refresh cũ chết và refresh mới dùng được (R-78).
- [ ] `punch_index` là giá trị dẫn xuất lúc đọc, một dãy duy nhất gồm cả IN lẫn
  OUT của `(user, work_date)` sắp theo `recorded_at`, bắt đầu từ 1; không phải cột
  DB (R-79).
- [ ] `POST /api/users/` bắt buộc đúng ba trường `username`, `full_name`, `role`;
  `username` bất biến sau khi tạo; `phone`/`email` nullable và không unique
  (R-80).
- [ ] Chỉ một `GET /api/users/` với filter tùy chọn; không endpoint picker riêng,
  không hardcode `is_active=True` vào queryset mặc định (R-81).
- [ ] Job cuối ngày chạy **mọi ngày**, quét `work_date < CURRENT_DATE`, không đọc
  `Holiday` và không có khái niệm ngày không làm việc (R-82).
- [ ] Sáu trường snapshot trên `Task` chỉ được ghi cùng transaction với
  `TaskUpdate` sinh ra chúng; `TaskUpdate` bất biến, không có endpoint gán
  Location sau completion (R-84, R-89).
- [ ] Job cuối ngày **luôn** ghi `AttendanceAnomaly(MISSING_CHECK_OUT)` cho mọi
  phiên nó đóng, kể cả `work_date` là Chủ nhật/ngày lễ; thân job không đọc
  `working_weekdays` lẫn `Holiday`; số `closed_by_job = True` bằng số anomaly
  (R-85).
- [ ] `Task.assigned_date` bất biến sau khi tạo: không job/endpoint nào `UPDATE`
  nó, không có `original_assigned_date`/`carried_over_count`/`due_date`; nhóm
  Quá hạn render trên nhóm Hôm nay và nhãn “trễ N ngày” tính lúc đọc (R-86).
- [ ] Luật “target là `MANAGER`” nằm trong cổng phân quyền
  (`permission_classes`/`has_object_permission`), chạy trước DTO validation nên
  body rỗng vẫn ra `403`; `SERVER_OWNED_FIELD` nằm **sau** cổng quyền, trong DTO
  validation (R-87).
- [ ] Thân lỗi dựng ở **một** helper duy nhất và luôn đủ `error_code`, `message`,
  `details`, `request_id` cộng mirror deprecated `error` + khóa lỗi theo trường ở
  cấp cao nhất; `csrf_failure` (dựng `JsonResponse` ngoài DRF) dùng đúng helper
  đó chứ không tự viết thân riêng (R-103).
- [ ] `request_id` do middleware sinh bằng `uuid4` mỗi request, echo ở
  `X-Request-Id`, và **không** đọc từ header client gửi lên (R-103).
- [ ] Mã lỗi là hằng ở `core/error_codes.py`, không phải chuỗi lặp rải trong
  view/serializer (R-103).
- [ ] Schema và client TypeScript được sinh lại và commit trong cùng thay đổi với
  code; sinh hai lần cho ra byte giống hệt nhau; CI gác drift và tương thích
  ngược (R-103).
- [ ] Không có hàm relay nào tên `append_*`; transaction claim không ôm lời gọi
  transport; mọi tiến độ của relay nằm ở cột đã commit chứ không ở biến trong bộ
  nhớ tiến trình (R-105).
- [ ] Backoff là hàm thuần có trần, và trần đến từ cấu hình chứ không phải hằng
  rải trong mã; cấu hình relay truyền vào bằng **một** dataclass frozen; bộ số
  mặc định phủ hết cửa sổ gián đoạn đã cam kết và có chạm tới trần (R-105).
- [ ] Mọi lệnh ghi lên dòng đã claim đều kèm điều kiện `leased_by` +
  `lease_expires_at` của claim; ghi hụt được đếm và log riêng chứ không tính là
  thành công/retry/dead-letter (R-105).
- [ ] Exception không phải `TransportError` được xử lý theo từng sự kiện, trả
  claim và không dừng lô (R-105).
- [ ] Khử trùng lặp dựa trên ràng buộc `UNIQUE(consumer, event_id)` với savepoint
  hấp thụ `IntegrityError`, không phải đọc-rồi-ghi; dấu khử trùng lặp nằm trong
  transaction của công việc nó bảo vệ (R-105).
- [ ] Cảnh báo dead-letter không có trường payload; `last_error` đi qua bộ làm
  sạch dùng chung và bị chặn độ dài (R-105).
- [ ] Test đồng thời/lease/retry chạy trên PostgreSQL thật với `transaction=True`
  và luồng thật; transport hỏng mô phỏng bằng substitute, không bằng broker
  (R-105).
- [ ] `request_id`/`correlation_id` lên bản ghi log bằng filter trong cấu hình
  `LOGGING`, không bằng cách truyền tay qua từng lời gọi; không có ngữ cảnh thì
  hai trường là chuỗi rỗng chứ không phải id dựng ra (R-106).
- [ ] Mọi metric mới khai báo tên **và** từ vựng đóng của từng nhãn trong
  registry; không nhãn nào nhận `event_id`, id người dùng, đường dẫn URL thô hay
  bất cứ giá trị không chặn trên nào (R-106).
- [ ] Mọi trường chuỗi của cảnh báo đi qua bộ làm sạch dùng chung; cảnh báo chỉ
  mang định danh, số đếm và ngưỡng — không payload, không URL, không đường dẫn
  request thô (R-106).
- [ ] Mọi điểm phát telemetry được chặn lỗi tại chỗ: một sink hỏng chỉ mất bản
  ghi quan trắc, không làm hỏng lô relay, response API hay thay đổi nghiệp vụ
  (R-106).
- [ ] Job dọn dẹp xóa theo lô, chỉ chạm `ProcessedEvent`, outbox đã publish và
  outbox ở trạng thái cuối; không truy vấn `PENDING`, không import `audit`, và
  báo cáo số dòng đã xóa theo từng bảng (R-106).
- [ ] Ngưỡng sức khỏe đọc bằng các helper `env_*` và fail-closed lúc khởi động;
  hàm đánh giá sức khỏe là hàm đọc thuần, không tự phát cảnh báo và không tự ghi
  gì, để endpoint đọc sau này dùng lại (R-106).
- [ ] Thiếu quan trắc trả `unknown` và vẫn cảnh báo; không nhánh nào coi “không
  có bản ghi” là `ok` (R-106).
- [ ] Ghi quan trắc của một thay đổi nghiệp vụ nằm **ngoài** transaction, ở cả
  hai nhánh, và không phải sự kiện outbox cũng không phải dòng `AuditLog`
  (R-106).

## 9. Công cụ ép tuân thủ

`pyproject.toml` dùng Ruff (line length 100, complexity tối đa 8, tối đa 4 tham
số, tối đa 25 statement) và mypy strict cho `domain/` và service. Hàm có tối đa
30 dòng thực; CI chạy script AST để kiểm vì Ruff không đếm dòng vật lý.

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "C4", "SIM", "ARG", "PL", "RUF"]

[tool.ruff.lint.pylint]
max-args = 4
max-statements = 25
max-branches = 8

[tool.ruff.lint.mccabe]
max-complexity = 8

[tool.mypy]
strict = true
files = ["backend/*/domain", "backend/*/application"]
```

ESLint frontend phải bật `max-lines-per-function` (30, ngoại lệ JSX component
80), `max-params` (4), `max-depth` (3), `complexity` (8), cấm `any` và cảnh báo
số ma thuật. Pre-commit chạy Ruff, format, kiểm độ dài hàm và kiểm `domain/`
không import Django/DRF/boto3.

**Artifact sinh tự động được miễn ngưỡng §4 và §9 (R-103).** Hai đường dẫn
`contracts/` và `frontend/src/shared/api/` chứa file do công cụ sinh ra
(`contracts/openapi.yaml`, `frontend/src/shared/api/schema.ts`); chúng được
**miễn** giới hạn độ dài hàm/file, complexity, `max-params` và lệnh cấm `any`, và
được liệt vào `globalIgnores` của ESLint. Lý do: không ai sửa tay được chúng —
sửa tay sẽ bị bước kiểm drift ở CI xóa ngay lần sinh sau — nên áp ngưỡng lên
chúng chỉ tạo ra lint error không có người sửa, hoặc tệ hơn, một chuỗi
`eslint-disable` rải trong file sinh. `globalIgnores` khai theo cả thư mục
(`src/shared/api/**`) chứ không theo từng file, nên lớp bọc viết tay
`frontend/src/shared/api/client.ts` cũng nằm ngoài tầm ESLint: nó vẫn phải tuân
đúng ngưỡng §4 (hàm ≤ 30 dòng, ≤ 4 tham số, không `any`) và điều đó được giữ bằng
review cùng `tsc --noEmit`, không phải bằng lint. File này vì thế phải mỏng — chỉ
là wrapper có kiểu quanh `authenticatedFetch`; logic nghiệp vụ nào lọt vào đây là
đặt sai chỗ. Đổi lại, hai đường dẫn trên phải được gác bằng kiểm drift ở CI: nội
dung của chúng luôn là kết quả sinh lại từ nguồn, không phải bản chỉnh tay.

## 10. Danh sách cấm

1. Logic nghiệp vụ trong view, serializer hoặc React component.
2. ORM/Django/DRF/boto3 import vào `domain/`.
3. Hàm quá 30 dòng, `except:` trần, cờ boolean tham số, trạng thái chuỗi thô.
4. Số ma thuật, N+1 query, `.date()` trên `DateTimeField` khi bật `USE_TZ`.
5. Lưu presigned URL vào DB, log URL ảnh hoặc tọa độ chính xác ở mức info.
6. Đưa lại EXIF GPS hoặc mô hình `BusinessLocation`/`PhysicalLocation`.
7. Chọn Location gần nhất/từ ngữ cảnh khi GPS có nhiều ứng viên INSIDE.
8. Thêm lại `UNCERTAIN` (hay trạng thái thứ ba nào khác) vào
   `LocationValidationResult`, hoặc trừ `accuracy_m` vào `radius_m` để thu hẹp
   effective radius.
9. Cài authorization chỉ ở frontend hoặc rải nhánh kiểm role trong các service.
10. Endpoint `.self` fetch object chỉ theo `id` mà không áp object scope/ownership.
11. Self Attendance nhận `user_id` client-side, hoặc client override trường
    server-owned qua JSON.
12. Dùng unit test/mock hoặc SQLite để tuyên bố đã kiểm chứng race condition
    PostgreSQL.
13. Thêm lại `UNIQUE(user_id, work_date, kind)` cho `Attendance`, hoặc chặn lượt
    Check In/Out thứ hai trong ngày bằng validate ở service.
14. Gắn anomaly đi muộn/về sớm/ra muộn vào lượt bấm giữa ngày, hoặc tính giờ công
    bằng hiệu giữa lượt đầu và lượt cuối thay vì tổng thời lượng phiên.
15. Bịa giờ Check Out cho phiên bị job đóng, hoặc coi `duration_minutes = NULL`
    là 0 khi cộng tổng.
16. Gọi API geocoding bên ngoài, nhúng iframe/SDK bản đồ, hoặc lưu
    `maps_url`/`resolved_address` thành cột database.
17. Hỏi phiên đang mở chỉ bằng `check_out IS NULL`, hoặc bỏ `closed_by_job` khỏi
    điều kiện partial unique index.
18. Chỉ ghi `AttendanceAttempt` cho request bị từ chối, bỏ qua `ACCEPTED`; lấy số
    ca công làm mẫu số cho tỉ lệ thất bại; hoặc đếm `LOCATION_CHOICE_REQUIRED`
    vào tử số hay mẫu số của tỉ lệ đó (R-77).
19. Trả `OUTSIDE_GEOFENCE` làm `error_code`, hay đặt thêm tên khác cho lỗi ngoài
    bán kính bên cạnh `OUTSIDE_RADIUS`.
20. Tính lại `location_candidates` khi đọc/hiển thị, thay nó bằng một cột đếm,
    kết luận “ngoài mọi địa điểm” chỉ từ `location IS NULL`, xét candidates trước
    `gps_quality`, hoặc commit completion nhiều candidates khi chưa chọn.
21. Cấu hình refresh token stateless (tắt `token_blacklist`), hoặc kéo dài
    `ACCESS_TOKEN_LIFETIME` để “đỡ phải refresh”.
22. Nhét `role`/permission vào payload JWT rồi phân quyền theo claim đó thay vì
    đọc DB.
23. Lưu token ở `localStorage`/`sessionStorage`, ghi token vào log/`AuditLog`,
    hoặc truyền token qua query string.
24. Tin token hợp lệ mà bỏ kiểm `is_active`/`must_change_password` (kể cả với lý
    do “không tra DB mỗi request”), hoặc tự blacklist token rải rác trong từng
    view thay vì gọi helper thu hồi chung.
25. Trả `INVALID_TOKEN` cho tài khoản bị khóa còn token hợp lệ, hoặc gộp
    `ACCOUNT_INACTIVE`/`PASSWORD_CHANGE_REQUIRED` vào một mã chung — client mất
    khả năng phân biệt và rơi vào vòng lặp refresh vô ích.
26. Đọc `task_gps_*` trong luồng Attendance, đọc `max_attendance_accuracy_m`
    trong luồng Task, hay gộp hai bộ ngưỡng thành một hằng số vì trùng giá trị
    mặc định.
27. Kiểm quyền action sau khi validate DTO — để `HELPDESK` gọi `POST /api/users/`
    body rỗng nhận `400 username field-required` thay vì `403 PERMISSION_DENIED`.
    Cụ thể: đặt kiểm quyền trong `serializer.validate()` hay `perform_create()`
    thay vì `permission_classes`/`check_permissions` (R-72).
28. Viết `AttendanceAttempt` bên trong `with transaction.atomic():` của luồng
    chấm công — request bị từ chối làm rollback luôn cả attempt nên báo cáo tỉ lệ
    thất bại rỗng. Attempt phải ghi ở **ngoài** transaction, trên **cả hai**
    nhánh commit và `except` (R-74).
29. Bỏ qua `user_id` trong payload `PATCH /api/me/` hoặc
    `POST /api/change-password/` một cách im lặng. Hai endpoint self này phải trả
    `400 SERVER_OWNED_FIELD` khi payload mang `user_id` (R-76).
30. Hardcode `is_active=True` vào queryset mặc định của `GET /api/users/`, hoặc
    dựng thêm một endpoint picker riêng. Chỉ có **một** endpoint danh sách user
    với filter tùy chọn `q`/`role`/`is_active`; client tự lọc ở màn giao việc,
    server vẫn chặn bằng `422 INACTIVE_ASSIGNEE` (R-81).
31. Cho job cuối ngày bỏ qua Chủ nhật, ngày có `Holiday`, hay bất kỳ khái niệm
    “ngày không làm việc” nào. Job quét theo `work_date < CURRENT_DATE` và
    **chạy mọi ngày** — phiên mở hôm thứ Bảy vẫn phải được đóng vào Chủ nhật
    (R-82).
32. Ghi `Task.status`, `completed_by`, `completed_at`, `completion_method`,
    `completion_note` hay `block_reason` mà không có `TaskUpdate` tương ứng sinh
    ra chúng trong **cùng** transaction; hoặc `UPDATE`/`DELETE` một `TaskUpdate`
    đã ghi ở bất kỳ trường nào ngoài `location` (R-84).
33. Đọc `Config.working_weekdays` hay `Holiday` ở bất kỳ đâu trong luồng chấm
    công, kể cả để quyết định *có ghi anomaly hay không*. Job luôn ghi
    `AttendanceAnomaly(MISSING_CHECK_OUT)` cho mọi phiên nó đóng; hai thứ đó chỉ
    phục vụ cấu hình và đọc báo cáo (R-85).
34. `UPDATE Task.assigned_date` để đẩy task quá hạn sang hôm nay, thêm cột
    `original_assigned_date`/`carried_over_count`, hay tách thêm cột `due_date`.
    Việc “task hôm trước chưa xong” hiển thị bằng nhóm Quá hạn đặt trên nhóm Hôm
    nay kèm nhãn “trễ N ngày” tính lúc đọc (R-86).
35. Đặt luật “target là `MANAGER` thì chặn” trong `serializer.validate()` /
    `perform_update()` thay vì `permission_classes`/`has_object_permission` —
    làm vậy thì DTO validation chạy trước và actor thiếu quyền nhận
    `400 SERVER_OWNED_FIELD` thay vì `403 PERMISSION_DENIED` (R-87). Ngược lại,
    cũng cấm mô tả `SERVER_OWNED_FIELD` như một ngoại lệ chạy **trước** cổng
    RBAC: nó nằm trong DTO validation, sau cổng quyền.
36. Đặt `transaction.atomic()` hoặc `transaction.on_commit()` bên trong
    `append_audit_entry`/`append_outbox_event`, hay ghi `AuditLog`/`OutboxEvent`
    bằng một transaction riêng “cho chắc”. Port tham gia unit of work của caller;
    commit riêng làm vết kiểm toán và sự kiện sống sót qua một rollback nghiệp vụ
    (CHOT §9.4, R-104).
37. Thêm cột vào `AuditLog` — kể cả `request_id`/`correlation_id` — để “tiện lần
    vết”. Hình dạng tám cột đã chốt ở CHOT §7; đổi nó là quyết định sản phẩm.
    Ngữ cảnh tương quan sống ở `OutboxEvent`.
38. Thêm tham số `request_id`/`correlation_id` vào DTO sự kiện rồi bắt từng use
    case chuyền tay qua các tầng, hoặc đọc header do client gửi lên làm
    `request_id`. Giá trị đến từ context ambient do middleware bind; id do server
    sinh (PRD NFR-18).
39. Coi `request_id`/`correlation_id` rỗng là lỗi: raise, chặn append, hay đặt
    cột thành nullable/`required`. Job, management command và shell không có
    request để mang id, và đó là trạng thái hợp lệ.
40. Lọc payload nhạy cảm ở call site thay vì ở port, nới bộ lọc thành khớp chuỗi
    con, hay đặt tên khóa vòng vo để lách bộ lọc. Cũng cấm đưa giá trị vi phạm
    vào thông báo lỗi hay log của chính bộ lọc — chống rò rỉ mà tự rò.
41. Ghi presigned URL, photo URL, Maps URL hay bất kỳ chuỗi chứa `://` vào
    `OutboxEvent.payload`/`AuditLog.before`/`after`, hoặc nhét nguyên trạng một
    row/DTO vào payload thay vì state tối thiểu consumer cần.
42. Import `models`/`domain`/`adapters` của module khác từ mã production, hoặc nới
    miễn trừ của test gác ranh giới ra ngoài ba mục đã chốt (`*/tests/*`,
    `*/migrations/*`, và composition root `config/`) để làm nó xanh.
43. Giữ tiến độ của relay ở ngoài PostgreSQL: bộ đếm số lần thử trong bộ nhớ,
    danh sách “đang xử lý” trong tiến trình, hay hỏi ngược transport xem sự kiện
    đã đi chưa. Tiến trình chết là mất sạch, còn công việc thì không (R-105).
44. Claim bằng `SELECT` thường rồi `UPDATE` (đọc-rồi-ghi), bỏ `skip_locked` để
    “cho chắc”, hay giữ transaction claim mở suốt lời gọi transport. Cái đầu cho
    hai worker cùng một sự kiện, cái thứ hai biến worker song song thành hàng
    đợi, cái thứ ba biến broker chậm thành database treo (R-105).
45. Thay lease bằng một bước “nhả việc” khi tắt máy, hay bắt vận hành vào DB gỡ
    tay sự kiện kẹt. Worker bị `kill -9` không nhả gì cả; quyền sở hữu phải tự
    hết hạn (R-105).
46. Backoff không trần, hoặc `sleep` trong luồng relay thay vì ghi
    `next_attempt_at`. Cả hai đều là mất sự kiện dưới một cái tên khác (R-105).
47. Xóa dòng khi hết lượt thử, hay để sự kiện thất bại nằm im ở `PENDING` mà
    không có trạng thái cuối và không có cảnh báo. Bỏ qua trong im lặng là hỏng
    nặng hơn báo lỗi (R-105).
48. Đặt payload, URL, token hay tọa độ vào cảnh báo/log của relay — kể cả bằng
    cách chuyển nguyên văn thông báo lỗi của transport vào `last_error` mà không
    làm sạch, hoặc lưu nó không chặn độ dài (R-105).
49. Cho `OUTBOX_TRANSPORT` sai giá trị rơi về mặc định thay vì dừng tiến trình,
    hay chấp nhận `0` cho kích thước lô / lease / số lần thử với ý “không giới
    hạn”. Cả hai đều để một triển khai tưởng mình đang phát sự kiện (R-105).
50. Khử trùng lặp bằng đọc-rồi-ghi, bằng khóa chính của bảng outbox, hay bằng
    thời điểm nhận thay vì `event_id`; hoặc ghi dấu khử trùng lặp ngoài
    transaction làm việc. Sự kiện bị đánh dấu “đã xử lý” trong khi chưa xử lý gì
    thì mọi lần phát lại sau đó đều bị chặn (R-105).
51. Viết consumer dựa vào thứ tự toàn cục giữa các aggregate. Thứ tự chỉ có
    trong phạm vi `(aggregate_type, aggregate_id)` theo `aggregate_version`
    (R-105).
52. Đặt tên hàm relay theo dạng `append_*`, hay nhét logic nghiệp vụ vào
    management command chạy relay. Cái đầu làm test gác AD-4 hiểu nhầm, cái sau
    đẩy quyết định vào chỗ không ai test (R-105).
53. Ghi kết quả lên một dòng đã claim mà **không** kèm điều kiện danh tính của
    claim (`leased_by` + `lease_expires_at` đã claim theo) trong `WHERE`. Lease
    hết hạn là chuyện được phép xảy ra; ghi vô điều kiện sau đó là cách đưa một
    dòng `PUBLISHED` về `PENDING`, hoặc `DEAD_LETTER` một sự kiện đã gửi xong
    (R-105).
54. Để một exception không phải `TransportError` thoát ra khỏi vòng lặp lô: mọi
    sự kiện đã claim còn lại bị bỏ rơi với lease đang giữ và một lượt thử đã
    tiêu. Bắt theo từng sự kiện, `logger.exception`, trả claim, chạy tiếp — và
    **không** biến defect của adapter thành lịch backoff như thể hạ tầng hỏng
    (R-105).
55. Phát metric với nhãn không khai báo trước, hoặc với giá trị nhãn không nằm
    trong từ vựng đóng — `event_id`, id người dùng, đường dẫn URL thô, tọa độ,
    tên file ảnh; đưa payload, URL, token, cookie, mật khẩu hay đường dẫn
    request thô vào một cảnh báo; để một điểm phát telemetry ném lỗi ra ngoài và
    làm hỏng việc mà nó đang quan sát; xóa dòng `PENDING` hay dòng `AuditLog`
    trong job dọn dẹp; và **coi việc không có bản ghi quan trắc là `ok`**. Ba
    cái đầu làm hỏng chính hệ thống quan trắc (cardinality không chặn trên, dữ
    liệu cấm rò ra ngoài, telemetry giết công việc); cái thứ tư là mất sự kiện
    và mất bằng chứng audit; cái cuối là dựng một bảng điều khiển xanh cho một
    job chưa từng được lên lịch (R-106).
56. Đọc một biến môi trường của phần triển khai bằng `os.environ.get` trần thay
    vì qua lớp kiểm tra fail-closed (`core/deployment.py`, `env_choice`,
    `env_positive_count`), hoặc ném ra một thông báo thất bại **không gọi tên
    biến sai**; commit một giá trị bí mật vào bất kỳ file nào — kể cả bản kê môi
    trường, vốn chỉ được chứa danh tính (mã project, tên bucket, tiền tố key,
    **tên** header credential); điền một giá trị đoán tạm vào chỗ đang chờ người
    có thẩm quyền quyết thay vì để `UNRESOLVED`; dùng chung một chuỗi kết nối
    cho cả đường runtime lẫn đường quản trị database, hoặc đọc chuỗi kết nối
    quản trị từ mã ứng dụng; gắn credential nguồn ở biên mà **không xóa header
    cùng tên do client gửi lên trước**, log nó, echo nó lại trên response, hay
    đặt nó dưới tiền tố `NEXT_PUBLIC_`; và để một response `/api/v1/` cache
    được. Cái đầu biến một cấu hình sai thành sự cố lúc chạy thay vì một lần từ
    chối khởi động có địa chỉ; cái thứ hai và thứ ba là hai cách khác nhau để
    một bí mật hoặc một quyết định chưa ai làm đi thẳng ra production; cái thứ
    tư xóa ranh giới giữa quyền đọc-ghi dữ liệu và quyền đổi schema mà không làm
    thay đổi bất cứ thứ gì quan sát được; cái thứ năm khiến câu trả lời của lớp
    chặn phụ thuộc vào request thay vì vào triển khai, tức là không chặn gì cả;
    cái cuối phục vụ dữ liệu của một phiên đã xác thực cho phiên kế tiếp (R-107).
57. Ghi một lần khôi phục hay một lần đo năng lực là `passed` khi số đo vượt mục
    tiêu, hoặc để trống kết luận và người chịu trách nhiệm khắc phục; trỏ công cụ
    kiểm tra bản khôi phục vào chuỗi kết nối runtime hay chuỗi kết nối quản trị,
    hoặc thêm một alias `DATABASES` cho chúng; **ghi bất cứ thứ gì** vào database
    đang được kiểm tra sau khôi phục; thêm một cột `NOT NULL` không có
    `db_default`, để một app có nhiều hơn một migration lá, hay gộp thao tác thu
    hẹp (xóa cột, xóa bảng) vào cùng migration với thao tác mở rộng; và in ra
    chuỗi kết nối, token, mật khẩu, giá trị header credential hay URL có kèm
    thông tin đăng nhập từ bất kỳ công cụ nào của mục này. Cái đầu biến một rủi
    ro đã biết thành một rủi ro đã có người ký nhận là không tồn tại; cái thứ hai
    và thứ ba khiến một lần diễn tập luôn xanh mà không chứng minh gì, hoặc sửa
    chính bản gốc đang phục vụ; cái thứ tư làm hỏng tiến trình phiên bản cũ ngay
    giữa lúc rollout, khi hai phiên bản cùng nói chuyện với một schema; cái cuối
    biến một báo cáo dán vào ticket thành một credential còn dùng được (R-108).
58. Để bộ đếm throttle nằm ở cache cục bộ theo tiến trình ngoài `development` —
    hoặc nới lỏng phép kiểm đó theo `DJANGO_DEBUG` thay vì theo môi trường đã
    được kiểm hợp lệ (`IS_DEVELOPMENT`); đọc `DJANGO_CACHE_BACKEND` bằng
    `os.environ.get` trần thay vì `env_choice` với từ vựng đóng; viết thẳng chuỗi
    `"default"` ở lớp throttle hay ở phép kiểm khởi động thay vì đọc
    `THROTTLE_CACHE_ALIAS`, và sao chép từ vựng backend vào
    `scripts/deployment_check.py` thay vì import từ `core/cache.py`; đặt tên bảng
    cache thành một giá trị cấu hình để settings và migration có thể lệch nhau;
    nhập bất cứ thứ gì của Django vào `core/cache.py`; và bọc lỗi cache bằng một
    nhánh fail-open để request vẫn qua khi kho đếm không với tới được. Cái đầu
    nhân hạn mức công bố lên theo số instance và xóa sạch bộ đếm sau mỗi lần khởi
    động lại; cái thứ hai biến một biến gỡ lỗi thành công tắc của một biện pháp
    an ninh; cái thứ ba khiến một giá trị sai chính tả đi thẳng vào production
    thay vì bị từ chối ngay lúc khởi động; cái thứ tư để lớp throttle đếm ở một
    alias còn phép kiểm khởi động soi một alias khác, nên bộ đếm nằm trong kho
    không ai kiểm; cái thứ năm và thứ sáu để hai chỗ cùng mô tả một sự thật rồi
    trôi khỏi nhau; cái thứ bảy làm `deployment_check.py` không chạy nổi ngoài
    Django; cái cuối biến một sự cố hạ tầng thành một cửa mở không hạn mức
    (R-109).
