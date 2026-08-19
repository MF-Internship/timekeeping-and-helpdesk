# Chốt yêu cầu — Phần mềm chấm công & quản lý công việc Helpdesk

> Trạng thái: nguồn sự thật triển khai. Mọi thay đổi nghiệp vụ mới phải cập nhật
> tài liệu này trước, rồi mới cập nhật PRD, quy tắc code và kiểm thử.

## 1. Stack bắt buộc

| Lớp | Công nghệ |
|---|---|
| Frontend | Next.js |
| Backend | Django REST Framework |
| Database | PostgreSQL |
| Lưu ảnh | S3 (AWS) hoặc R2 (Cloudflare) |

Quy mô MVP khoảng 50 người dùng. Không cần PostGIS/GeoDjango: vòng lặp
haversine trên 76 điểm chạy dưới 1 ms.

## 2. Phạm vi và dữ liệu nguồn

- Web app cho khoảng 50 người dùng: `LEADER`, `MANAGER`, `HELPDESK`.
- [dia_chi_ttkd.csv](dia_chi_ttkd.csv): 7 trung tâm kinh doanh (TTKD). Cả hai file
  đều dùng dấu chấm thập phân; ba dòng TTKD (`HCM010000`, `HCM050000`,
  `HCM070000`) có 15 chữ số thập phân. Seed parse bằng `float`/`Decimal`, không
  làm tròn và không đổi giá trị.
- [dia_chi_cua_hang.csv](dia_chi_cua_hang.csv): 69 cửa hàng, không thiếu tọa độ và
  không trùng mã.
- Seed giữ nguyên **76 `Location`**. Không gộp theo địa chỉ, không tạo
  `PhysicalLocation`, không sửa tọa độ gốc CSV.
- Tọa độ là nguồn sự thật cho kiểm tra vị trí; `address` và `name` là chuỗi hiển
  thị và **không** được dùng để suy luận nghiệp vụ.

Hai CSV đã được làm sạch; seed đọc bằng `csv` stdlib. Năm điểm `HCM07xxxx` ở Bà
Rịa - Vũng Tàu/Côn Đảo không phải lỗi dữ liệu: tiền tố `HCM` là mã tổ chức, không
phải mã địa lý.

**Mapping header (chốt).** Hai file **không** dùng chung tên cột: file TTKD có
thêm cột `STT` và đặt tên tiếng Việt, file cửa hàng đặt tên tiếng Anh. Seed phải
khai báo mapping riêng cho từng file; đọc file TTKD bằng header của file cửa hàng
sẽ trả `None` toàn bộ và **âm thầm seed thiếu 7 TTKD** — khi đó mọi cửa hàng cũng
mất `parent`, nên đây là lỗi phải chặn chứ không phải cảnh báo.

| Trường `Location` | `dia_chi_ttkd.csv` | `dia_chi_cua_hang.csv` |
|---|---|---|
| `code` | `Mã TTKD` | `SHOP_CODE` |
| `name` | `Tên` | `NAME` |
| `address` | `ADDRESS` | `ADDRESS` |
| `latitude` | `LATITUDE` | `LATITUDE` |
| `longitude` | `LONGITUDE` | `LONGITUDE` |
| `kind` | hằng `BUSINESS_CENTER` | hằng `SHOP` |
| `parent` | luôn `NULL` | suy từ `SHOP_CODE[:5] + '0000'` |
| `radius_m` | `Config.default_radius_m` | `Config.default_radius_m` |
| `is_active` | `True` | `True` |

Cột `STT` của file TTKD **bị bỏ qua**: nó là số thứ tự trình bày, không phải khóa
nghiệp vụ. `kind` và `radius_m` không có trong CSV nên suy từ nguồn file và
`Config`, không thêm cột vào CSV.

Seed **kiểm header trước khi đọc dòng đầu tiên**: thiếu bất kỳ cột nào trong
mapping của file đó thì dừng ngay với thông báo nêu tên file và tên cột thiếu.
Sau khi seed xong, khẳng định đúng **7** `BUSINESS_CENTER` và **69** `SHOP`; lệch
số là dừng, không seed một phần. Cấm dò header kiểu “thử `SHOP_CODE`, không có
thì thử `Mã TTKD`” — mapping gắn với file, không đoán theo nội dung.

**Quy tắc suy TTKD cha.** `Location.parent` biểu diễn phân cấp TTKD và được suy
bằng `SHOP_CODE[:5] + '0000'`. Quy tắc này áp dụng cho *toàn bộ* 69 cửa hàng,
không có ngoại lệ hard-code:

- Mã là nguồn sự thật cho phân cấp. `HCM020129` mang tên hiển thị “Cửa hàng Lê Văn
  Duyệt (MobiFone TTKD Sài Gòn)” nhưng mã `HCM02…` nên `parent = HCM020000`
  (TTKD Gia Định). Không sửa dữ liệu theo tên.
- Nếu mã suy ra không khớp `Location` TTKD nào thì `parent = NULL`; seed không
  được tự bịa cha. `HCM000079` (`HCM00…` → `HCM000000` không tồn tại) là trường
  hợp duy nhất hiện nay và là hợp lệ.
- Bảy dòng TTKD có `parent = NULL`; không áp quy tắc trên cho chính chúng để tránh
  tự làm cha của mình.

**Trùng tọa độ.** `HCM000079` và `HCM010005` có cùng địa chỉ và **cùng tọa độ**
(khoảng cách 0 m). Đây là cặp trùng duy nhất và là dữ liệu hợp lệ: xem §3.1.

## 3. Mô hình địa điểm duy nhất

Mỗi TTKD hoặc cửa hàng là đúng một `Location`, có geofence riêng. Không còn hai
khái niệm “đơn vị nghiệp vụ” và “mặt bằng vật lý”.

```text
Location (76 bản ghi)
  code, name, kind, parent?, address
  latitude, longitude, radius_m, is_active
```

Tập này là tập đóng đúng 76 bản ghi từ hai CSV canonical. Không có thao tác tạo
`Location` thủ công hoặc `POST /api/v1/locations/`; Manager chỉ được sửa các
field cho phép qua `PATCH` và seed chạy lại có quyền khôi phục field do
nguồn/config sở hữu (R-113).

```python
class LocationKind(models.TextChoices):
    BUSINESS_CENTER = "BUSINESS_CENTER", "Trung tâm kinh doanh"
    SHOP = "SHOP", "Cửa hàng"
```

### 3.1 Geofence và địa chỉ trùng nhau

`Location.radius_m` là bán kính geofence có hiệu lực của từng địa điểm. Giá trị
seed là `Config.default_radius_m = 50`; quản lý có thể sửa từng địa điểm, không
vượt `Config.max_radius_m = 70`. Không hardcode các số này trong nghiệp vụ.

Nhiều `Location` có thể cùng địa chỉ, cùng tọa độ hoặc có geofence giao nhau. Đây
là dữ liệu hợp lệ: ví dụ một TTKD và một cửa hàng cùng địa chỉ vẫn là hai đơn vị,
hai dòng dữ liệu, hai geofence. Validator chỉ cảnh báo khi hai geofence giao nhau;
không tự gộp và không chặn lưu.

Điều kiện duy nhất **chặn** seed/import về mặt định danh là **trùng
`Location.code`** — mã là khóa nghiệp vụ và là căn cứ chạy idempotent (§9.3).
Trùng tọa độ hoặc geofence chồng nhau chỉ cảnh báo: dữ liệu thật có đúng một cặp
trùng tọa độ tuyệt đối (`HCM000079` và `HCM010005`), chặn theo tọa độ sẽ không
seed đủ 76 địa điểm.

Khi GPS nằm trong từ hai `Location` trở lên, luồng **chấm công** bắt người dùng
chọn đúng đơn vị. Không tự suy luận bằng khoảng cách gần nhất, lịch sử, TTKD hay
task đang mở. Backend phải kiểm tra lựa chọn thuộc tập ứng viên hợp lệ. Luồng
**hoàn thành công việc tại hiện trường** không chặn — xem §6.2.

Ba cặp địa điểm sau đây luôn hoặc thường sinh nhiều ứng viên với
`radius_m = 50`; đây là hành vi mong đợi, không phải lỗi:

| Cặp | Khoảng cách | Hệ quả |
|---|---:|---|
| `HCM000079` ↔ `HCM010005` | 0 m | Luôn có đúng 2 ứng viên, **không bao giờ** `AUTO_SINGLE` |
| `HCM030015` ↔ `HCM030000` | 4.8 m | Luôn có đúng 2 ứng viên |
| `HCM010018` ↔ `HCM010000` | 47.1 m | Có 2 ứng viên khi đứng giữa hai tâm |

`HCM000079` và `HCM010005` trùng cả địa chỉ lẫn tọa độ, nên UI chọn địa điểm
**bắt buộc** hiển thị `code` cùng `name`; chỉ hiện địa chỉ hoặc khoảng cách là
không đủ để người dùng phân biệt.

## 4. GPS là nguồn vị trí duy nhất

Ảnh không dùng EXIF để lấy hoặc đối chiếu vị trí. Khi Check In, Check Out hoặc
hoàn thành công việc tại hiện trường, client lấy một mẫu từ GPS điện thoại bằng
Geolocation API và gửi cùng request:

```text
latitude, longitude, accuracy_m, captured_at
```

- `captured_at` là thông tin audit/debug do client gửi; không dùng để tính công.
  Client phải xin mẫu mới với `maximumAge=0`; mẫu gửi lên quá 60 giây so với lúc
  server nhận bị từ chối và phải đo lại. Trường này không thay thế server time và
  không quyết định `work_date`/anomaly.
- Attendance chỉ chấp nhận `accuracy_m <= Config.max_attendance_accuracy_m = 25`.
- Mẫu GPS dùng cho hoàn thành hiện trường phải được lấy ngay trước khi gửi; client
  không tái sử dụng mẫu cũ trong phiên.
- Ảnh chỉ là bằng chứng hình ảnh: nén rồi upload, không đọc/lưu `exif_lat`,
  `exif_lng`, `exif_offset_m`, và không có luật EXIF mismatch.
- Khi một `Location` được xác định, địa chỉ hiển thị lấy từ `Location.address`.
  Khi không có địa điểm khớp, báo cáo giữ tọa độ GPS; MVP không gọi dịch vụ
  reverse-geocoding.

### 4.1 Chất lượng GPS cho Attendance và Task là hai luật khác nhau

`Attendance` dùng GPS để xác thực vị trí tính công nên có quality gate nghiêm
ngặt. `FIELD_EVIDENCE` dùng GPS làm bằng chứng thực hiện nên không bị chặn chỉ vì
tín hiệu yếu: client cảnh báo và mời lấy lại mẫu, nhưng vẫn cho hoàn thành nếu
còn thiếu chất lượng.

Hai luồng đọc **hai config khác nhau**, nên bảng dưới đây tách hẳn cột điều kiện;
không có dòng nào dùng chung ngưỡng:

| Điều kiện Attendance | Attendance | Điều kiện Task `FIELD_EVIDENCE` | Task `FIELD_EVIDENCE` |
|---|---|---|---|
| `accuracy_m <= Config.max_attendance_accuracy_m` (mặc định 25) | Qua quality gate, được xét geofence | `accuracy_m <= Config.task_gps_good_accuracy_m` (mặc định 25) | `gps_quality = GOOD`, được xét geofence |
| `accuracy_m > Config.max_attendance_accuracy_m` | Từ chối `WEAK_GPS` | `task_gps_good_accuracy_m < accuracy_m <= Config.task_gps_low_accuracy_m` (mặc định 100) | `gps_quality = LOW_ACCURACY`, cảnh báo nhưng vẫn hoàn thành |
| — (Attendance chỉ có hai nhánh) | — | `accuracy_m > Config.task_gps_low_accuracy_m` | `gps_quality = UNRELIABLE`, cảnh báo nhưng vẫn hoàn thành |

Threshold Attendance là `Config.max_attendance_accuracy_m` và threshold Task là
`Config.task_gps_good_accuracy_m`; hai giá trị mặc định đều bằng 25 nhưng là hai
field độc lập, không được hardcode và không được dùng thay cho nhau. Attendance
**không** đọc `task_gps_*` và Task **không** đọc `max_attendance_accuracy_m` —
Manager có thể chỉnh một bên mà không được kéo theo bên kia. Attendance cũng
không có khái niệm `LOW_ACCURACY`: chỉ có đạt hoặc `WEAK_GPS`.

Với `LOW_ACCURACY` hoặc `UNRELIABLE`, backend lưu nguyên tọa độ/sai số nhưng
không tự gán `TaskUpdate.location` và không coi là xác minh geofence. Báo cáo
phải lọc/nhóm theo `gps_quality`; không được hiển thị các bản ghi này như GPS tốt.

```python
class TaskGpsQuality(models.TextChoices):
    GOOD = "GOOD", "GPS tốt"
    LOW_ACCURACY = "LOW_ACCURACY", "GPS sai số cao"
    UNRELIABLE = "UNRELIABLE", "GPS không tin cậy"
```

### 4.2 Luật geofence: hai cổng độc lập

Sai số GPS là **quality gate riêng**, không được dùng để thu hẹp bán kính hiệu
lực. Với khoảng cách `d`, sai số `a`, bán kính `r` và threshold chất lượng `t`:

```text
Cổng 1 (chất lượng):  a <= t
Cổng 2 (vị trí):      d <= r  ->  INSIDE_GEOFENCE
                      d >  r  ->  OUTSIDE_GEOFENCE
```

`LocationValidationResult` chỉ có hai giá trị: `INSIDE_GEOFENCE` và
`OUTSIDE_GEOFENCE`. **Không có `UNCERTAIN`.** Công thức cũ `d + a <= r` /
`d - a > r` đã bị bãi bỏ vì nó biến sai số thành khoản trừ vào bán kính: với
`r = 50` và `a = 25`, nhân viên phải đứng trong vòng 25 m tính từ tâm dù bán kính
cấu hình là 50 m.

- **Attendance**: phải qua cả hai cổng. Trượt cổng 1 → từ chối `WEAK_GPS`. Qua
  cổng 1 nhưng không có ứng viên `INSIDE_GEOFENCE` → từ chối `OUTSIDE_RADIUS`.
- **Task `FIELD_EVIDENCE`**: cổng 1 không chặn, chỉ gán `gps_quality` (§4.1). Chỉ
  khi `gps_quality = GOOD` mới chạy cổng 2. Ngược lại `location = NULL` và
  `validation_result = NULL`.

### 4.3 Validation GPS và Config

Tại API boundary, trước Haversine/geofence, mọi GPS payload phải thỏa:

```text
latitude   là số hữu hạn, -90 <= latitude <= 90
longitude  là số hữu hạn, -180 <= longitude <= 180
accuracy_m là số hữu hạn, accuracy_m >= 0
```

Từ chối `NaN`, `Infinity`, `-Infinity` và mọi giá trị ngoài miền. Domain service
chỉ nhận `ValidatedPosition`, không tự xử lý JSON/raw input.

Config bắt buộc thỏa toàn bộ bất biến sau, kiểm ở model `clean()` và ở
serializer:

```text
radius_m > 0
default_radius_m > 0  và  default_radius_m <= max_radius_m
max_radius_m > 0
max_attendance_accuracy_m > 0
task_gps_good_accuracy_m > 0
task_gps_low_accuracy_m > 0
task_gps_good_accuracy_m <= task_gps_low_accuracy_m
late_grace_minutes >= 0
early_checkout_grace_minutes >= 0
late_checkout_grace_minutes >= 0
shift_start < shift_end          (MVP không hỗ trợ ca qua ngày)
```

**Cấu hình vận hành nguy hiểm.** Với luật hai cổng ở §4.2, quan hệ giữa
`max_attendance_accuracy_m` và `radius_m` không còn làm Attendance bất khả thi.
Điều kiện cần cảnh báo giờ là `radius_m` quá nhỏ so với sai số GPS thực tế mà
điện thoại đạt được. Ranh giới xử lý:

| Nơi phát sinh | Hành vi |
|---|---|
| Seed và import CSV | **Dừng** nếu vi phạm bất biến Config ở trên |
| Seed và import CSV | **Dừng** nếu `radius_m <= 0` hoặc `radius_m > max_radius_m` |
| Manager sửa Config/`Location.radius_m` qua UI | **Cảnh báo rõ**, không chặn, khi `radius_m < max_attendance_accuracy_m` |
| Mọi nơi | Geofence overlap chỉ **cảnh báo** |

Không biến cảnh báo thành DB constraint khi nghiệp vụ chưa chốt nó là bất biến
cứng; ngược lại, không cho dữ liệu vi phạm bất biến cứng đi vào hệ thống qua
seed/import.

**Hạ trần bán kính Config (chốt, R-114).** `Location.radius_m <=
Config.max_radius_m` là bất biến trên **toàn bộ** 76 Location, không chỉ các dòng
đang hoạt động. `PATCH /api/v1/config/` làm `max_radius_m` thấp hơn bán kính của
bất kỳ Location hiện hữu nào bị từ chối nguyên tử bằng `400 VALIDATION_FAILED`;
`details` nêu field `max_radius_m` và danh sách `id`/`code` vi phạm nhưng không
chứa tọa độ. Server không tự thu nhỏ Location, không ghi Config/AuditLog/
OutboxEvent và không tăng aggregate version. Giá trị bằng bán kính lớn nhất hiện
có là hợp lệ. Kiểm tra này chạy sau RBAC/DTO nhưng trong transaction đã khóa
Config; mọi Location update cũng khóa Config trước Location để kết quả tuyến tính
dưới cạnh tranh.

## 5. Chấm công

Đối tượng chấm công trong MVP là **`HELPDESK`**. `MANAGER` và `LEADER` không
chấm công (§8) — mọi công thức, báo cáo và job ở phần này chỉ chạy trên dữ liệu
của Helpdesk, nên không cần lọc role ở từng truy vấn.

### 5.1 Luồng Check In / Check Out

1. Server tạo `recorded_at` theo UTC, đổi sang `Asia/Ho_Chi_Minh` để xác định
   `work_date` và tính anomaly ca làm. Không dùng `captured_at` của client.
2. `kind` được suy từ route (`/check-in` → `IN`, `/check-out` → `OUT`), không nhận
   từ payload. Kiểm quyền `attendance.check_in.self` hoặc
   `attendance.check_out.self`.
3. Check In chỉ hợp lệ khi user **không có phiên đang mở**; nếu đang có, từ chối
   `SESSION_ALREADY_OPEN` (§5.3).
4. Check Out chỉ hợp lệ khi user **đang có đúng một phiên mở**; nếu không, từ chối
   `NO_OPEN_SESSION`.
5. Cổng chất lượng: `accuracy_m <= Config.max_attendance_accuracy_m`. Trượt →
   từ chối `WEAK_GPS`.
6. Tính khoảng cách tới **toàn bộ `Location` đang hoạt động** (`is_active = True`).
7. Lấy các ứng viên có `distance_m <= radius_m` (§4.2).
8. Không có ứng viên: từ chối `OUTSIDE_RADIUS`.
9. Có một ứng viên: tự chọn, `resolution_method = AUTO_SINGLE`.
10. Có từ hai ứng viên: trả `409 LOCATION_CHOICE_REQUIRED` kèm danh sách; request
   xác nhận phải mang `selected_location_id`, backend tính lại và xác thực nó vẫn
   nằm trong tập ứng viên. `resolution_method = USER_SELECTED`. Nếu
   `selected_location_id` **không** nằm trong tập ứng viên vừa tính lại: từ chối
   `422 INVALID_LOCATION_CHOICE` (cùng mã với `complete-field`, §6.2).
   Nếu tập tính lại rỗng thì bước 8 thắng và response là `422 OUTSIDE_RADIUS`,
   không phải `INVALID_LOCATION_CHOICE`; `INVALID_LOCATION_CHOICE` chỉ áp dụng
   khi tập ứng viên tính lại không rỗng nhưng id được gửi không thuộc tập đó.
11. Ghi `Attendance`, mở hoặc đóng `AttendanceSession` (§5.3), ghi/gỡ anomaly
   và append đúng một `AuditLog` trong cùng một transaction. Check In dùng action
   `attendance.check_in.created`, Check Out dùng action
   `attendance.check_out.created`; target là `Attendance` vừa tạo, `before = {}`
   và `after` chứa đúng năm khóa `attendance_id`, `kind`, `work_date`,
   `location_id`, `session_id`, không chứa tọa độ, sai số, device metadata,
   request IP hay maps URL. Request bị từ chối không tạo
   `AuditLog`. Check In/Out thường không tạo `OutboxEvent` vì chưa có consumer hay
   event type được duyệt.

**Quan trắc nearest không đổi thứ tự validation (chốt).** Ngay khi request đã
qua ranh giới giữa bước 2 và bước 3, service quan trắc tính
`nearest_location`/`nearest_distance_m` từ tọa độ request cho **mọi** outcome,
kể cả request bị chặn tại bước 3, 4 hoặc 5. Phép tính này phục vụ
`AttendanceAttempt`, không tạo candidates, không xét geofence và tuyệt đối không
được dùng để cho request đi tiếp hay đổi thứ tự bước 5 → 6. Với `WEAK_GPS`,
nearest chỉ là nhãn gom nhóm **xấp xỉ để chẩn đoán**, không phải bằng chứng người
dùng hiện diện tại Location đó. Tập dùng để tìm nearest là **toàn bộ đúng 76
`Location` canonical, gồm cả active và inactive** (R-118); phép tính không xét
`radius_m`. Tập này cố ý khác tập candidates ở bước 6–7, vốn vẫn chỉ gồm
`is_active = True`: một Location inactive có thể là nearest quan trắc nhưng
không bao giờ trở thành candidate, được auto-select, được chọn bởi user hay gắn
vào `Attendance` mới. Nếu nhiều Location có cùng khoảng cách nhỏ nhất, nearest
quan trắc chọn dòng có `Location.code` nhỏ nhất theo thứ tự từ điển (R-119),
không dùng database id/name/history/active. Tie-break này chỉ làm một FK quan trắc
ổn định; nó không gộp hay phá hòa tập candidates.

Nearest và candidates của một request phải xuất phát từ **cùng một snapshot tham
chiếu**: transaction khóa Config theo thứ tự Config → Location hiện hành, tải đúng
một lần toàn bộ 76 Location canonical, dùng toàn bộ snapshot cho nearest và lọc
`is_active = True` trên chính snapshot đó cho candidates (R-126). Việc tính
nearest có thể xảy ra trước business gate trên snapshot đã khóa nhưng vẫn chỉ là
quan trắc: không được đổi outcome, mở khóa business state hay phá thứ tự gate.

**GPS foreground có giới hạn, không phải tracking.** Khi màn Attendance đang
hiện và quyền vị trí đã được cấp, client được dùng `watchPosition` để hiển thị
sai số so với ngưỡng; dừng watch ngay khi tab ẩn, user rời màn, hủy, timeout hoặc
request được gửi. Không lưu chuỗi fix, không gửi fix nền và không tự Check In/Out.
Nếu browser chưa cấp quyền, client chỉ gọi xin quyền sau thao tác rõ ràng “Bật vị
trí”. Fix dùng để submit vẫn phải là fix mới, `maximumAge = 0`, và qua kiểm tra
độ tươi phía server.

**Mọi request chấm công đã vào tới bước 3 và kết thúc bằng một outcome nghiệp vụ
đóng đều ghi đúng một `AttendanceAttempt`, kể cả request thành công** — xem §5.2.
Request thành công ghi `outcome = ACCEPTED`; các lần từ chối ở bước 3, 4, 5, 8
và 10 ghi outcome tương ứng. Lỗi hạ tầng 5xx theo R-125 không thuộc tập này. Không được chỉ log
request bị từ chối: thiếu mẫu số `ACCEPTED` thì không tính được tỉ lệ thất bại theo
người và theo địa điểm.

Ranh giới nằm **giữa bước 2 và bước 3 (chốt)**. Những gì chết ở bước 1–2 —
`401 INVALID_TOKEN`/`ACCOUNT_INACTIVE`, `403 PERMISSION_DENIED` (ví dụ `MANAGER`
gọi check-in, §8), `403 PASSWORD_CHANGE_REQUIRED`, `400 SERVER_OWNED_FIELD` do
payload mang `kind` — **không** ghi `AttendanceAttempt` dòng nào. Lý do không phải
tiện tay: `AttendanceAttemptOutcome` là enum đóng đúng 7 giá trị (§5.2) và không có
giá trị nào mô tả “chưa qua cổng xác thực/phân quyền”. Muốn ghi những ca đó thì
phải mở enum, mà mở enum là đổi cấu trúc chứ không phải thêm log — nếu thật sự cần
thì sửa §5.2 trước, đừng nhét đại `outcome` gần đúng. Tầng đó dùng access/security
log ứng dụng đã lọc; riêng endpoint punch bị từ chối không tạo `AuditLog` theo
bước 11/R-121. Nói cách khác: `AttendanceAttempt` là nhật ký **nghiệp vụ chấm
công của Helpdesk**, không phải access log của endpoint.

`resolution_method = GPS_ONLY` không xảy ra với Attendance vì bước 8 đã chặn; giá
trị này chỉ dùng cho `TaskUpdate`.

**Một ngày được phép chấm công nhiều lần.** `AttendanceSession` biểu diễn **ca làm
việc từ Check In đến Check Out**, không biểu diễn thời gian nhân viên liên tục
đứng trong geofence. Sau Check In, nhân viên được rời `Location` để di chuyển hoặc
xử lý Task ở bất kỳ tọa độ nào — kể cả ngoài 76 `Location` — mà **không cần Check
Out khi rời geofence**. Check Out chỉ dùng để kết thúc ca làm việc; một phiên mới
chỉ bắt đầu khi nhân viên thật sự Check In lại sau khi ca trước đã kết thúc.

Nhân viên vẫn có thể Check In / Check Out nhiều lượt trong cùng `work_date` khi
có nhiều ca hoặc khoảng nghỉ không tính công. Ràng buộc là **ghép cặp nghiêm
ngặt**: chuỗi bấm hợp lệ luôn là `IN → OUT → IN → OUT …`. Mỗi Check Out đóng đúng
phiên đang mở gần nhất; không có phiên lồng nhau, không có hai phiên mở cùng lúc.
Thời gian làm việc của một ngày là **tổng thời lượng các phiên đã đóng hợp lệ**;
mỗi phiên có `duration = check_out.recorded_at - check_in.recorded_at`, không trừ
thời gian nhân viên di chuyển hoặc ở ngoài geofence trong khi phiên còn mở.

Mọi bước xác thực vị trí (bước 5-10) áp dụng **độc lập cho từng sự kiện Check In
và Check Out**, không chỉ lượt đầu tiên. Check Out không bắt buộc cùng `Location`
với Check In; nó có thể diễn ra tại bất kỳ `Location` đang hoạt động nào nếu qua
đủ hai cổng GPS. Geofence không được dùng để theo dõi liên tục, tự ngắt phiên khi
nhân viên rời địa điểm hoặc trừ thời gian khỏi phiên.

Không gán địa điểm mặc định cho nhân viên, và **không có model nào lưu địa điểm
hay ca được phân công của một user**. Check In/Out ở bất kỳ `Location` đang hoạt
động nào cũng hợp lệ như nhau; hệ thống không so sánh với “nơi được phân công” vì
không có dữ liệu đó để so (R-73). `Task.location` là địa điểm dự kiến của **một
công việc**, không phải phân công cố định của **một người**, nên không được dùng
làm chuẩn đối chiếu chấm công.

### 5.2 Bất thường chấm công và nhật ký lần bấm chấm công

Đây là **hai khái niệm khác nhau, lưu ở hai bảng khác nhau**:

- `AttendanceAnomaly` gắn vào một `Attendance` đã tồn tại → mô tả một lần chấm
  công **thành công nhưng bất thường**.
- `AttendanceAttempt` là **nhật ký request chấm công đã được phân loại**: mỗi lần
  kết thúc bằng một trong bảy outcome sinh đúng một dòng. Dòng thành công có
  `outcome = ACCEPTED` và trỏ tới `Attendance` vừa tạo; dòng của request bị từ
  chối có `attendance IS NULL`. Đây **không** phải bảng “lần bị từ chối”: thiếu
  các dòng `ACCEPTED` thì không có mẫu số để tính tỉ lệ thất bại theo người hay
  theo địa điểm.

Không dùng cờ nguồn như `is_late`.

```python
class AttendanceAnomalyReason(models.TextChoices):
    LATE_CHECK_IN = "LATE_CHECK_IN", "Check In muộn"
    EARLY_CHECK_OUT = "EARLY_CHECK_OUT", "Check Out sớm"
    LATE_CHECK_OUT = "LATE_CHECK_OUT", "Check Out muộn"
    MISSING_CHECK_OUT = "MISSING_CHECK_OUT", "Thiếu Check Out"
```

Enum này **đóng**, đúng **bốn** giá trị. `OFF_ASSIGNMENT` đã bị loại (R-73): nó
đòi so sánh địa điểm chấm công với “nơi được phân công”, mà §5.1 đã chốt là không
có model nào lưu dữ liệu đó — một anomaly không bao giờ tính được. Muốn khôi phục
thì phải thêm model phân công người ↔ địa điểm cùng endpoint quản lý trong cùng
một thay đổi, không tự suy từ `Task.location`.

`GPS_LOW_ACCURACY` và `OUTSIDE_ALLOWED_LOCATION` đã bị loại vì
hai trường hợp đó không bao giờ tạo `Attendance` để gắn anomaly — chúng là lý do
từ chối, thuộc `AttendanceAttemptOutcome`. `MANUAL_ADJUSTMENT` cũng bị loại vì MVP
không có endpoint `attendance.adjust.any`; khi thêm ở phase sau phải bổ sung lại
enum value cùng endpoint trong cùng một thay đổi.

`Attendance.has_anomaly` chỉ là giá trị dẫn xuất/cached nếu cần hiển thị.

**`AttendanceAttempt`.** Mọi request chấm công **đã qua xác thực và phân quyền,
đã vào tới bước 3 của §5.1 và kết thúc bằng một outcome nghiệp vụ đóng** đều ghi
đúng một `AttendanceAttempt` — kể cả request thành công. Dòng attempt được ghi
**ngoài transaction nghiệp vụ**, sau khi transaction đó đã kết thúc, ở cả nhánh
commit và nhánh exception nghiệp vụ đã phân loại (R-74, R-125).
Lý do: bất biến `uniq_open_session_per_user` (§5.3) bắn `IntegrityError` làm abort
transaction, nên attempt ghi *bên trong* sẽ bị rollback cùng — đúng ca
`SESSION_ALREADY_OPEN` mà §10 bắt buộc phải có dòng attempt cho **cả hai** request
đua nhau. Transaction nghiệp vụ chỉ bao `Attendance`, `AttendanceSession`,
`AttendanceAnomaly` và `AuditLog` của bước 11; `AttendanceAttempt` nằm ngoài. Đổi lại,
attempt có thể mất nếu process chết giữa hai bước — chấp nhận, vì attempt là dữ
liệu quan trắc chứ không phải bất biến nghiệp vụ. Nếu chính thao tác ghi
`AttendanceAttempt` thất bại sau khi transaction nghiệp vụ đã kết thúc, hệ thống
giữ nguyên response hoặc exception nghiệp vụ gốc, không tự retry và không
rollback/che khuất kết quả đó; lỗi ghi attempt chỉ phát telemetry đã lọc, không
chứa tọa độ, device metadata hay request IP. Cam kết "đúng một attempt" áp dụng
khi persistence quan trắc hoạt động bình thường; process death hoặc lỗi
persistence ở bước hậu-transaction là các trường hợp mất quan trắc được chấp
nhận, không được biến thành một kết quả chấm công khác.

Cam kết này chỉ áp dụng khi request kết thúc bằng một trong đúng bảy outcome
nghiệp vụ dưới đây. Lỗi database/network/process/framework bất ngờ giữ response
5xx canonical, **không tạo `AttendanceAttempt`**, không được gán nhãn bằng outcome
gần đúng và chỉ phát telemetry đã lọc. Đây là lỗi vận hành chứ không phải một lần
chấm công được phân loại; không mở rộng enum để che lỗi hạ tầng (R-125).

Enum dưới đây là **đóng**, và việc nó không có giá trị nào cho `401`/`403`/payload
sai chính là lý do những ca đó không ghi attempt (§5.1):

```python
class AttendanceAttemptOutcome(models.TextChoices):
    ACCEPTED = "ACCEPTED", "Được chấp nhận"
    WEAK_GPS = "WEAK_GPS", "GPS sai số cao"
    OUTSIDE_RADIUS = "OUTSIDE_RADIUS", "Ngoài mọi vùng cho phép"
    LOCATION_CHOICE_REQUIRED = "LOCATION_CHOICE_REQUIRED", "Chờ chọn địa điểm"
    INVALID_LOCATION_CHOICE = "INVALID_LOCATION_CHOICE", "Địa điểm chọn không hợp lệ"
    NO_OPEN_SESSION = "NO_OPEN_SESSION", "Không có phiên đang mở"
    SESSION_ALREADY_OPEN = "SESSION_ALREADY_OPEN", "Đang có phiên mở"
```

`LOCATION_CHOICE_REQUIRED` (chưa chọn) và `INVALID_LOCATION_CHOICE` (chọn một
địa điểm ngoài tập ứng viên) là hai tình huống khác nhau, phải tách để báo cáo
phân biệt được người dùng chưa thao tác với client gửi sai dữ liệu.

`CHECK_IN_REQUIRED` và `DUPLICATE` đã bị bỏ khi cho phép chấm công nhiều lần
trong ngày (§5.1). Chúng được thay bằng hai outcome theo trạng thái phiên:
`NO_OPEN_SESSION` (bấm Check Out khi không có phiên mở) và `SESSION_ALREADY_OPEN`
(bấm Check In khi đang có phiên mở). Không thêm lại hai giá trị cũ.

`AttendanceAttempt` lưu tọa độ, `accuracy_m`, `nearest_location` và
`nearest_distance_m` cho mọi request đã vào bước 3 (kể cả khi bị chặn trước bước
6 hoặc ngoài bán kính) nên báo cáo “số lần chấm công bị
từ chối theo từng địa điểm” query trực tiếp được, không phải parse JSON của
`AuditLog`. Nearest được tính trên toàn bộ 76 Location canonical, kể cả Location
inactive; đây chỉ là phép gán quan trắc, không thay tập candidate active-only và
không cho phép chấm công tại Location inactive (R-118). Dòng `WEAK_GPS` có nearest
được serializer/report gắn nhãn suy diễn
`nearest_is_approximate = true`; không thêm cột vì suy trực tiếp từ `outcome`.
Nếu khoảng cách nhỏ nhất bằng nhau, chọn `Location.code` nhỏ nhất theo thứ tự từ
điển (R-119); candidates active cùng INSIDE vẫn giữ nguyên từng dòng riêng.
Về tập ứng viên, attempt chỉ giữ **`candidate_count`** — một số đếm,
**không** có cột mảng ứng viên và không thêm cột đó. Danh sách ứng viên là dữ liệu
của **response API** ở `409 LOCATION_CHOICE_REQUIRED` và `422
INVALID_LOCATION_CHOICE`, để client hiển thị cho người dùng chọn lại; đừng nhầm nó
với `TaskUpdate.location_candidates` (mảng **có** lưu, R-44) — hai model khác nhau
có chủ đích. Bản ghi `ACCEPTED` trỏ tới `Attendance` vừa tạo; các outcome khác có
`attendance = NULL`.

`LOCATION_CHOICE_REQUIRED` không phải lỗi của người dùng: nó tồn tại để đo tần
suất phải chọn tay. Vì vậy nó bị **loại khỏi cả tử số lẫn mẫu số** của tỉ lệ chấm
công thất bại, và **không** nằm trong danh sách “lý do bị từ chối” của báo cáo
(R-77):

```sql
-- mẫu số
COUNT(*) FROM attendance_attempt
WHERE outcome <> 'LOCATION_CHOICE_REQUIRED'
-- tử số
COUNT(*) FROM attendance_attempt
WHERE outcome NOT IN ('ACCEPTED', 'LOCATION_CHOICE_REQUIRED')
```

Nếu tính cả nó vào mẫu số thì một lượt bấm hai bước (bước chọn `409` rồi bước xác
nhận `ACCEPTED`) ghi hai dòng cho **một** lượt bấm thành công, đẩy tỉ lệ thất bại
lên ≥ 50% dù không có lỗi nào. Danh sách lý do từ chối vì thế còn đúng **năm**:
`WEAK_GPS`, `OUTSIDE_RADIUS`, `INVALID_LOCATION_CHOICE`, `NO_OPEN_SESSION`,
`SESSION_ALREADY_OPEN`.

### 5.3 Ca làm, anomaly và bất biến database

MVP dùng một lịch ca cấu hình chung: `timezone = Asia/Ho_Chi_Minh`,
`shift_start`, `shift_end`, `late_grace_minutes`, `early_checkout_grace_minutes`,
`late_checkout_grace_minutes` và không hỗ trợ ca qua ngày. `recorded_at` được đổi
về timezone này trước khi tính `work_date` và mọi anomaly ca làm:

| Anomaly | Gắn vào | Điều kiện |
|---|---|---|
| `LATE_CHECK_IN` | Check In **đầu tiên** trong ngày | `recorded_at > shift_start + late_grace_minutes` |
| `EARLY_CHECK_OUT` | Check Out **cuối cùng** trong ngày | `recorded_at < shift_end - early_checkout_grace_minutes` |
| `LATE_CHECK_OUT` | Check Out **cuối cùng** trong ngày | `recorded_at > shift_end + late_checkout_grace_minutes` |

**Anomaly ca làm thuộc về ngày công, không thuộc về từng lượt bấm.** Vì một ngày
có nhiều lượt (§5.1), chỉ lượt Check In đầu tiên và lượt Check Out cuối cùng của
`work_date` mới được đánh giá đi muộn / về sớm / ra muộn. Các lượt giữa ngày
(ra ngoài rồi quay lại) **không sinh anomaly nào** — nếu tính theo từng lượt thì
mỗi lần ra ngoài buổi sáng sẽ thành một `EARLY_CHECK_OUT` giả và mỗi lần quay lại
buổi chiều thành một `LATE_CHECK_IN` giả.

Hệ quả về thứ tự ghi: khi một Check Out mới trở thành lượt cuối cùng của ngày,
`EARLY_CHECK_OUT`/`LATE_CHECK_OUT` đã gắn vào lượt Check Out trước đó phải được
gỡ bỏ trong cùng transaction. Mỗi `work_date` chỉ tồn tại tối đa một
`LATE_CHECK_IN` và tối đa một anomaly thuộc nhóm ra ca (`EARLY_CHECK_OUT` hoặc
`LATE_CHECK_OUT`) cho mỗi user.

Ví dụ `shift_start=08:00`, `late_grace_minutes=5`: 08:00-08:05 là bình thường,
sau 08:05 tạo `LATE_CHECK_IN`. `late_checkout_grace_minutes` mặc định 60: Check
Out sau `shift_end + 60'` tạo `LATE_CHECK_OUT`. `LATE_CHECK_OUT` là tín hiệu làm
thêm giờ hoặc quên bấm ra, không phải vi phạm kỷ luật; báo cáo phải tách nó khỏi
nhóm đi muộn/về sớm.

**Phiên chấm công.** Mỗi cặp Check In / Check Out là một `AttendanceSession`
(§7), tức ca làm việc chứ không phải phiên hiện diện liên tục trong geofence.
Phiên luôn thuộc **đúng một** `work_date` — lấy theo `work_date` của Check In.
`check_in_location_id` và `check_out_location_id` được trả riêng theo hai
`Attendance` biên; chúng có thể khác nhau. MVP **không hỗ trợ phiên qua ngày**:
không có ca đêm, và một phiên còn mở khi sang ngày mới được xử lý bằng job đóng
cuối ngày bên dưới chứ không kéo dài sang `work_date` kế tiếp.

Database là lớp bảo vệ cuối cùng, không chỉ pre-check service:

```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=["user"],
            condition=models.Q(check_out__isnull=True, closed_by_job=False),
            name="uniq_open_session_per_user",
        )
    ]
```

Partial unique index này bảo đảm **mỗi user tối đa một phiên đang mở tại một thời
điểm**. Điều kiện có **cả hai** vế vì job cuối ngày đóng phiên treo mà vẫn giữ
`check_out = NULL` (không bịa giờ ra ca, xem bên dưới): nếu chỉ xét
`check_out IS NULL` thì phiên đã bị job đóng vẫn bị DB coi là đang mở và chặn
Check In sáng hôm sau. Định nghĩa canonical của **phiên đang mở** là
`check_out IS NULL AND closed_by_job = False`; mọi truy vấn nghiệp vụ, báo cáo và
kiểm tra ở service phải dùng đúng định nghĩa này, không được rút gọn còn
`check_out IS NULL`. Nó thay thế hoàn toàn ràng buộc cũ `UNIQUE(user_id, work_date, kind)` —
ràng buộc đó chỉ cho một Check In và một Check Out mỗi ngày nên mâu thuẫn với
§5.1; **không được thêm lại**. `Attendance` không còn unique constraint nào theo
`(user, work_date, kind)`.

Bất biến này cũng là cơ chế chống bấm trùng: hai request Check In gửi cùng lúc thì
DB chỉ cho một request thắng, request còn lại nhận `SESSION_ALREADY_OPEN`. MVP
**không** dùng thêm ngưỡng thời gian tối thiểu giữa hai lần bấm. Service đổi lỗi
unique thành phản hồi thân thiện; transaction vẫn là bắt buộc.

**Job đóng phiên cuối ngày.** Sau khi ca/ngày kết thúc, job định kỳ đóng mọi phiên
còn mở và gắn `MISSING_CHECK_OUT` vào Check In của phiên đó. Job **không bịa giờ
ra ca**: `check_out` giữ `NULL` và `duration_minutes` giữ `NULL`, nên phiên này bị
loại khỏi tổng giờ công của ngày và phải hiển thị trong báo cáo như dữ liệu thiếu
cần quản lý xử lý. Việc “đóng” được ghi bằng `closed_by_job = True`; theo định
nghĩa phiên mở ở trên, phiên này không còn là phiên đang mở nên Check In sáng hôm
sau diễn ra bình thường và không đụng partial unique index.

Job **chạy mọi ngày**, không phụ thuộc `Config.working_weekdays` hay `Holiday`
(R-82), và đóng mọi phiên còn mở có `work_date < ngày hiện tại`:

```sql
WHERE check_out IS NULL AND closed_by_job = False AND work_date < CURRENT_DATE
```

Nếu job bỏ qua ngày nghỉ như bản trước, một người trực Chủ nhật hoặc ngày lễ mà
quên Check Out sẽ có phiên **không bao giờ được đóng**, và partial unique index
chặn mọi lần Check In sau đó bằng `409 SESSION_ALREADY_OPEN` — người dùng bị kẹt
vĩnh viễn, không có endpoint nào tự thoát. Điều kiện `work_date < CURRENT_DATE`
bảo đảm job không bao giờ đóng nhầm phiên đang mở hợp lệ của hôm nay, nên chạy
thừa vào ngày nghỉ là vô hại. Đổi lại, `MISSING_CHECK_OUT` có thể xuất hiện vào
ngày không làm việc — đúng bản chất: người đó có bấm Check In thật.

**Transaction và retry của job (chốt, R-127).** Mỗi phiên đủ điều kiện là một
đơn vị transaction riêng: job khóa lại phiên, xác nhận nó vẫn thỏa định nghĩa
phiên mở canonical, rồi đặt `closed_by_job = True` và tạo đúng một
`AttendanceAnomaly(MISSING_CHECK_OUT)` trong cùng transaction. Lỗi ở một phiên
rollback cả hai thay đổi của riêng phiên đó nhưng không rollback các phiên đã
commit; job tiếp tục các phiên còn lại khi có thể và `JobRun` phải phản ánh đúng
số đã commit cùng việc có ít nhất một lỗi. Chạy lại chỉ thấy các phiên vẫn mở,
nên hoàn tất phần còn lại mà không đóng lại phiên cũ hoặc tạo anomaly trùng.
Không dùng một transaction cho toàn bộ lần chạy và không commit theo batch.

**`JobRun` của reconciliation (chốt, R-128).** `job_name` canonical là
`MISSING_CHECK_OUT`; mỗi invocation commit một dòng `RUNNING` trước khi quét.
`status` là enum đóng đúng bốn giá trị: `RUNNING`,
`SUCCEEDED`, `PARTIAL_FAILED`, `FAILED`; chỉ `RUNNING` có `finished_at = NULL`.
Không có lỗi thì `SUCCEEDED`, kể cả không có phiên đủ điều kiện. Có cả phiên đã
commit và lỗi thì `PARTIAL_FAILED`; có lỗi nhưng không phiên nào commit, hoặc run
abort trước khi hoàn tất scan, thì `FAILED`. Hai trạng thái lỗi bắt buộc có
`error_code` máy đọc được đã làm sạch; `RUNNING`/`SUCCEEDED` không có error code.
Error code là tập đóng đúng hai giá trị: `SESSION_PROCESSING_FAILED` khi một hay
nhiều phiên lỗi và `RUN_ABORTED` khi invocation không hoàn tất scan.
`scanned_count` đếm phiên invocation đã khóa và re-check, `changed_count` chỉ
đếm phiên mới commit `closed_by_job = True`, `anomaly_count` chỉ đếm anomaly mới
commit; `changed_count` luôn bằng `anomaly_count`. Process chết giữ dòng
`RUNNING` cùng các count đã commit để health phát hiện stale. `JobRun` chính là
dòng nhịp tim PostgreSQL cụ thể của job này theo §9.6, không tạo thêm model
heartbeat song song. Migration tạo bảng mới không backfill lần chạy lịch sử.

**Cutoff, stale và lịch gọi job (chốt, R-131/R-133).** Một run chỉ được xem là
success đúng hạn khi `finished_at < 01:00:00` Asia/Ho_Chi_Minh của ngày hiện tại;
đúng `01:00:00` đã là trễ và dùng luật at/after-cutoff. Trước cutoff, RUNNING bắt
đầu từ 00:00 của ngày hiện tại là hợp lệ; RUNNING bắt đầu trước mốc đó là stale và
alert ngay. Từ đúng cutoff trở đi, mọi RUNNING chưa terminal đều alert. Scheduler
triển khai hiện hữu gọi management command đúng một lần mỗi ngày lúc `00:15`
Asia/Ho_Chi_Minh (`15 0 * * *` với timezone tường minh), kể cả cuối tuần/ngày lễ.
Repository phải có `deploy/scheduled-jobs.yaml` phi bí mật và kiểm tra binding môi
trường/scheduler identity; không thêm Celery, broker hay timer trong web process.

MVP không tạo `MISSING_CHECK_IN` vì không có bản ghi Attendance để gắn anomaly;
báo cáo “chưa Check In” dùng lịch ca/user.

### 5.4 Ownership Attendance self

Endpoint `attendance.check_in.self`/`attendance.check_out.self` không nhận
`user_id`, `kind`, `recorded_at`, `work_date`, anomaly hoặc authorization scope từ
client. Server lấy user từ authentication context, suy `kind` từ route và tự
tạo/ghi các field authoritative. Client chỉ gửi số đo GPS: `latitude`,
`longitude`, `accuracy_m`, `captured_at?`, `selected_location_id?`. Bất kỳ
`user_id` hoặc `kind` trong payload self bị reject `400 SERVER_OWNED_FIELD`;
không ignore im lặng. Điều chỉnh công cho người khác, nếu có phase sau, dùng
endpoint/action riêng `attendance.adjust.any`.

## 6. Công việc

### 6.1 Giao việc và danh sách

Quản lý được giao việc cho một hoặc nhiều Helpdesk, kể cả `assigned_date > today`.
Màn hình có bốn nhóm theo ngày hệ thống (Asia/Ho_Chi_Minh):

| Nhóm | Điều kiện |
|---|---|
| Hôm nay | `assigned_date = today` và chưa hoàn thành |
| Sắp tới | `assigned_date > today` và chưa hoàn thành |
| Quá hạn | `assigned_date < today` và chưa hoàn thành |
| Đã hoàn thành | `status = COMPLETED` |

Task tương lai không được tính KPI/ngày công của hôm nay. Một người hoàn thành là
hoàn thành task: `Task.status = COMPLETED` và `Task.completed_by` là người thực
hiện.

**Task quá hạn “trôi” sang ngày mới thuần ở tầng hiển thị (chốt R-86).**
`Task.assigned_date` là **bất biến sau khi tạo**: không job nào, không endpoint
nào ghi đè nó để đẩy task sang hôm nay. Yêu cầu “nhìn vào biết là task hôm trước
chưa xong” được đáp ứng bằng ba quy tắc đọc:

- Nhóm **Quá hạn** render **phía trên** nhóm **Hôm nay** trên màn danh sách, để
  việc chưa xong đập vào mắt trước việc mới.
- Mỗi dòng quá hạn hiển thị `assigned_date` gốc của nó, không phải hôm nay.
- Mỗi dòng quá hạn kèm nhãn “trễ N ngày”, với `N = today - assigned_date` tính
  **lúc đọc** (Asia/Ho_Chi_Minh), không lưu thành cột.

Bị loại bỏ tường minh: job `UPDATE` `assigned_date` mỗi đêm (kèm
`original_assigned_date` / `carried_over_count`), và thêm cột `due_date` tách
khỏi `assigned_date`. Cả hai làm hỏng báo cáo lịch sử — số task của một ngày quá
khứ sẽ tự đổi mỗi đêm — trong khi mọi thứ người dùng cần đều suy ra được từ
`assigned_date` tại thời điểm đọc.

**Khóa tài khoản không đụng vào task đang mở (chốt).** Đặt `is_active = False`
chỉ chặn đăng nhập và chặn **giao việc mới**; nó không sửa một dòng
`TaskAssignee` nào. Cụ thể:

- Màn giao việc lấy ứng viên bằng `GET /api/users/?is_active=true` (thêm
  `&role=HELPDESK` nếu muốn thu hẹp). **Không có endpoint picker riêng**: chỉ tồn
  tại một `GET /api/users/` với query tùy chọn, và khi không truyền filter thì nó
  trả cả user đang khóa (§10, R-81). Lọc `is_active` là trách nhiệm của client ở
  màn giao việc, không phải filter cứng ở server.
- `assignee_ids` chứa user đang khóa → `422 INACTIVE_ASSIGNEE` kèm danh sách id
  vi phạm, **toàn bộ** request bị từ chối, không tạo task rồi bỏ bớt người.
- Task đã giao trước khi khóa giữ nguyên assignee, giữ nguyên `status`, vẫn rơi
  vào nhóm Quá hạn như mọi task khác. Manager tự xử: giao thêm người, hoặc đóng
  bằng `task.complete.override` (§6.3) với `completion_note` giải thích.
- Báo cáo và lịch sử **không** lọc bỏ user đã khóa: việc họ đã làm trong quá khứ
  vẫn phải đếm đúng, nếu không thì số liệu tháng trước tự đổi mỗi lần có người
  nghỉ việc.

Không tự động gỡ assignee khi khóa. Một thao tác quản trị mà sửa hàng loạt bản
ghi nghiệp vụ là thứ không hoàn nguyên được: mở khóa lại không trả assignee về
chỗ cũ, và `AuditLog` khi đó phải ghi n dòng cho một cú bấm nút.

`Task.status` là **trạng thái duy nhất** của công việc. `TaskAssignee` chỉ là bảng
nối `(task, user, assigned_at)`, **không có cột `status`** — nếu có thì hệ thống
sẽ có hai nguồn sự thật phải đồng bộ. Báo cáo “Việc được giao đã đóng” đếm số
`Task` có `status = COMPLETED` mà user nằm trong `TaskAssignee`; báo cáo “Việc tự
tay hoàn thành” đếm theo `Task.completed_by`.

```python
class TaskStatus(models.TextChoices):
    TODO = "TODO", "Chưa bắt đầu"
    IN_PROGRESS = "IN_PROGRESS", "Đang thực hiện"
    BLOCKED = "BLOCKED", "Có vướng mắc"
    COMPLETED = "COMPLETED", "Đã hoàn thành"
```

Chuyển trạng thái hợp lệ: `TODO -> IN_PROGRESS|BLOCKED|COMPLETED`,
`IN_PROGRESS -> BLOCKED|COMPLETED`, `BLOCKED -> IN_PROGRESS|COMPLETED`.
`BLOCKED` bắt buộc có `block_reason` hoặc `note`; task được giữ nguyên để tiếp
tục ngày sau, không tạo task mới. Không có `NOT_COMPLETED` làm trạng thái chính.

`COMPLETED` là terminal trong MVP: mọi transition từ `COMPLETED` bị từ chối.
Không có reopen bằng `task.update.any`; phase sau phải thêm action/endpoint
`task.reopen` và completion cycle rõ ràng.

| From \ To | TODO | IN_PROGRESS | BLOCKED | COMPLETED |
|---|:---:|:---:|:---:|:---:|
| TODO | - | ✅ | ✅ | ✅ |
| IN_PROGRESS | - | - | ✅ | ✅ |
| BLOCKED | - | ✅ | - | ✅ |
| COMPLETED | ❌ | ❌ | ❌ | - |

Đây là transition matrix canonical. Test mọi ô ✅ cùng permission/object scope,
và phải reject toàn bộ ô ❌; không thay terminal rule bằng `task.update.any`.

### 6.2 Hoàn thành tại hiện trường

`FIELD_EVIDENCE` bắt buộc có 1-5 ảnh, `latitude`, `longitude` và `accuracy_m`.
Ảnh không mang dữ liệu vị trí; tất cả tọa độ nằm trên `TaskUpdate`.

1. Client kiểm file, chuyển HEIC đọc được sang JPEG, nén ảnh và xin intent upload
   cho từng ảnh. Ảnh không đọc được hoặc không thể nén xuống ≤ 5 MB bị chặn trước
   khi upload; backend vẫn kiểm lại độc lập.
2. Backend cấp presigned `PUT` ngắn hạn cho object staging private, khóa theo
   authenticated user + Task + upload intent. Mỗi ảnh có checksum, MIME và size
   đã khai báo; object key không chứa `TaskUpdate.id`.
3. Client upload từng ảnh độc lập. Ảnh đã hoàn tất không upload lại khi ảnh khác
   lỗi. Upload staging **không** tạo `TaskUpdate`, không đổi `Task.status` và
   không đồng nghĩa hoàn thành.
4. Khi user chủ động hoàn thành, client lấy GPS mới rồi gọi endpoint finalize với
   1-5 `upload_ids`, tọa độ, ghi chú và `selected_location_id?`.
5. Backend khóa Task, kiểm `task.complete.field`, ownership/scope của mọi staging
   key, object tồn tại, checksum/MIME/size/count, GPS và trạng thái Task; sau đó
   phân loại `gps_quality`.
6. Chỉ khi `gps_quality = GOOD` mới tính ứng viên `INSIDE_GEOFENCE` theo §4.2,
   giải quyết Location theo bảng dưới đây và suy `resolved_address` (§6.2.1).
7. Trong một transaction, tạo `TaskUpdate`/`TaskPhoto`, chuyển Task sang
   `COMPLETED` và đánh dấu staging objects đã được bind. Request finalize có
   `Idempotency-Key`. Response pre-commit như `LOCATION_CHOICE_REQUIRED`,
   `INVALID_LOCATION_CHOICE`, GPS/file validation failure **không consume/bind
   key**; client được gửi lại cùng key với lựa chọn hoặc fix mới. Key chỉ bind khi
   request đã commit-eligible và service bắt đầu completion transaction. Từ lúc
   đó, retry cùng key + cùng normalized payload trả cùng kết quả; cùng key với
   payload khác trả `409 IDEMPOTENCY_CONFLICT`.

Task có thể được thực hiện tại **bất kỳ tọa độ nào**. Không khớp một `Location`
đã biết không phải lỗi và không chặn hoàn thành; GPS ở đây là bằng chứng sự kiện,
không phải cổng kiểm soát như chấm công. Chỉ trường hợp GPS `GOOD` khớp **nhiều**
geofence mới bắt buộc người dùng chọn một ứng viên để giải quyết mơ hồ trước khi
hoàn thành:

| Tình huống | `location` | `resolution_method` | `location_candidates` |
|---|---|---|---|
| `gps_quality != GOOD` | `NULL` | `GPS_ONLY` | `[]` (không tính ứng viên) |
| Đúng một ứng viên | ứng viên đó | `AUTO_SINGLE` | 1 phần tử |
| Client gửi `selected_location_id` hợp lệ | địa điểm đã chọn | `USER_SELECTED` | toàn bộ ứng viên |
| Từ hai ứng viên, client không chọn | không tạo `TaskUpdate` | không có | trả `409 LOCATION_CHOICE_REQUIRED` + toàn bộ ứng viên |
| Không có ứng viên | `NULL` | `GPS_ONLY` | `[]` |

`selected_location_id` là tùy chọn ở request đầu, nhưng trở thành **bắt buộc**
khi backend tính được từ hai ứng viên trở lên. Client gửi lại GPS và lựa chọn;
backend phải tính lại tập ứng viên và chỉ chấp nhận id còn nằm trong tập đó,
ngược lại trả `422 INVALID_LOCATION_CHOICE` kèm danh sách mới nhất. Không có
endpoint gán Location sau khi Task đã hoàn thành.

**`TaskUpdate.location_candidates` được lưu vào DB**, không chỉ trả trong response.
Đây là mảng id `Location` tính tại thời điểm ghi thành công (mảng rỗng khi không
có ứng viên hoặc khi `gps_quality != GOOD`). Lý do phải lưu:

- Nó lưu dấu tập đối chiếu tại thời điểm hoàn thành để audit; bản ghi nhiều ứng
  viên đã chọn giữ toàn bộ candidates cùng `location` được chọn.
- Tính lại khi hiển thị sẽ trôi kết quả nếu sau đó quản lý sửa `radius_m`, tắt
  `is_active` hay thêm địa điểm mới.
- Số ứng viên = độ dài mảng, nên không cần thêm cột `candidate_count` riêng.

Mảng này là dữ liệu lịch sử, **không** tính lại khi đọc. `HCM000079` và
`HCM010005` trùng tọa độ tuyệt đối, còn `HCM030015` cách `HCM030000` 4.8 m
(§3.1), nên UI chọn Location phải là luồng bình thường, nhanh và hiển thị
`code + name`, không phải một màn xử lý lỗi kỹ thuật.

Task completion dùng compare-and-set/row lock trong một transaction: chỉ request
đầu tiên chuyển `Task.status` sang `COMPLETED` được tạo `TaskUpdate COMPLETED` và
audit. Request thắng sau nhận lỗi `TASK_ALREADY_COMPLETED`. MVP không hỗ trợ
reopen; nếu thêm sau này phải có completion cycle riêng.

Staging object chưa bind không phải dữ liệu nghiệp vụ và không hiện ở báo cáo hay
photo API. Job dọn xóa object/intents chưa bind sau **7 ngày**; finalize thành
công không phụ thuộc việc đổi tên/move object, có thể bind nguyên key staging để
tránh copy không atomic. Một staging key chỉ bind được đúng một lần, đúng Task và
đúng actor đã tạo intent; presigned URL không được lưu DB/log/AuditLog.

`Task.location` là địa điểm dự kiến của công việc, nullable. `TaskUpdate.location`
là địa điểm GPS thực tế, nullable theo bảng trên; hai giá trị này không được ghi
đè lẫn nhau.

#### 6.2.1 Địa chỉ minh chứng và link Google Maps

Ảnh minh chứng hoàn thành **luôn phải có tọa độ**; xác nhận địa chỉ là phần “nếu
được”, không phải điều kiện để hoàn thành task. Quy tắc suy địa chỉ hiển thị:

| Tình huống | Địa chỉ hiển thị |
|---|---|
| `TaskUpdate.location` có giá trị (`AUTO_SINGLE`/`USER_SELECTED`) | `location.name` + `location.address`, kèm nhãn “Đã xác nhận” và `distance_m` |
| `location IS NULL`, `gps_quality = GOOD`, `location_candidates` rỗng | Tọa độ + “Ngoài mọi địa điểm đã đăng ký” |
| `location IS NULL`, `gps_quality != GOOD` | Tọa độ + “GPS sai số cao, chưa xác nhận địa chỉ” kèm `accuracy_m` |

Thứ tự xét là **`location` → `gps_quality` → `location_candidates`**: chỉ khi
`location IS NULL` **và** `gps_quality = GOOD` mới được đọc `location_candidates`.
Xét mảng trước là sai, vì bản ghi `gps_quality != GOOD` không hề chạy geofence
nên `location_candidates` luôn rỗng (§6.2) — nhìn mảng rỗng rồi kết luận sẽ hiện
nhầm “ngoài mọi địa điểm đã đăng ký” cho một bản ghi mà hệ thống thực ra chưa
kiểm tra gì. Sau rule bắt chọn, một TaskUpdate hoàn thành với GPS `GOOD` và nhiều
ứng viên luôn có `location`, nên không tồn tại trạng thái “nhiều địa điểm phù
hợp, chưa chọn” trong dữ liệu đã commit.

Địa chỉ xác nhận **chỉ đối chiếu với bảng `Location` trong hệ thống**. MVP
**không gọi bất kỳ API geocoding bên ngoài nào** (Google Geocoding, Nominatim,
Mapbox…): không cần API key, không phát sinh chi phí, không gửi tọa độ nhân viên
ra dịch vụ thứ ba. Khi không khớp Location nào thì hiển thị tọa độ, không đoán
địa chỉ hành chính.

Mọi bản ghi có tọa độ hiển thị kèm **link mở Google Maps**, dựng từ tọa độ đã lưu:

```text
https://www.google.com/maps?q={latitude},{longitude}
```

Ràng buộc dựng link:

- Dựng từ `captured_latitude`/`captured_longitude` của chính bản ghi, không dựng
  từ tọa độ của `Location` đã gán — người xem cần thấy nơi nhân viên thật sự đứng.
- Số thập phân giữ nguyên như lưu trong DB; không làm tròn, không nội suy.
- Thẻ link phải có `target="_blank"` và `rel="noopener noreferrer"`.
- Không nhúng iframe bản đồ, không tải SDK bản đồ bên ngoài (§9.1 giữ nguyên
  nguyên tắc không phụ thuộc dịch vụ ngoài ngoài S3/R2).

Quy tắc hiển thị này áp dụng cho cả `Attendance` (tọa độ chấm công) và
`TaskUpdate` (tọa độ minh chứng) để báo cáo dùng chung một component.

### 6.3 Quản lý xác nhận hoàn thành

Quản lý có quyền `task.complete.override` có thể hoàn thành task bằng
`CompletionMethod.MANAGER_OVERRIDE`: 0-5 ảnh, không bắt buộc GPS, nhưng bắt buộc
`completion_note` và tạo `AuditLog`. Báo cáo tách rõ `FIELD_EVIDENCE` và
`MANAGER_OVERRIDE`.

`task.complete.field` giữ scope “người tạo **hoặc** người được giao” kể cả với
Manager có `task.update.any`, vì `FIELD_EVIDENCE` khẳng định chính người bấm đã
tới hiện trường. Manager muốn đóng hộ task của người khác thì dùng
`task.complete.override` — bắt buộc lý do và có audit.

```python
class CompletionMethod(models.TextChoices):
    FIELD_EVIDENCE = "FIELD_EVIDENCE", "Hiện trường"
    MANAGER_OVERRIDE = "MANAGER_OVERRIDE", "Quản lý xác nhận"
```

## 7. Mô hình dữ liệu

```text
User(id, username, full_name, phone?, email?,
     role[LEADER|MANAGER|HELPDESK], is_active, must_change_password,
     last_login?, created_at)
Location(id, code, name, kind, parent?, address, latitude, longitude,
         radius_m, is_active, version)
Attendance(id, user, kind[IN|OUT], work_date, recorded_at, captured_at?,
           captured_latitude, captured_longitude, accuracy_m, location,
           distance_m, validation_result, resolution_method, device_metadata,
           request_ip?)
AttendanceSession(id, user, work_date, check_in, check_out?, duration_minutes?,
                  closed_by_job, created_at)
AttendanceAnomaly(id, attendance, reason, metadata, created_at)
AttendanceAttempt(id, user, kind[IN|OUT], work_date, recorded_at, outcome,
                  attendance?, captured_latitude, captured_longitude, accuracy_m,
                  nearest_location?, nearest_distance_m?, candidate_count,
                  device_metadata, request_ip?)
Task(id, title, description, created_by, assigned_date, status, location?,
     completed_by?, completed_at?, completion_method?, completion_note?,
     block_reason?)
TaskAssignee(id, task, user, assigned_at)
TaskUpdate(id, task, user, status, captured_latitude?, captured_longitude?,
           accuracy_m?, captured_at?, location?, location_candidates,
           distance_m?, validation_result?, gps_quality?, resolution_method?,
           completion_method?, completion_note?, block_reason?, note)
TaskPhoto(id, task_update, file, created_at)
EvidenceUpload(id, task, user, object_key, declared_mime, declared_size_bytes,
               checksum_sha256, status[ISSUED|UPLOADED|BOUND|EXPIRED],
               expires_at, bound_at?, created_at)
Notification(id, recipient, event_type, object_type, object_id, dedupe_key,
             title, created_at, read_at?)
PushSubscription(id, user, endpoint_hash, encrypted_subscription,
                 user_agent_family, is_active, last_used_at, created_at)
JobRun(id, job_name, started_at, finished_at?, status, scanned_count,
       changed_count, anomaly_count, error_code?)
Holiday(id, date, name)
AuditLog(id, actor, action, target_type, target_id, before, after, recorded_at)
OutboxEvent(id, event_id, event_type, schema_version, aggregate_type,
            aggregate_id, aggregate_version, payload, created_at,
            request_id, correlation_id,
            publish_state, published_at?, lease_expires_at?)
Config(id=1, timezone, working_weekdays, default_radius_m, max_radius_m,
       max_attendance_accuracy_m, task_gps_good_accuracy_m,
       task_gps_low_accuracy_m, shift_start, shift_end, late_grace_minutes,
       early_checkout_grace_minutes, late_checkout_grace_minutes, ...)
```

Ghi chú model:

- `User.username` là `UNIQUE`, **bất biến** sau khi tạo (`PATCH
  /api/users/{id}/` không khai báo trường này, gửi lên trả
  `400 SERVER_OWNED_FIELD`). `User.full_name` **bắt buộc, không rỗng**
  (`blank=False`) — mọi màn danh sách, báo cáo và ô tìm kiếm hiển thị theo tên
  này nên chuỗi rỗng làm hỏng toàn bộ (R-80). `phone` và `email` **nullable và
  KHÔNG unique**: nhân sự nội bộ ~50 người có thể dùng chung số máy bàn cửa hàng
  hoặc email nhóm, và hệ thống không gửi mail/SMS nên không cần tính duy nhất.
  Vì thế `POST /api/users/` chỉ bắt buộc **ba** trường `username`, `full_name`,
  `role`; thiếu bất kỳ trường nào trả `400` field-required, không tự đặt mặc
  định (§10). Mật khẩu do server sinh (§9.2), không nhận từ client.
- `Location.parent` là nullable theo §2 (7 dòng TTKD và `HCM000079` có
  `parent IS NULL`). `Location.is_active` là
  `BooleanField(default=True, null=False)` — **không nullable**: geofence và mọi
  truy vấn ứng viên lọc `is_active = True`, nên một dòng `NULL` sẽ âm thầm biến
  mất khỏi chấm công và khỏi đối chiếu địa chỉ mà không báo lỗi ở đâu. Cả 76 dòng
  seed có `is_active = True`.
- `Location.version` là số nguyên tăng đơn điệu. `PATCH` bắt version hiện tại;
  server khóa bản ghi, tính lại overlap từ candidate state trong cùng transaction,
  ghi Location + AuditLog + warning set rồi tăng version. Stale write trả `409`
  và giữ reason client đã nhập để review lại; không last-write-wins.
  Nếu version hiện tại nhưng candidate không đổi bất kỳ field mutable nào thì đây
  là no-op idempotent (R-115): trả `200` với Location/version hiện tại và warning
  tính lại, không ghi DB, không tăng version, không AuditLog/OutboxEvent và không
  tăng aggregate version. Version stale vẫn trả `409` kể cả candidate tình cờ
  bằng state hiện tại; `reason` đứng một mình vẫn là `400 VALIDATION_FAILED`.
- `Attendance.location` **không nullable** và `validation_result` luôn là
  `INSIDE_GEOFENCE`: §5.1 bước 8 đã từ chối mọi trường hợp khác. Giữ hai cột này
  để báo cáo dùng chung schema với `TaskUpdate`, không để mở rộng ngầm.
- `Attendance` **không** có `UNIQUE(user, work_date, kind)`: một ngày có nhiều
  lượt bấm (§5.1). Bất biến duy nhất là partial unique index trên
  `AttendanceSession` (§5.3). Index `Attendance(user, work_date, recorded_at)` để
  dựng dòng thời gian trong ngày.
- `AttendanceSession.check_in` và `check_out` là `OneToOne` tới `Attendance`
  (`check_out` nullable): một bản ghi Attendance chỉ thuộc đúng một phiên.
  `check_in_location_id = check_in.location_id`; khi có Check Out,
  `check_out_location_id = check_out.location_id`. Hai field Location của API là
  projection từ hai Attendance biên, **không thêm FK trùng lặp** vào
  `AttendanceSession`; chúng có thể khác nhau. `work_date` copy từ
  `check_in.work_date`. `duration_minutes` tính bằng hiệu hai `recorded_at` khi
  đóng phiên và giữ `NULL` với phiên bị job đóng (§5.3), nên tổng giờ công phải
  cộng có bỏ qua `NULL` chứ không coi `NULL` là 0 im lặng.
- `AttendanceSession.duration_minutes` là `DecimalField(..., decimal_places=6)`;
  lấy hiệu chính xác giữa hai server timestamp theo microsecond rồi lượng tử hóa
  một lần tới 6 chữ số thập phân phút bằng `ROUND_HALF_UP`. Không làm tròn theo
  phút nguyên và không dùng giá trị đã lượng tử hóa để suy ngược timestamp.
- `AttendanceSession.closed_by_job` là `BooleanField(default=False)`, **không
  nullable**: nó nằm trong điều kiện partial unique index (§5.3) nên `NULL` sẽ
  làm hỏng bất biến. Cờ này vừa phân biệt phiên do người dùng bấm Check Out với
  phiên bị job cuối ngày đóng, vừa là vế thứ hai của định nghĩa “phiên đang mở”;
  báo cáo dùng cờ này thay vì đoán từ `check_out IS NULL`.
- `JobRun.status` dùng đúng bốn giá trị ở R-128. Các count không âm;
  `changed_count = anomaly_count <= scanned_count`. Chỉ `RUNNING` thiếu
  `finished_at`; `RUNNING`/`SUCCEEDED` không có `error_code`, còn
  `PARTIAL_FAILED` và `FAILED` bắt buộc có một trong hai mã lỗi đóng ở R-128.
- `TaskUpdate.location_candidates` là mảng id `Location` (`ArrayField`/`JSONField`),
  mặc định `[]`, **không nullable**. Ghi một lần tại thời điểm tạo bản ghi và
  không tính lại khi đọc (§6.2). Mảng rỗng đi cùng `GPS_ONLY` khi không đối chiếu
  được known Location; mảng nhiều phần tử đi cùng `USER_SELECTED` và `location`
  bắt buộc có giá trị. Số ứng viên suy từ độ dài mảng, không thêm cột đếm.
- `AttendanceAttempt` không có `UNIQUE(user, work_date, kind)` — một người có thể
  thử nhiều lần trong ngày. Index theo `(work_date, outcome)` và
  `(nearest_location, outcome)` để phục vụ báo cáo §9.
- `EvidenceUpload.object_key` và `Notification.dedupe_key` là `UNIQUE`. Bản ghi upload không chứa
  presigned URL. `BOUND` là terminal; `EXPIRED` không được finalize. Không hard
  delete `TaskPhoto`; `EvidenceUpload` hết hạn có thể xóa sau khi object staging
  đã được dọn.
- `PushSubscription` thuộc đúng một user và một browser subscription. Logout,
  account switch hoặc `is_active = False` vô hiệu hóa subscription liên quan;
  endpoint plaintext không ghi log. Notification luôn kiểm lại object scope khi
  đọc/deep-link, không coi push payload là quyền truy cập.
- `resolved_address` và link Google Maps (§6.2.1) là **giá trị dẫn xuất**, không
  lưu thành cột: suy từ `location` và tọa độ tại thời điểm hiển thị. Lưu thành cột
  sẽ tạo nguồn sự thật thứ hai và lệch khi `Location.address` được sửa.
- `punch_index` (§10) cũng là **giá trị dẫn xuất, không phải cột** (R-79): nó là
  số thứ tự của bản ghi trong **một dãy duy nhất gồm cả IN lẫn OUT** của cùng
  `(user, work_date)`, sắp theo `recorded_at` tăng dần, bắt đầu từ **1**. Tính
  bằng `ROW_NUMBER() OVER (PARTITION BY user_id, work_date ORDER BY recorded_at)`
  ở tầng truy vấn báo cáo, hoặc bằng `enumerate(..., start=1)` sau khi sắp trong
  serializer — không đánh riêng hai dãy cho IN và OUT, vì mục đích của nó là đọc
  dòng thời gian ra/vào trong ngày. Không lưu thành cột: một bản ghi bị xóa hay
  sửa `recorded_at` sẽ làm mọi số phía sau sai mà không có gì báo.
- `Holiday.date` là `UNIQUE`; nhập tay, không tự sinh.
- `TaskAssignee` là `UNIQUE(task, user)`.
- **Quan hệ `Task` ↔ `TaskUpdate` (chốt, R-84, cập nhật R-89).** `TaskUpdate` là
  **lịch sử bất biến**: chỉ `INSERT`, không sửa, không xóa. Location mơ hồ phải
  được chọn trong luồng `complete-field` trước khi tạo bản ghi, nên không còn
  ngoại lệ `PATCH` Location sau hoàn thành. Sáu trường trùng tên trên
  `Task` — `status`, `completed_by`, `completed_at`, `completion_method`,
  `completion_note`, `block_reason` — là **ảnh chụp của `TaskUpdate` mới nhất**
  (theo `id` tăng dần trong cùng task), tồn tại để danh sách task không phải
  join-and-aggregate ở mọi lần đọc. Vì là ảnh chụp nên chúng **chỉ được ghi
  trong cùng transaction với `TaskUpdate` sinh ra chúng**; cấm mọi đường ghi
  riêng lẻ vào `Task.status` mà không kèm một `TaskUpdate` tương ứng, kể cả
  `MANAGER_OVERRIDE` (§6.3). Hệ quả kiểm thử: sau mỗi thao tác đổi trạng thái,
  sáu trường trên `Task` phải
  bằng đúng giá trị của `TaskUpdate` mới nhất — đây là bất biến kiểm được, không
  phải quy ước.
- Trạng thái refresh token **không** tự định nghĩa model mới: dùng đúng hai bảng
  `OutstandingToken` và `BlacklistedToken` của
  `rest_framework_simplejwt.token_blacklist` (§9.2.1). Thu hồi toàn bộ token của
  một user là blacklist mọi `OutstandingToken` chưa hết hạn của user đó.

`LocationResolutionMethod`: `AUTO_SINGLE`, `USER_SELECTED`, `GPS_ONLY`. Không có
`NEAREST` hay `BUSINESS_CONTEXT` vì các cách này có thể ghi sai đơn vị khi địa chỉ
trùng nhau. Đây là tên canonical, dùng thống nhất với `LocationValidationResult`.

`LocationValidationResult`: `INSIDE_GEOFENCE`, `OUTSIDE_GEOFENCE` (§4.2).

`Config` là singleton (`pk=1`); database/service chặn tạo dòng thứ hai.

## 8. RBAC — ma trận canonical duy nhất

Backend kiểm quyền bằng `PermissionAction` tập trung; cấm rải `if role == ...`
trong view/service. Client chỉ ẩn/hiện UI, không thay thế backend authorization.

| Action | LEADER | MANAGER | HELPDESK |
|---|:---:|:---:|:---:|
| `attendance.check_in.self`, `attendance.check_out.self`, `attendance.view.self` | - | - | ✅ |
| `attendance.view.all` | ✅ | ✅ | - |
| `task.create.self`, `task.complete.field` | - | ✅ | ✅ |
| `task.view.self`, `task.update.self` | - | - | ✅ |
| `task.view.all` | ✅ | ✅ | - |
| `task.create.assign`, `task.update.any` | - | ✅ | - |
| `task.complete.override` | - | ✅ | - |
| `location.view`, `config.view` | ✅ | ✅ | ✅ |
| `location.manage`, `config.manage_attendance`, `holiday.manage` | - | ✅ | - |
| `user.view`, `user.manage`, `user.assign_role` | - | ✅ | - |
| `report.view.self` | - | - | ✅ |
| `report.view.all`, `report.export`, `photo.view.all` | ✅ | ✅ | - |
| `photo.view.self` | - | - | ✅ |
| `operations.job_health.view` | ✅ | ✅ | - |

**`config.view` và `holiday.manage` (chốt, R-83).** Hai action này được tách ra
để mọi endpoint ở §10 đều có đúng một action canonical, không còn endpoint nào
"ngầm hiểu là quyền quản lý". `config.view` cấp cho **cả ba** vai trò vì client
phải đọc `Config` để dựng UI — biết `max_attendance_accuracy_m` mới hiện được
cảnh báo GPS yếu, biết `shift_start`/`shift_end` mới tô được giờ muộn. Nó chỉ
đọc; sửa `Config` vẫn là `config.manage_attendance` của riêng `MANAGER`. Hệ quả:
`GET /api/config/` và `PATCH /api/config/` cùng một URL nhưng **hai action khác
nhau**, kiểm theo method. `holiday.manage` gộp cả đọc lẫn ghi lịch nghỉ và chỉ
`MANAGER` có, vì danh sách ngày nghỉ chỉ dùng ở màn cấu hình chứ không dùng để
dựng UI của Helpdesk (§5.3: job cuối ngày **không** đọc `Holiday`, R-82).

**Job health (chốt, R-130).** `operations.job_health.view` là action đọc global
aggregate, cấp trực tiếp cho `LEADER` và `MANAGER`, không cấp `HELPDESK` và không
nằm trong `PERMISSION_IMPLIES`. Nó không có object scope theo user vì response
không trả danh sách phiên hay người dùng. Response vẫn được shape theo role:
LEADER không nhận account/AuditLog deep-link; MANAGER chỉ nhận link điều tra mà
endpoint đích vẫn phải kiểm quyền độc lập.

Việc shape response theo role thuộc duy nhất module Identity (R-132). Sau khi
authorize action, Identity trả enum đóng `JobHealthAccessScope.INVESTIGATE` cho
MANAGER hoặc `JobHealthAccessScope.ESCALATE_ONLY` cho LEADER; HELPDESK bị từ chối
trước khi có scope. Operations và adapter composition chỉ tiêu thụ scope này,
không đọc hoặc so sánh `Role`.

Một `*.all` chỉ bao hàm `*.self` tương ứng **khi cặp đó có trong
`PERMISSION_IMPLIES` ở §8.1**; ngoài map đó không có kế thừa ngầm nào. Vì vậy
không cần cấp cả hai action cho cùng một role đối với các cặp đã liệt kê, và ma
trận trên **không cấp trùng**: `MANAGER` không có dấu ✅ ở `task.view.self` hay
`task.update.self` vì hai action này suy ra từ `task.view.all` và
`task.update.any`. Đọc ma trận theo đúng nghĩa "cấp trực tiếp"; muốn biết một
role có làm được action nào không thì hỏi `has_perm()`, không dò mắt bảng.

**Chấm công và `MANAGER` (chốt).** `MANAGER` **không thuộc đối tượng chấm công**
trong MVP: không có `attendance.check_in.self`, `attendance.check_out.self`, và
`attendance.view.self` chỉ tồn tại qua implication từ `attendance.view.all` để
xem, không để tự chấm. Manager gọi hai endpoint check in/out nhận
`403 PERMISSION_DENIED`. Việc Manager "trực tiếp hoàn thành công việc tại hiện
trường" (PRD §3.3) đi bằng `task.complete.field` — luồng ảnh/GPS của Task, độc
lập hoàn toàn với bảng công. Nhờ vậy báo cáo §9 giữ nguyên nghĩa "bảng công của
Helpdesk", không phải lọc bỏ Manager ở từng truy vấn. Khi nào cần Manager chấm
công thì đó là một quyết định mới, phải sửa cả §5, §9 và ma trận này cùng lúc.

`LEADER` **chỉ đọc**: không có bất kỳ action tạo/sửa/xóa nào, kể cả
`task.create.assign` và `task.update.any`. `HELPDESK` không có quyền xác nhận
thay quản lý hay xem ảnh/báo cáo người khác. Đây là **ma trận RBAC duy nhất**;
PRD chỉ mô tả vai trò và trỏ tới bảng này, không lặp ma trận action.

**Phạm vi `user.assign_role` (chốt).** Action này cho phép gán đúng **hai** vai
trò: `LEADER` và `HELPDESK`. Gán `MANAGER` bị từ chối `403 PERMISSION_DENIED`,
kể cả khi actor chính là `MANAGER` và kể cả khi target là chính actor. Tài khoản
`MANAGER` chỉ sinh ra từ seed hoặc Django superuser (`manage.py`), không qua API.
Lý do: chặn leo thang quyền theo chiều ngang — một Manager bị chiếm tài khoản
không được phép tự nhân bản thêm Manager. Tập role gán được là một hằng số ở
tầng policy (`ASSIGNABLE_ROLES = {LEADER, HELPDESK}`), không rải `if role == ...`
trong view/serializer, và mọi lần đổi vai trò ghi `AuditLog`.

**Phạm vi `user.manage` (chốt).** Khóa `user.assign_role` mà để hở `user.manage`
là vô nghĩa: dev cấm được ở endpoint gán vai trò nhưng vẫn lọt qua create/update
user. Nên hai luật dưới đây áp cho **mọi** endpoint quản trị người dùng, không
riêng endpoint gán vai trò.

1. **Không tạo/sửa ra `MANAGER`.** Đúng hai endpoint nhận trường `role`:
   `POST /api/users/` và `PATCH /api/users/{id}/role`. Cả hai mang
   `role = MANAGER` đều bị từ chối `403 PERMISSION_DENIED`, kể cả khi actor là
   `MANAGER`. Trường `role` đi qua đúng một chỗ kiểm là `ASSIGNABLE_ROLES`, dùng
   chung cho hai endpoint đó — không có bản sao luật thứ hai. `PATCH
   /api/users/{id}/` (sửa hồ sơ) **không** khai báo `role`, nên nó trả
   `400 SERVER_OWNED_FIELD` vì *có mặt* trường đó, không phải vì giá trị là gì:
   `role = HELPDESK` gửi vào đây cũng `400`. Hai mã không mâu thuẫn vì chúng trả
   lời hai câu hỏi khác nhau — `400` là "trường này không thuộc endpoint này",
   `403` là "giá trị này ngoài quyền của anh".
2. **Không đụng vào target đang là `MANAGER`.** Khi user bị tác động có
   `role = MANAGER`, các thao tác update thông tin quản trị, khóa/mở khóa
   (`is_active`), đặt lại mật khẩu và gán vai trò đều trả
   `403 PERMISSION_DENIED` — kể cả khi target là chính actor. Lý do: một Manager
   bị chiếm tài khoản không được phép khóa, reset hay hạ quyền Manager khác.

`user.view` **không** bị chặn: danh sách và chi tiết vẫn trả tài khoản `MANAGER`
để tổng số nhân sự trên giao diện không lệch. Ranh giới là **đọc được, cấm mọi
thao tác ghi**.

Manager tự đổi mật khẩu và tự sửa thông tin cá nhân bằng **endpoint self riêng**
(`/api/change-password/`, `/api/me/`), không đi qua nhánh quản trị ở trên — hai
nhánh này có policy khác nhau nên không được gộp view. Thao tác self không cần
`user.manage`; nó chỉ cần user đã đăng nhập và chỉ tác động lên chính
`request.user`.

Kiểm quyền chạy theo thứ tự: action (`user.manage`) → role của target
(`MANAGER` thì dừng) → `role` trong payload (ngoài `ASSIGNABLE_ROLES` thì dừng).
Mọi lần từ chối ở hai bước sau đều là `403 PERMISSION_DENIED`, không phải `422`,
vì đây là giới hạn quyền chứ không phải dữ liệu sai định dạng.

Hai bước đầu — action và role của target — **cùng thuộc cổng phân quyền** và
chạy **trước** DTO validation (R-87). `target.role = MANAGER` là luật cố định
của cả nhóm endpoint quản trị người dùng, không phụ thuộc một chữ nào trong
body, nên xét nó không cần parse payload; đặt nó sau DTO validation chỉ khiến
một request thiếu quyền bị lộ thông tin về hình dạng payload. Hệ quả: `PATCH`
lên target `MANAGER` với body sai trường trả `403 PERMISSION_DENIED`, **không**
phải `400 SERVER_OWNED_FIELD` — 403 thắng 400. Bước thứ ba (`role` trong
payload) buộc phải nằm sau DTO validation vì phải parse được giá trị mới xét
được; đây là khác biệt so với object scope của Task, vốn phụ thuộc dữ liệu gửi
lên. Hai bước cổng quyền cài trong `permission_classes`, không nhét vào
`serializer.validate()` hay `perform_create()`.

**`LEADER` không có `user.view` (chốt).** Đây là chủ ý, không phải bỏ sót ô trong
bảng: Lãnh đạo giám sát bằng báo cáo chấm công/công việc — vốn đã hiện đủ tên
nhân viên — nên không cần màn hình danh bạ kèm số điện thoại, email và trạng thái
khóa. `GET /api/users/` và `GET /api/users/{id}/` với actor `LEADER` trả
`403 PERMISSION_DENIED`, và có test khẳng định điều đó. Khi nào Lãnh đạo cần xem
danh sách nhân sự thì sửa ma trận §8 và PRD §5.1 cùng lúc, đừng lặng lẽ nới
queryset.

### 8.1 Permission implication đóng và object scope

RBAC trả lời *ai được làm loại action nào*; object scope/ABAC trả lời *được làm
trên bản ghi nào*. Middleware không kiểm exact action đơn thuần. Chỉ năm implication
sau được phép, không tự suy diễn cho action khác:

```python
PERMISSION_IMPLIES = {
    "task.view.all": {"task.view.self"},
    "task.update.any": {"task.update.self"},
    "attendance.view.all": {"attendance.view.self"},
    "report.view.all": {"report.view.self"},
    "photo.view.all": {"photo.view.self"},
}
```

Map này là **đóng**. `task.complete.field`, `task.complete.override`,
`task.create.assign`, `location.manage`, `config.manage_attendance`,
`holiday.manage` và mọi action quản trị khác không nằm trong map, nên không
action nào bao hàm chúng. Đặc biệt `location.manage` **không** bao hàm
`location.view`, và `config.manage_attendance` **không** bao hàm `config.view`:
ma trận §8 đã cấp trực tiếp cả hai action đọc cho `MANAGER`, nên không cần
implication và không được thêm.

Nghĩa của scope task:

| Action | Scope bắt buộc |
|---|---|
| `task.view.self` | Task do user tạo **hoặc** user là assignee |
| `task.update.self` | Task do user tạo **hoặc** user là assignee, và transition hợp lệ |
| `task.complete.field` | Task do user tạo **hoặc** user là assignee; sau đó vẫn kiểm evidence/transition |
| `*.all` / `task.update.any` | Không giới hạn theo creator/assignee, nhưng vẫn kiểm business invariant |

Scope lấy theo **action mạnh nhất actor thực sự có**, không theo action mà
endpoint khai báo. Endpoint yêu cầu `task.view.self` mà actor có `task.view.all`
thì qua cổng action nhờ implication và scope là **không giới hạn**; implication
chỉ để mở cổng action, không kéo theo ràng buộc creator/assignee của dòng `.self`.
Nhờ vậy bỏ cấp trùng `.self` cho `MANAGER` ở ma trận §8 không làm Manager mất
quyền đọc/sửa task của người khác. Ngược lại, `task.complete.field` không nằm
trong `PERMISSION_IMPLIES`: Manager có action này **trực tiếp** và vẫn bị ràng
buộc scope creator/assignee — muốn đóng việc của người khác thì dùng
`task.complete.override` (§6.3).

Service phải lọc scope ngay trong query/policy khi hợp lý, ví dụ
`Task.objects.filter(id=task_id).filter(Q(created_by=user) | Q(assignees=user))`.
Không được gọi `require_permission("task.update.self")`, fetch theo `id` rồi mới
cho mutation mà không kiểm ownership. Leader bị từ chối mọi mutation dù có quyền
`*.view.all`.

### 8.2 Authorization pipeline bắt buộc

```text
Authentication
  -> action permission RBAC (direct hoặc implication đã chốt)
       (a) actor có action này không
       (b) target có nằm ngoài tầm với của action không  <- ví dụ target.role = MANAGER
  -> DTO/input validation                                <- 400 SERVER_OWNED_FIELD ở đây
  -> object scope/ownership ABAC
  -> business validation/state transition
  -> atomic transaction/DB constraint
  -> audit log/event
```

Bước (b) là một phần của **cổng phân quyền**, không phải object scope: nó chỉ
đọc thuộc tính của target trên URL và luật cố định của nhóm endpoint, không đọc
body. Object scope ở bước sau mới là thứ phụ thuộc dữ liệu gửi lên.

View/controller chỉ điều phối pipeline; cấm gộp thành `if role == ...` lớn.

**Thứ tự RBAC trước DTO validation là bắt buộc, không phải sở thích (chốt,
R-72).** Khi một actor **không có quyền** gọi endpoint **và** gửi body sai định
dạng, response phải là `403 PERMISSION_DENIED`, không phải `400`. Lý do: `400`
mô tả body, mà body của người không có quyền gọi endpoint này thì không đáng
được mô tả — trả `400` là rò rỉ thông tin về schema nội bộ cho người ngoài
quyền, và tệ hơn là làm client hiểu nhầm "sửa body là gọi được". Ví dụ cụ thể:
`HELPDESK` gọi `POST /api/users/` với body rỗng → `403`, không phải
`400 username field-required`. Hệ quả kỹ thuật ở DRF: kiểm quyền phải nằm ở
`permission_classes`/`check_permissions` (chạy trước `serializer.is_valid()`),
không được nhét vào `serializer.validate()` hay `perform_create()`.

`400 SERVER_OWNED_FIELD` (§8.3 — trường không thuộc endpoint này) **không** là
ngoại lệ đứng trước RBAC. Nó nằm **trong** bước DTO validation, tức **sau** cổng
phân quyền: actor phải qua được (a) và (b) rồi mới tới lượt body của họ được mô
tả. Trong phạm vi DTO validation, `SERVER_OWNED_FIELD` bắn **trước** kiểm giá
trị của các trường hợp lệ. Còn `403` vì *giá trị* ngoài quyền (ví dụ
`role = MANAGER` trong payload, §8) bắn **sau** DTO validation vì phải parse
được giá trị mới xét được. Ba mốc này không mâu thuẫn nhau: cổng RBAC đầu
pipeline hỏi "actor có được gọi action này, lên target này không"; `400` hỏi
"body có đúng hình dạng của endpoint không"; `403` muộn hỏi "actor có được đặt
giá trị này không".

### 8.3 Client-owned và server-owned data

| Client báo/gửi | Server authoritative |
|---|---|
| `latitude`, `longitude`, `accuracy_m`, `captured_at?`, `selected_location_id?`, photo, note, `block_reason`, input nghiệp vụ được phép | authenticated `user_id`, `kind` (suy từ route), `recorded_at`, `work_date`, `validation_result`, `resolution_method`, `gps_quality`, `distance_m`, permission/object scope, completion actor, kết quả transition, anomaly, audit timestamps |

Serializer/DTO chỉ expose cột client-owned ở input. Client không được override
server-owned field qua JSON, kể cả bằng field optional. Quy tắc này áp dụng cho
Attendance, Task và TaskUpdate.

## 9. Vận hành, báo cáo, ảnh và audit

- Báo cáo chấm công theo ngày/người/địa điểm và `AttendanceAnomaly.reason` (4 giá
  trị ở §5.2).
- Giờ công một ngày = **tổng `duration_minutes` của các `AttendanceSession`** trong
  ngày đó, không phải hiệu giữa lần bấm đầu và lần bấm cuối. Báo cáo phải hiển thị
  cả **số lượt** trong ngày và danh sách phiên, vì một ngày có thể có nhiều lượt
  (§5.1).
- Phiên có `closed_by_job = True` (§5.3 — vẫn giữ `check_out IS NULL`) hiển thị
  riêng là “thiếu Check Out”, không cộng vào tổng giờ và không được điền giờ ước
  tính. Báo cáo lọc theo `closed_by_job`, không lọc theo `check_out IS NULL`:
  phiên đang mở thật của hôm nay cũng có `check_out IS NULL` nhưng chưa phải lỗi.
- Mọi bản ghi có tọa độ trong báo cáo hiển thị địa chỉ xác nhận và link Google
  Maps theo §6.2.1.
- Báo cáo **lần chấm công bị từ chối** đọc từ `AttendanceAttempt`, nhóm theo
  `outcome` và `nearest_location`. Có đúng **năm** `outcome` từ chối: `WEAK_GPS`,
  `OUTSIDE_RADIUS`, `INVALID_LOCATION_CHOICE`, `SESSION_ALREADY_OPEN`,
  `NO_OPEN_SESSION` (R-77). `LOCATION_CHOICE_REQUIRED` **không** nằm trong danh
  sách này và bị loại khỏi **cả tử số lẫn mẫu số** của tỉ lệ thất bại (§5.2): nó
  không phải một lần chấm công hỏng mà là bước giữa của một luồng đúng — hệ
  thống hỏi lại "anh đang ở địa điểm nào", người dùng chọn, rồi lượt sau
  `ACCEPTED`. Đếm nó vào tử số làm tỉ lệ lỗi phồng lên ở đúng những cụm địa chỉ
  trùng/rất gần nhau ở §3.1; đếm vào riêng mẫu số lại làm tỉ lệ co xuống giả
  tạo. Loại khỏi cả hai vế là cách duy nhất giữ tỉ lệ đọc được. Đây là báo cáo
  riêng, không trộn với báo cáo anomaly vì hai nguồn dữ liệu khác nhau: anomaly
  gắn với ca công đã ghi nhận, attempt là lần bấm không tạo ra `Attendance`.
- Mọi metric tỉ lệ failure hiển thị đồng thời: tử số, mẫu số hợp lệ, số
  `LOCATION_CHOICE_REQUIRED` bị loại, tổng attempt quan sát được, số dòng có/không
  có nearest, thời điểm refresh và nhãn “lượt request, không phải số người/ca”.
  Mẫu số bằng 0 hiển thị `N/A`, không hiển thị `0%`.
- Báo cáo task tách người được giao khỏi `completed_by`, và tách phương thức hoàn
  thành hiện trường khỏi quản lý xác nhận.
- Báo cáo task lọc/nhóm rõ `TODO`, `IN_PROGRESS`, `BLOCKED`, `COMPLETED` và
  `TaskUpdate.gps_quality`; completion GPS thấp/không tin cậy không được gộp vào
  nhóm GPS tốt.
- Báo cáo task tách hai nhóm của `location IS NULL`: `gps_quality != GOOD` là
  “GPS không đủ tin cậy để đối chiếu”; `gps_quality = GOOD` với mảng rỗng là
  “Ngoài mọi địa điểm đã đăng ký”. TaskUpdate GPS `GOOD` có nhiều candidates
  luôn đã chọn `location` trước khi commit, nên không có nhóm “chưa chọn”.
- Presigned URL ảnh chỉ tạo sau khi kiểm `photo.view.self`/`photo.view.all`.
- MVP: nhận ảnh camera hoặc thư viện ở JPEG/PNG/WebP, tối đa 5 MB/ảnh sau khi nén
  client; backend vẫn kiểm MIME/type/kích thước độc lập.
  Số lượng ảnh phụ thuộc `completion_method`: `FIELD_EVIDENCE` bắt buộc **1-5**
  ảnh (§6.2), `MANAGER_OVERRIDE` cho phép **0-5** ảnh (§6.3), cập nhật trạng thái
  thường cho phép 0-5 ảnh.
- Không hard delete Attendance/Task; điều chỉnh qua nghiệp vụ có `AuditLog`.
- Bắt buộc audit cho manager override, thay đổi Location/Config, quản lý tài khoản
  và điều chỉnh dữ liệu chấm công/task.
- Dashboard có health read model cho job `MISSING_CHECK_OUT`: lần chạy thành công
  gần nhất, timezone/cutoff dự kiến, số scanned/closed/anomaly, số phiên mở quá
  hạn hiện tại và cờ vi phạm bất biến closed/anomaly. MANAGER thấy link tới điều
  tra vận hành được phép; LEADER chỉ thấy trạng thái read-only và hành động chuyển
  thông tin cho MANAGER, không thấy account/AuditLog.
- Cutoff hoàn tất daily reconciliation là **01:00 Asia/Ho_Chi_Minh** (R-129,
  R-131), theo ranh giới loại trừ: chỉ `finished_at < 01:00:00` là đúng hạn,
  đúng `01:00:00` đã là trễ.
  Health dùng đúng `ok`/`alert`/`unknown` và precedence của §9.6. Chưa từng có
  `JobRun` là `unknown`. Sau cutoff, thiếu một `SUCCEEDED` của ngày hiện tại,
  `RUNNING` chưa kết thúc, latest terminal `PARTIAL_FAILED`/`FAILED`, còn phiên
  mở quá hạn, count mismatch hoặc quan hệ job-closed/`MISSING_CHECK_OUT` sai đều
  là `alert`; chỉ success đúng hạn và không còn lỗi/bất biến mới là `ok`. Trước
  cutoff, overdue-open vẫn hiển thị nhưng riêng nó chưa nâng thành alert; RUNNING
  từ trước 00:00 ngày hiện tại là stale, lỗi và invariant đều alert ngay. Từ đúng
  cutoff, mọi RUNNING chưa terminal alert. Read model trả latest run, latest successful run,
  cutoff, counts, overdue-open, reason flags và `refreshed_at`.
- `JobRun` cùng `AttendanceSession` và `AttendanceAnomaly` là bằng chứng canonical
  của auto-close. Job không có actor người dùng nên không tạo AuditLog hoặc
  OutboxEvent theo từng phiên; đọc health cũng không tạo AuditLog/OutboxEvent.
  Response health không chứa GPS, danh sách user, raw exception hay secret và
  phải là private/no-store (R-130).

### 9.1 Lưu ảnh S3 / R2

Bucket phải private. DB chỉ lưu object key, không lưu presigned URL vì URL có hạn.
S3 và R2 dùng chung `django-storages[s3]`/`boto3`; khác nhau ở `S3_ENDPOINT`.

```python
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": env("S3_BUCKET"),
            "endpoint_url": env("S3_ENDPOINT", default=None),
            "default_acl": None,
            "querystring_auth": True,
            "querystring_expire": 3600,
            "file_overwrite": False,
        },
    },
}
```

Object staging key có dạng
`task-evidence/staging/{task_id}/{user_id}/{upload_uuid}.{ext}`; không chứa
`TaskUpdate.id`. Presigned `PUT` sống tối đa 15 phút, chỉ cho đúng key, MIME,
checksum và giới hạn size đã khai báo. Client nén ảnh trước upload để tránh nhân
viên hiện trường phải đợi file gốc qua 4G; không đọc EXIF. Backend xác nhận object
bằng metadata/HEAD và checksum trước finalize, không tin callback từ client.

Draft client lưu **ảnh đã nén + note**, không lưu GPS, token hay presigned URL.
Namespace theo user + Task; không bao giờ render draft của account khác. Draft
được giữ tối đa 7 ngày kể từ lần sửa cuối, xóa sau finalize đã verify, khi user tự
xóa, logout hoặc đổi account; storage unavailable/quota/eviction phải hiển thị
trung thực, không báo “đã lưu”. Account bị khóa làm server từ chối finalize và
client xóa draft ở lần tiếp theo xác nhận được trạng thái account. Đây là
best-effort local purge, không phải secure erase của hệ điều hành.

### 9.1.1 Notification in-app và web push

MVP có in-app notification và web push opt-in; không email/SMS. Năm event:

| Event | Recipient | Thời điểm / suppression |
|---|---|---|
| Task mới được giao | assignee vừa được thêm | ngay sau commit; dedupe theo Task + assignee + assignment version |
| Task sắp đến ngày thực hiện | assignee của Task chưa `COMPLETED` | 17:00 ngày trước `assigned_date` |
| Task quá hạn | assignee của Task chưa `COMPLETED` | 08:00 mỗi ngày, tối đa một lần/Task/ngày |
| Phiên còn mở gần cuối ngày | HELPDESK sở hữu phiên | `shift_end - 30 phút`; hủy nếu đã Check Out |
| Task nhiều assignee được người khác hoàn thành | các assignee còn lại | ngay sau commit; không gửi cho `completed_by` |

Quiet hours 21:00–07:00 Asia/Ho_Chi_Minh; event rơi vào quiet hours chỉ ghi
in-app và dời push tới 07:00 nếu trạng thái vẫn còn phù hợp. Push dùng nội dung
chung, không chứa tên Task, tên nhân viên, tọa độ hay ảnh trên lock screen. Trước
khi enqueue và khi deep-link, server kiểm lại `is_active`, recipient/object scope
và trạng thái hiện tại. Push có TTL 24 giờ, collapse/dedupe key ổn định; logout,
đổi account hoặc khóa account vô hiệu hóa subscription. In-app là nguồn đầy đủ;
push chậm/mất/trùng không được làm đổi nghiệp vụ.

### 9.2 Đăng nhập lần đầu và đặt lại mật khẩu

User mới có `must_change_password=True`. Một DRF permission chặn mọi endpoint
trừ `/api/change-password/` cho tới khi đổi mật khẩu thành công. Chức năng reset
mật khẩu của Manager đặt lại cờ này; MVP không cần email invitation/token. Reset
mật khẩu — dù do Manager hay do user tự đổi — đồng thời thu hồi mọi refresh token
đang mở của user đó (§9.2.1).

Mật khẩu mới tối thiểu 12 ký tự, không được trùng `username` và phải qua các
Django password validators đã cấu hình. Mật khẩu do server sinh dùng `secrets`,
không dùng `random` hay UUID cắt ngắn.

**Mật khẩu ban đầu do server sinh, hiển thị đúng một lần (chốt).** Cả `POST
/api/users/` (tạo user) lẫn `POST /api/users/{id}/reset-password` đều **không
nhận** trường `password` trong payload; gửi kèm trả `400 SERVER_OWNED_FIELD`.
Server sinh chuỗi ngẫu nhiên bằng `secrets` (không phải `random`), trả về trong
response của đúng request đó để Manager đọc lại cho nhân viên, và sau đó không
đọc lại được ở bất kỳ đâu: không lưu bản rõ, không ghi vào `AuditLog`, không log
ra file. Mất thì reset lại, không có đường khôi phục — đây là hành vi mong muốn,
không phải thiếu sót cần vá. Lý do không cho Manager tự nhập: tránh cả đội dùng
chung một mật khẩu dễ đoán, và tránh mật khẩu đi qua bàn phím/clipboard/log của
client. Cờ `must_change_password = True` được bật ngay, nên **mật khẩu này chỉ
dùng để đăng nhập ban đầu và bắt buộc đổi trước khi dùng hệ thống**.

**Đây không phải OTP (chốt).** Mật khẩu server sinh vẫn hợp lệ cho tới khi user
đổi nó: đăng nhập được nhiều lần (mất mạng giữa chừng, đóng nhầm tab, đổi máy đều
không làm hỏng nó), và không có TTL — để một tuần rồi mới đăng nhập vẫn vào được.
Thứ chặn không phải là mật khẩu hết hạn mà là cờ `must_change_password`: token cấp
ra dùng được đúng một việc là gọi `/api/change-password/`, mọi endpoint nghiệp vụ
khác trả `403 PASSWORD_CHANGE_REQUIRED`. Viết “dùng một lần” trong tài liệu hay
tên test là sai lệch — không có cơ chế nào vô hiệu hóa mật khẩu sau lần đăng nhập
đầu, và cũng **không** thêm cơ chế đó trong MVP: nó chỉ tạo ra ca hỏng “user đăng
nhập được, mất kết nối, hết đường vào” mà `must_change_password` đã chặn đủ.

### 9.2.1 Cơ chế xác thực: JWT ngắn hạn + refresh token thu hồi được

Chốt: **JWT access token ngắn hạn, cặp với refresh token thu hồi được ở server**
(`djangorestframework-simplejwt`). Lý do: nhân viên hiện trường dùng điện thoại cả
ngày nên không thể bắt đăng nhập lại liên tục, nhưng khi mất máy hoặc nghỉ việc
thì quản lý phải cắt được truy cập ngay — access token thuần không thu hồi được,
còn session cookie thuần thì bất tiện với client Next.js gọi API chéo origin.

| Tham số | Giá trị chốt | Ghi chú |
|---|---|---|
| `ACCESS_TOKEN_LIFETIME` | **15 phút** | Đủ ngắn để thiệt hại khi lộ là có hạn |
| `REFRESH_TOKEN_LIFETIME` | **7 ngày** | Ca làm cả tuần không phải đăng nhập lại |
| `ROTATE_REFRESH_TOKENS` | `True` | Mỗi lần refresh cấp token mới |
| `BLACKLIST_AFTER_ROTATION` | `True` | Refresh token cũ dùng lại bị từ chối |
| `UPDATE_LAST_LOGIN` | `True` | Phục vụ rà soát tài khoản |

**Câu canonical về thu hồi phiên.** Mọi tài liệu mô tả thu hồi phiên phải dùng
đúng nghĩa của câu này, không diễn đạt mạnh hơn:

> Thu hồi là **thu hồi toàn bộ refresh token** của user; **access token không
> blacklist riêng**, nên thao tác đang cầm access token còn hạn vẫn chạy được tối
> đa `ACCESS_TOKEN_LIFETIME` (15 phút) — **trừ** các request bị chặn ngay bởi
> `is_active` hoặc `must_change_password`, vì hai cổng này kiểm ở mọi request.

Hệ quả cần nói đúng: khóa tài khoản (`is_active = False`) chặn **ngay ở request
kế tiếp**; đăng xuất, reset mật khẩu và tự đổi mật khẩu thì chỉ chặn được đường
refresh, còn access token hiện hành hết hiệu lực theo hạn của nó. Viết “toàn bộ
thiết bị phải đăng nhập lại ở lần thao tác kế tiếp” cho cả bốn tình huống là
**sai** — chỉ đúng với tình huống khóa tài khoản.

Quy tắc bắt buộc:

- Refresh token **phải có trạng thái ở server** (bảng blacklist/outstanding của
  SimpleJWT). Cấu hình chỉ dùng JWT stateless cho refresh là **sai chốt** vì mất
  khả năng thu hồi.
- Thu hồi xảy ra ở bốn tình huống, tất cả đều blacklist **toàn bộ** refresh token
  đang mở của user: đăng xuất, Manager reset mật khẩu, user tự đổi mật khẩu, và
  tài khoản bị đặt `is_active = False`. Evidence của chính lần thu hồi chỉ ghi
  khi count > 0 theo §9.2.2; reset/đổi mật khẩu/status transition vẫn có evidence
  mutation riêng. Không có tình huống nào chỉ thu hồi đúng một refresh token —
  kể cả logout (§10).
- **User tự đổi mật khẩu là ngoại lệ về response, không phải về thu hồi (chốt,
  R-78).** `POST /api/change-password/` vẫn thu hồi **toàn bộ** refresh token
  như ba tình huống kia, nhưng sau đó **cấp ngay một cặp `access` + `refresh`
  mới** trong response của chính request đó. Thứ tự bắt buộc là **thu hồi trước,
  cấp sau** — làm ngược lại thì cặp token vừa cấp cũng bị blacklist ngay. Lý do
  có ngoại lệ này: user vừa chứng minh được mình biết mật khẩu cũ và vừa tự đặt
  mật khẩu mới, đá họ về màn đăng nhập là bắt đăng nhập lại bằng đúng mật khẩu
  vừa gõ hai lần — vô nghĩa, và với luồng bắt buộc đổi lần đầu (§9.2) còn tệ
  hơn: người dùng mới bị văng ra ngay giữa lần đăng nhập đầu tiên. Ba tình huống
  còn lại **không** có ngoại lệ: logout không cấp token (đó là mục đích của nó),
  reset mật khẩu do Manager thì actor không phải chủ tài khoản, và khóa tài
  khoản thì càng không. Hệ quả: đây là endpoint duy nhất vừa gọi
  `revoke_all_refresh_tokens()` vừa trả token trong response — kiểm thử phải
  khẳng định refresh token **cũ** đã chết và refresh token **mới** dùng được
  ngay, cả hai trong cùng một test.
- Access token **không** có cơ chế blacklist riêng; cửa sổ tối đa còn hiệu lực sau
  khi thu hồi refresh token là đúng `ACCESS_TOKEN_LIFETIME`. Đây là đánh đổi đã
  chấp nhận: **không** dựng thêm bảng blacklist cho access token và không tra bảng
  đó ở mỗi request để rút ngắn cửa sổ này.
- Điều đó **không** có nghĩa là request không chạm database. Mỗi request vẫn nạp
  user và kiểm `user.is_active` cùng `must_change_password` (§9.2), và RBAC vẫn
  đọc role từ DB (§8) — đây là các truy vấn bắt buộc, không phải phần “bù” bị
  cấm ở trên. Token hợp lệ **không** thay thế ba cổng này. Nhờ vậy tài khoản bị
  khóa mất quyền ngay ở request kế tiếp dù access token còn hạn, chỉ có thao tác
  chưa gửi đi mới nằm trong cửa sổ 15 phút.
- Payload token chỉ chứa `user_id`, `exp`, `jti`, `token_type`. **Không nhét
  `role`/permission vào token**: quyền đổi tức thì ở server, còn token đã phát thì
  không sửa được, nên RBAC luôn đọc từ DB (§8).
- Client chỉ giữ access token ở bộ nhớ ứng dụng. Refresh token chỉ nằm trong
  cookie host-only `Secure; HttpOnly; SameSite=Strict`, không khai báo `Domain`,
  `Path=/api/v1/auth/`; không token nào vào browser storage, log, query string
  hay `AuditLog`.
- MVP không làm đăng nhập nhiều thiết bị có quản lý danh sách phiên; nhiều thiết
  bị vẫn dùng được, và thu hồi là thu hồi **toàn bộ** refresh token của user.
- Token hợp lệ nhưng `is_active = False` trả `401 ACCOUNT_INACTIVE`, **không** trả
  `INVALID_TOKEN`: client cần phân biệt để dừng vòng lặp refresh và hiển thị “Tài
  khoản đã bị khóa, liên hệ quản lý” thay vì đẩy người dùng về màn đăng nhập rồi
  báo sai mật khẩu. Mã này chỉ dùng khi request **đã** kèm token hợp lệ của chính
  tài khoản đó nên không lộ thêm thông tin; ở `/api/v1/auth/login` vẫn giữ chung
  `401 INVALID_CREDENTIALS` cho cả sai mật khẩu lẫn tài khoản khóa.

### 9.2.2 Logout và thao tác lặp: idempotent theo trạng thái (R-110, R-111)

**Logout dùng access token để xác định actor và luôn ưu tiên cắt phiên (R-110).**
Sau khi access token hợp lệ đã nạp được user hoạt động và request qua các cổng
phân quyền/trạng thái tài khoản hiện hành, refresh cookie **không còn là điều kiện
để được logout**. Cookie chỉ là credential cần xóa ở client; server thu hồi theo
actor của access token, tuyệt đối không lấy user từ cookie. Bốn trường hợp có
cùng kết quả HTTP và cùng gọi `revoke_all_refresh_tokens(actor, LOGOUT)`:

| Refresh cookie ở request logout | HTTP | Thu hồi toàn bộ refresh của actor | Evidence |
|---|---|---|---|
| Thiếu | `204`, không body | Có | Chỉ khi thực sự thu hồi ít nhất một refresh đang hoạt động |
| Sai định dạng/chữ ký/hết hạn hoặc thuộc user khác | `204`, không body | Có | Chỉ khi thực sự thu hồi ít nhất một refresh đang hoạt động |
| Hợp lệ nhưng đã bị thu hồi | `204`, không body | Có | Chỉ khi thực sự thu hồi ít nhất một refresh đang hoạt động khác |
| Hợp lệ và đang hoạt động | `204`, không body | Có | Có: một `AuditLog` và một `OutboxEvent` cho lần thu hồi toàn cục |

Cookie luôn được clear với đúng thuộc tính cookie đã chốt. Logout là **idempotent
theo trạng thái**: gọi lại khi không còn refresh hoạt động vẫn trả `204`, helper
trả `revoked_count = 0`, không ghi `AuditLog`, không append `OutboxEvent`, không
tăng `aggregate_version`. Nếu cookie gửi lại đã chết nhưng actor còn một phiên
khác, lần gọi vẫn thu hồi phiên còn lại và sinh đúng một cặp evidence. Không thêm
mã lỗi mới: `401 INVALID_TOKEN` của logout chỉ còn áp cho access token thiếu/sai/
hết hạn; `401 ACCOUNT_INACTIVE`, `403 PASSWORD_CHANGE_REQUIRED` và thứ tự cổng
quyền giữ nguyên. Endpoint refresh vẫn trả `401 INVALID_TOKEN` cho refresh token
thiếu/sai/hết hạn/blacklist; quyết định idempotent này chỉ áp cho logout.

**Mọi thao tác lặp khác cũng phân biệt “ý định mới” với “không đổi state”
(R-111).**

- `PATCH .../status` đặt đúng giá trị hiện có trả `200` với representation hiện
  tại, là no-op: không UPDATE User, không gọi thu hồi, không AuditLog, không
  OutboxEvent và không tăng aggregate version.
- Chuyển `active → inactive` hoặc `inactive → active` là mutation thật: ghi User,
  một AuditLog và một OutboxEvent trạng thái; mỗi OutboxEvent làm version tăng
  đúng một. Riêng `active → inactive` còn gọi thu hồi toàn cục.
- `revoke_all_refresh_tokens` khi không có refresh đang hoạt động trả thành công
  với `revoked_count = 0`, không ghi dòng blacklist mới, không AuditLog, không
  OutboxEvent và không tăng version. Khi count > 0, helper ghi đúng một AuditLog
  và một OutboxEvent tổng hợp, không ghi một cặp evidence cho từng token.
- Vì vậy deactivation lặp lại sau khi đã inactive là no-op `200`; logout lặp lại
  theo R-110 là no-op `204`. Không có hard delete và không xóa lịch sử.
- Manager reset mật khẩu lặp lại **không phải no-op**: mỗi request hợp lệ là một
  ý định mới, sinh mật khẩu mới, ghi hash/cờ, trả `200`, ghi một AuditLog và một
  OutboxEvent reset, làm aggregate version tăng một. Nó vẫn gọi helper thu hồi;
  event thu hồi chỉ sinh thêm (và version chỉ tăng thêm) khi count > 0.
- User tự đổi mật khẩu hợp lệ lần nữa cũng là mutation mới theo mật khẩu mới;
  luật revoke-before-issue của R-78 giữ nguyên.

Mọi evidence nói trên cùng mutation/blacklist nằm trong transaction của caller.
Version chỉ tăng vì một OutboxEvent đã commit; no-op không tạo “khoảng trống”
version và không tạo bằng chứng giả rằng state đã đổi.

### 9.3 Import, xuất báo cáo và lịch làm việc

- Seed chạy idempotent theo `Location.code`, giữ mã/tên/địa chỉ/tọa độ CSV và
  quan hệ cha suy theo §2; không gộp location vì địa chỉ hay tọa độ trùng.
- **Reference-data readiness (chốt, R-117).** Migration chỉ tạo schema, không bịa
  shift/grace và không tự seed. Trước khi bật route/UI Feature 003, deployment
  phải chạy một kiểm tra read-only có exit code: đúng một Config hoàn chỉnh
  `id=1`, đúng 76 Location/7 BUSINESS_CENTER/69 SHOP, đúng canonical code,
  hierarchy và source coordinates. Thiếu/sai bất kỳ điều kiện nào thì gate fail
  closed và route/UI chưa được enable. Check không sửa dữ liệu và không thay thế
  hai command initialization/seed có attribution.
- Validator import áp dụng đúng bảng “dừng hay cảnh báo” ở §4.3: dừng khi vi phạm
  bất biến Config hoặc `radius_m <= 0` / `radius_m > Config.max_radius_m`; chỉ
  cảnh báo với geofence overlap và với `radius_m < Config.max_attendance_accuracy_m`.
  Sau khi bỏ công thức `d + a <= r` (§4.2), `radius_m` nhỏ hơn ngưỡng sai số
  **không** còn khiến Attendance bất khả thi, nên không phải lý do dừng import.
- Xuất Excel bằng `openpyxl`, CSV bằng stdlib. PDF phải dùng font Unicode tiếng
  Việt hoặc xuất HTML để trình duyệt in PDF.
- Export đồng bộ tối đa 10.000 dòng theo filter hiện hành. Vượt giới hạn trả lỗi
  rõ ràng yêu cầu thu hẹp filter; MVP không có background export.
- Export mặc định không có tọa độ chính xác, Maps URL, photo URL hay presigned
  URL. MANAGER/LEADER có thể bật tùy chọn tọa độ cho report được phép; hành động
  ghi `AuditLog` với filter/số dòng nhưng **không** ghi tọa độ. File trả về
  `Cache-Control: no-store`, tên file không chứa tên nhân viên; HELPDESK không có
  bulk export tọa độ.
- Báo cáo theo nhân viên bắt buộc tách “Việc tự tay hoàn thành” (`completed_by`)
  và “Việc được giao đã đóng” (`TaskAssignee`, xem §6.1); không cộng hai số này
  vào một tổng.
- `working_weekdays` mặc định Thứ Hai đến Thứ Bảy (`[0,1,2,3,4,5]`), cấu hình
  được. `Holiday` (§7) nhập tay; không tự sinh. Cả hai chỉ phục vụ **cấu hình và
  đọc báo cáo** (đánh dấu ngày nghỉ, tính số ngày công kỳ vọng); chúng **không**
  là đầu vào của bất kỳ job hay validation nào ở luồng chấm công (R-85).
- Job `MISSING_CHECK_OUT` (§5.3) vì vậy **không đọc** `working_weekdays` cũng như
  `Holiday`: nó chạy mọi ngày, quét `work_date < CURRENT_DATE`, đóng phiên bằng
  `closed_by_job = True` và **luôn** ghi `AttendanceAnomaly(MISSING_CHECK_OUT)`,
  kể cả khi `work_date` rơi vào Chủ nhật hay ngày lễ. Không có nhánh `if` nào
  trong job đọc Config. Hệ quả kiểm chứng được: số phiên `closed_by_job = True`
  luôn bằng số anomaly `MISSING_CHECK_OUT`. Người trực ngày nghỉ có bấm Check In
  thật thì thiếu Check Out vẫn là dữ liệu thiếu cần quản lý xử lý, không phải
  ngoại lệ được im lặng bỏ qua.

### 9.4 Audit và outbox: một unit of work, một envelope, một danh sách cấm (R-104)

- Ghi nghiệp vụ, dòng `AuditLog` và dòng `OutboxEvent` của cùng một hành động
  nằm trong **đúng một** transaction. Hai port ghi (`append_audit_entry`,
  `append_outbox_event`) **tham gia** transaction của caller và không bao giờ tự
  mở commit riêng: đặt `transaction.atomic()` hay `transaction.on_commit()` bên
  trong port là lỗi hồi quy, vì nó tách vết kiểm toán và sự kiện ra khỏi số phận
  của dữ liệu mà chúng mô tả. Caller rollback sau khi đã append thì **không còn
  dòng nào** — cả ba cùng sống, cùng chết.
- `AuditLog` giữ nguyên đúng tám cột ở §7
  (`id, actor, action, target_type, target_id, before, after, recorded_at`).
  Bản ghi kiểm toán là bằng chứng đóng băng, không mang thêm ngữ cảnh vận hành;
  muốn đổi hình dạng của nó là **quyết định sản phẩm**, không phải việc của một
  story kỹ thuật.
- `OutboxEvent` có envelope cố định đủ **bảy phần**, mọi publisher tương lai
  dùng chung:
  1. `event_id` — UUID server sinh, **ổn định qua mọi lần phát lại**; consumer
     khử trùng lặp theo id này chứ không theo khóa chính hay thời điểm nhận.
  2. `event_type` kèm `schema_version` — consumer cũ và mới cùng đọc được một
     dòng, không đoán hình dạng payload theo tên sự kiện.
  3. Danh tính aggregate: `aggregate_type`, `aggregate_id`, `aggregate_version`,
     ràng buộc `UNIQUE(aggregate_type, aggregate_id, aggregate_version)`; version
     đếm **theo từng aggregate**, lịch sử của aggregate khác không đẩy số này.
  4. `created_at` do server sinh, không nhận từ client.
  5. Ngữ cảnh tương quan `request_id` và `correlation_id` (AD-11) để lần một sự
     cố từ request API đến sự kiện đã phát.
  6. `payload` chỉ chứa **state tối thiểu** consumer cần, không phải bản sao
     nguyên trạng của row.
  7. Trạng thái phát (`publish_state`, `published_at`, `lease_expires_at`) do
     tầng phát sở hữu; sự kiện vừa append luôn ở `PENDING` và chưa published.
- `request_id`/`correlation_id` là `CharField(blank=True, default="", db_default="")`,
  **không nullable**. Giá trị đến từ context ambient do middleware bind theo
  vòng đời request, port tự đọc — không thêm tham số vào DTO sự kiện và không
  bắt use case chuyển tay. Chuỗi rỗng là **trạng thái bình thường** của sự kiện
  sinh ngoài request (shell, management command, job), không phải lỗi và không
  chặn append. Khi không có chain id thượng nguồn, `correlation_id` lấy bằng
  `request_id`; hai cột tách riêng để relay sau này nối chuỗi qua nhiều hop.
- Thêm hai cột này là bước **expand** của expand–migrate–contract (§7, AD-7):
  cột mới có default rỗng, không backfill, không bước contract. Default phải nằm
  ở **DDL** (`db_default`), không chỉ ở phía Python: `default=` của Django được
  áp khi ORM dựng câu INSERT, nên một cột `NOT NULL` chỉ có `default=` vẫn từ
  chối mọi INSERT không nêu tên nó — kể cả INSERT của **phiên bản tiến trình
  cũ** đang chạy song song trên schema đã migrate, đúng tình huống của rolling
  deploy. Không có `db_default`, lời hứa “không cần backfill” là lời hứa suông.
- Danh sách cấm áp dụng cho **cả** `OutboxEvent.payload` lẫn
  `AuditLog.before`/`after`: mật khẩu (kể cả mật khẩu server sinh), token /
  credential / chữ ký, cookie và session, **mọi chuỗi chứa `://`** (bao gồm
  presigned URL, photo URL và Maps URL), object key và nội dung ảnh, tọa độ
  chính xác, và câu chữ UI/push. Quy tắc này là hệ quả trực tiếp của §9.3 và
  của nguyên tắc “không ghi bí mật vào log/audit”.
- Bộ lọc nằm ở **shared kernel** và chạy **tại port, trước khi tạo dòng**. Vi
  phạm ném lỗi, hủy toàn bộ unit of work của caller (không ghi nghiệp vụ, không
  audit, không event); thông báo lỗi nêu **đường dẫn** khóa vi phạm và **không**
  nêu giá trị — bộ lọc chống rò rỉ thì bản thân nó không được thành chỗ rò.
  Bộ lọc khớp **tên khóa chính xác**, không khớp chuỗi con, nên các cờ nghiệp vụ
  hợp lệ như `must_change_password` hay `active_refresh_sessions` vẫn ghi bình
  thường; khớp chuỗi con sẽ đẩy người viết vào chỗ đặt tên né bộ lọc.
- Ba lời hứa trên (một transaction, tương quan đi tới nơi, payload sạch) phải
  được khẳng định bằng test **đỏ khi vi phạm** trên PostgreSQL thật, gồm một
  test ép caller rollback **sau** khi cả hai port đã append. Unit test/mock hay
  SQLite không đủ (§10, QUY_TAC §10).

### 9.5 Relay outbox: PostgreSQL là nguồn sự kiện, transport chỉ là đường đi (R-105)

- §9.4 dừng ở chỗ sự kiện đã nằm trong PostgreSQL ở trạng thái `PENDING`. R-105
  quy định phần còn lại: **ai** lấy sự kiện đó ra, **khi nào** thử lại, và **lúc
  nào** thì được phép ngừng thử. Nguyên tắc bao trùm: mọi quyết định của relay
  (nhận việc, thời hạn giữ, số lần đã thử, mốc thử lại kế tiếp, trạng thái cuối)
  là một **thay đổi dòng đã commit trong PostgreSQL**, không phải biến trong bộ
  nhớ tiến trình và cũng không phải trạng thái của transport. Tiến trình relay
  chết bất cứ lúc nào thì toàn bộ tiến độ vẫn đọc được từ database.
- Relay nhận việc bằng `SELECT ... FOR UPDATE SKIP LOCKED` kèm một cột
  `lease_expires_at` được ghi xuống. `SKIP LOCKED` khiến hai worker chạy song
  song **chia nhau** hàng đợi thay vì xếp hàng chờ nhau, và không sự kiện nào bị
  hai worker cùng sở hữu. Lease là phần bù cho việc **không có bước trả lại**:
  worker bị `kill -9` không kịp nhả gì cả, nên quyền sở hữu phải **tự hết hạn**.
  Lease hết hạn là sự kiện quay lại trạng thái nhận được, **không cần thao tác
  vận hành nào**. Một hàng đợi chỉ phục hồi khi có người vào database sửa tay là
  hàng đợi đã hỏng.
- Hệ quả trực tiếp của việc lease **được phép** hết hạn: chủ cũ có thể vẫn đang
  publish trong lúc chủ mới đã claim hợp lệ. Vì vậy mọi lệnh ghi của worker lên
  một dòng đã claim phải **kèm điều kiện danh tính của claim** (`leased_by` và
  `lease_expires_at` mà nó claim theo). Ghi vô điều kiện là cách một worker chậm
  đưa dòng `PUBLISHED` của chủ mới về `PENDING` (lần gửi thứ ba) hoặc
  `DEAD_LETTER` một sự kiện đã gửi xong. Ghi hụt **không** phải thành công,
  không phải thất bại, không phải hết lượt: nó là một kết cục riêng, được đếm và
  ghi log riêng, và không được sửa gì trong bộ nhớ tiến trình.
- Relay **tự mở transaction ngắn của chính nó** khi nhận việc. Đây không phải
  ngoại lệ của §9.4: quy tắc “không tự commit” ràng buộc các port `append_*` vì
  chúng chạy **bên trong** unit of work của một thay đổi nghiệp vụ. Relay chạy
  độc lập, không có thay đổi nghiệp vụ nào để đi cùng, nên nó phải sở hữu ranh
  giới transaction của mình — và ranh giới đó phải **ngắn**, không bao giờ ôm
  lời gọi transport bên trong.
- Giao nhận là **at-least-once**, không phải exactly-once, và đây là lựa chọn có
  chủ đích. Một worker publish thành công rồi chết trước khi kịp ghi nhận điều
  đó để lại đúng một dòng `PENDING` còn lease — không cách nào phân biệt với một
  lần publish chưa từng xảy ra. Đoán rồi bỏ qua là **mất sự kiện**; đoán rồi phát
  lại là **trùng sự kiện**. Hệ thống chọn phát lại. Hệ quả bắt buộc: **consumer
  phải khử trùng lặp bền vững theo `event_id`**, bằng ràng buộc `UNIQUE` trên
  `(consumer, event_id)` chứ không phải bằng đọc-rồi-ghi; hai consumer chạy song
  song trên cùng một lần phát lại thì đúng một bên làm việc, bên còn lại bị
  **database** từ chối. Bản ghi khử trùng lặp phải **cùng sống cùng chết** với
  công việc mà nó bảo vệ: nếu công việc rollback mà dấu khử trùng lặp vẫn còn,
  sự kiện bị đánh dấu “đã xử lý” trong khi chưa xử lý gì, và mọi lần phát lại sau
  đó đều bị chặn.
- Thứ tự **chỉ** được bảo đảm theo từng `(aggregate_type, aggregate_id)` qua
  `aggregate_version` (§9.4). Không có thứ tự toàn cục giữa các aggregate và
  không được viết consumer dựa vào một thứ tự như vậy.
- Thất bại transport đưa sự kiện **trở lại `PENDING`** với `next_attempt_at` =
  `now + min(base * 2^(số lần đã thử - 1), trần)`. Công thức là hàm thuần, và
  trần là **bắt buộc**: backoff nhân đôi không giới hạn sẽ đẩy một sự kiện sang
  khoảng chờ tính bằng ngày, tức là mất sự kiện dưới một cái tên khác. Lỗi của
  một sự kiện **không** làm hỏng cả lô: mỗi sự kiện được ghi nhận kết quả riêng.
  Điều này áp dụng cho **mọi** thứ transport ném ra, không riêng lỗi hạ tầng đã
  khai báo. Một exception ngoài hợp đồng là **defect của adapter**: nó được ghi
  log kèm traceback, claim của sự kiện đó được **trả lại** để dòng không bị treo
  tới khi lease hết hạn, và lô chạy tiếp — nhưng nó **không** được chuyển thành
  lịch backoff, vì đó là nói dối rằng hạ tầng hỏng. Lượt thử đã tiêu không hoàn
  lại.
- Bộ số backoff mặc định phải phủ được một **cửa sổ gián đoạn đã công bố**, và
  trần phải thực sự chạm tới trong ngân sách thử lại. Đây không phải chuyện thẩm
  mỹ: `DEAD_LETTER` chưa có đường quay lại, nên một bộ số quá ngắn biến một sự
  cố vài phút thành toàn bộ backlog nằm vĩnh viễn ở trạng thái cuối. Lý do chọn
  bộ số ghi ngay cạnh bộ số, ở nơi người vận hành đọc được.
- Hết ngân sách thử lại thì sự kiện chuyển sang trạng thái cuối **`DEAD_LETTER`**
  và **ở lại trong bảng**. Không xóa, không im lặng bỏ qua. Đồng thời phát một
  cảnh báo mang `event_id`, danh tính aggregate, số lần đã thử và **lý do đã làm
  sạch**. Ngân sách được trừ **tại lúc nhận việc**, nên worker liên tục chết giữa
  chừng cũng hết lượt chứ không thử lại vô hạn.
- Danh sách cấm ở §9.4 áp dụng nguyên vẹn cho cảnh báo và log của relay. Khác
  biệt duy nhất là **cách xử lý**: `payload` do hệ thống này dựng nên bị **từ
  chối**, còn thông báo lỗi của transport do hệ thống khác viết ra nên bị **che
  bỏ** phần cấm và giữ lại phần chẩn đoán — từ chối nó chỉ làm mất manh mối mà
  không làm hệ thống an toàn hơn. Độ dài lý do lưu xuống phải bị chặn: bề rộng
  một cột không được để hệ thống bên ngoài quyết định.
- Cấu hình relay (kích thước lô, thời hạn lease, số lần thử tối đa, base và trần
  backoff, tên transport) là cấu hình **có kiểu và fail-closed ngay lúc khởi
  động**. Tên transport không hợp lệ làm tiến trình **dừng** kèm tên biến môi
  trường; các số đếm nói trên phải **dương** — giá trị `0` không có nghĩa “không
  giới hạn” mà có nghĩa relay không nhận gì, hoặc lease đã hết hạn ngay khi đặt,
  hoặc sự kiện chết trước khi được thử lần nào. Lặng lẽ rơi về mặc định là để
  một triển khai tưởng mình đang phát sự kiện trong khi không.
- Các lời hứa về đồng thời (không sở hữu chéo), về phục hồi lease và về thử lại
  phải được khẳng định bằng test chạy **nhiều luồng trên PostgreSQL thật**.
  `SKIP LOCKED` là hành vi khóa dòng của PostgreSQL: SQLite không có nó và sẽ
  làm test **xanh sai**, còn mock chỉ khẳng định rằng code đã gọi đúng phương
  thức mà chính nó được viết ra để gọi. Tình trạng transport hỏng được chứng minh
  bằng một transport thay thế **hỏng có kiểm soát**, không phải bằng broker thật.

### 9.6 Quan trắc vận hành: telemetry đã lọc, lưu trữ có hạn và cảnh báo có ngưỡng (R-106)

- R-105 dừng ở chỗ relay đã ghi đủ trạng thái xuống PostgreSQL. R-106 quy định
  phần còn lại: **ai nhìn thấy** trạng thái đó, **dữ liệu quan trắc sống bao
  lâu**, và **khi nào thì im lặng bị coi là hỏng**. Nguyên tắc bao trùm: im
  lặng **không** phải bằng chứng khỏe mạnh. Một relay chưa từng chạy, một job
  dọn dẹp chưa từng được lên lịch và một hệ thống hoàn toàn bình thường tạo ra
  cùng một thứ — không có bản ghi nào — nên trạng thái sức khỏe phải phân biệt
  được **`ok`**, **`alert`** và **`unknown`**, và `unknown` không bao giờ được
  gộp vào `ok`.
- Mọi bản ghi log phải mang **`request_id` và `correlation_id`** của ngữ cảnh
  đang chạy, được gắn ở tầng hạ tầng log chứ không phải bằng cách người viết
  nhớ truyền tay qua từng lời gọi. Không có ngữ cảnh thì hai trường đó là
  **chuỗi rỗng**: rỗng là câu trả lời đúng cho một tiến trình chạy ngoài
  request, không phải lỗi và không được dựng ra một id giả. Không đọc id tương
  quan do client gửi lên và không luồn id tương quan qua DTO.
- Danh sách cấm ở §9.4 áp dụng nguyên vẹn cho **mọi** telemetry, không riêng
  log của relay: không token, không URL đã ký, không cookie, không mật khẩu,
  không byte ảnh, không tọa độ chính xác, không `payload` nghiệp vụ. Mọi trường
  chuỗi của một cảnh báo phải đi qua **đúng một bộ lọc dùng chung** trước khi
  chạm tới bản ghi — cùng bộ lọc mà relay dùng cho lý do thất bại của transport
  (§9.5). Cảnh báo chỉ mang **định danh, số đếm và ngưỡng**; nó là tín hiệu để
  người vận hành đi tra, không phải bản sao của dữ liệu.
- Metric phải khai báo trước: **tên metric và tập giá trị hợp lệ của từng nhãn
  đều là từ vựng đóng**. Một tên metric ngoài danh sách hoặc một giá trị nhãn
  ngoài từ vựng bị **bỏ**, kèm đúng một cảnh báo chỉ nêu tên metric. Lý do là
  cardinality: `event_id`, id người dùng, đường dẫn URL thô hay tọa độ đưa vào
  nhãn sẽ sinh ra số chuỗi thời gian không chặn trên và làm hỏng chính hệ thống
  quan trắc. Từ vựng đóng khiến điều đó **không thể xảy ra do sơ ý**, thay vì
  chỉ bị cấm bằng lời.
- Telemetry **không bao giờ được làm hỏng việc mà nó quan sát**. Mọi điểm phát
  metric, log quan trắc và cảnh báo đều chặn lỗi tại chỗ: một sink hỏng, một
  handler ném exception hay một metric sai hợp đồng chỉ được phép làm mất bản
  ghi quan trắc đó, tuyệt đối không được làm hỏng một lô relay, một response API
  hay một thay đổi nghiệp vụ.
- Dữ liệu quan trắc có **thời hạn công bố**, và thời hạn đó được ghi thành hằng
  số có tên trong mã nguồn để tài liệu và cấu hình sink cùng trỏ về một chỗ:
  log **30 ngày**, trace **30 ngày**, metric **90 ngày**. Trong database, dấu
  khử trùng lặp (`ProcessedEvent`) giữ **30 ngày**, sự kiện outbox đã publish
  giữ **30 ngày** tính từ lúc publish, sự kiện ở trạng thái cuối giữ **90 ngày**
  tính từ lúc tạo. `AuditLog` là **ngoại lệ tuyệt đối**: chính sách **hai năm**
  của nó (§9.4) không do job dọn dẹp nào thực thi, và không có đường mã nguồn
  nào được phép xóa một dòng audit.
- Job dọn dẹp **chỉ** được xóa ba nhóm dòng nói trên. Sự kiện `PENDING` ở bất kỳ
  tuổi nào là công việc **chưa làm xong** — xóa nó là mất sự kiện, nên nó không
  bao giờ nằm trong tập chọn. Việc xóa chạy **theo lô có kích thước cấu hình
  được**, để một lần dọn dẹp muộn không khóa bảng bằng một lệnh `DELETE` khổng
  lồ, và mỗi bảng báo cáo số dòng đã xóa của riêng nó.
- Ngưỡng cảnh báo là **cấu hình fail-closed lúc khởi động** như cấu hình relay
  (§9.5), và phủ đủ các cách hàng đợi hỏng: **độ sâu backlog** và **tuổi của sự
  kiện đến hạn cũ nhất** (backlog nhỏ nhưng kẹt cũng là hỏng), **số lease quá
  hạn**, **số sự kiện ở trạng thái cuối**, **bất biến bị vi phạm** (dòng ở trạng
  thái đã ngừng dùng, hoặc `PUBLISHED` mà không có mốc publish), và **độ trễ
  nhịp tim** của cả worker relay lẫn job định kỳ. Ngưỡng `0` là ngưỡng hợp lệ và
  có nghĩa với số sự kiện ở trạng thái cuối: một dòng cũng là quá nhiều.
- Bằng chứng “job đã chạy” phải là **một dòng đã commit trong PostgreSQL**
  (nhịp tim mang tên job, mốc bắt đầu, mốc thành công gần nhất và kết cục), chứ
  không phải một bản ghi log mà không ai đọc. Chưa từng có dòng nhịp tim thì
  check tương ứng là **`unknown`** và vẫn phát cảnh báo; dòng cũ hơn ngưỡng là
  **`alert`**. Trạng thái tổng hợp xếp hạng **`alert` > `unknown` > `ok`**.
- Đánh giá sức khỏe là **hàm đọc thuần**: nó truy vấn, so ngưỡng và trả về báo
  cáo, không tự phát cảnh báo và không tự ghi gì. Nhờ vậy một endpoint đọc sau
  này (§10) dùng lại đúng phép đánh giá đó thay vì viết lại ngưỡng lần thứ hai.
- Ghi quan trắc của một thay đổi nghiệp vụ **thất bại** phải xảy ra **ngoài**
  transaction nghiệp vụ, ở cả nhánh commit lẫn nhánh exception **nghiệp vụ đã
  được phân loại**, và bản ghi
  đó **không** phải sự kiện outbox, cũng **không** phải dòng `AuditLog` — nó là
  dữ liệu quan sát, không phải bất biến nghiệp vụ. Ghi nó bên trong transaction
  sẽ khiến nó bị cuốn theo rollback, tức là mất đúng bằng chứng về lần thất bại
  cần điều tra. Một lỗi trong chính việc ghi quan trắc được log lại và **không**
  được che mất exception nghiệp vụ gốc.
  Riêng exception hạ tầng chưa phân loại của Attendance theo R-125 không đăng ký
  AttendanceAttempt; nó chỉ đi telemetry 5xx đã lọc.
- Ba lời hứa trên (ghi quan trắc sống qua rollback, dọn dẹp không chạm dòng cấm,
  thiếu quan trắc ra `unknown`) phải được khẳng định bằng test chạy trên
  PostgreSQL thật, với `transaction=True` ở mọi chỗ có khẳng định về hành vi
  transaction (§10, QUY_TAC §10).

### 9.7 Triển khai nhiều vùng sẵn sàng và cô lập môi trường (R-107)

- Hệ thống chạy trên **ba môi trường** — `development`, `staging`, `production`
  — và ba môi trường đó **không dùng chung bất kỳ tài nguyên nào**: không chung
  project database, không chung bucket lưu ảnh, không chung database Redis hay
  tiền tố key, không chung khóa ký, không chung credential biên. Đây là quy tắc
  **không tiến trình nào tự kiểm được**: một tiến trình chỉ nhìn thấy môi trường
  của chính nó và không có cách nào biết bucket nó được giao có phải cũng là
  bucket của production hay không. Vì vậy danh tính của cả ba phải được ghi vào
  **một bản kê được commit** (`deploy/environments.yaml`) và có lệnh so trùng
  chạy trong CI ở mọi thay đổi.
- Bản kê đó chỉ chứa **danh tính**: mã project, tên bucket, tiền tố key, **tên**
  header credential, cờ cấu hình. Nó **không bao giờ** chứa một giá trị bí mật
  nào — không mật khẩu, không token, không chuỗi kết nối đầy đủ. Bí mật chỉ tồn
  tại trong kho bí mật của nền tảng triển khai và đến tiến trình qua biến môi
  trường.
- Một lựa chọn hạ tầng **chưa được người có thẩm quyền quyết** phải được ghi
  đúng như vậy trong bản kê, bằng một giá trị `UNRESOLVED` mang nghĩa riêng chứ
  không phải bằng một giá trị đoán tạm. Chừng nào production còn bất kỳ lựa chọn
  `UNRESOLVED` nào, **không ai được tuyên bố production đã sẵn sàng**, và điều
  đó phải là một lệnh kiểm tra trả về mã lỗi kèm danh sách từng lựa chọn còn
  treo — không phải một câu trong biên bản họp.
- Mọi biến môi trường của phần triển khai đều đọc qua **đúng một lớp kiểm tra
  fail-closed chạy trước khi Django được cấu hình**, và mọi thông báo thất bại
  phải **gọi tên biến sai**. Biến được đặt tên nhưng để rỗng là **một lần sửa
  dở**, không phải yêu cầu lấy mặc định: nó dừng khởi động và nói rõ như vậy.
  Tên môi trường là **từ vựng đóng** ba giá trị — một lỗi chính tả như `prod`
  dừng khởi động, thay vì được hiểu thành “không phải production” và mở đúng
  những nới lỏng mà lỗi chính tả đó vô tình mua được.
- Ngoài `development`, mọi tên do dự án tự đặt trong hạ tầng dùng chung không có
  ranh giới cứng (tiền tố key Redis, tên bucket) **bắt buộc chứa tên môi
  trường**. Nhờ vậy một file cấu hình bị copy nhầm giữa hai môi trường không thể
  trông có vẻ đúng.
- Đường vào database được tách làm **hai kết nối có mục đích khác nhau và không
  được phép trùng nhau**: một kết nối **qua pooler ở chế độ session** cho toàn
  bộ đường chạy runtime, và một kết nối **trực tiếp** chỉ dùng cho migration,
  `pg_dump` và restore, chỉ tiếp cận được từ một danh sách địa chỉ egress cố
  định. Không đường mã nguồn nào của ứng dụng được đọc kết nối thứ hai. Ghi cùng
  một chuỗi kết nối vào cả hai bị **từ chối lúc khởi động**: nó xóa sạch ranh
  giới trên mà không làm thay đổi bất cứ thứ gì quan sát được.
- Kết nối tới hàng đợi đi qua internet công cộng nên ngoài `development` **bắt
  buộc mã hóa transport và có mật khẩu**; một endpoint hàng đợi không xác thực
  chỉ cách việc trở thành hàng đợi của người khác đúng một lượt quét địa chỉ.
  **Kho lưu kết quả job phải tắt**, và việc đặt nó bị từ chối chứ không được âm
  thầm chấp nhận: job của hệ thống trả về payload dựng từ dữ liệu nhân sự, không
  ai đọc lại, nên bật nó chỉ tạo thêm một bản sao dữ liệu đó nằm dưới chính sách
  lưu trữ khác với database sinh ra nó (§9.6).
- Ảnh bằng chứng lưu ở bucket **không mở công khai**, chỉ đọc qua URL ký có hạn
  (§9.4), và gợi ý vị trí lưu trữ giới hạn trong khu vực châu Á – Thái Bình
  Dương. Phải nói thẳng trong tài liệu vận hành rằng **gợi ý vị trí không phải
  cam kết pháp lý về nơi lưu trữ dữ liệu**: một nghĩa vụ về data residency không
  được coi là đã đáp ứng bằng cấu hình này.
- Trình duyệt chỉ nói chuyện với ứng dụng web; mọi lời gọi API đi qua một chặng
  proxy ở biên. Chặng đó gắn một **credential nguồn** — một header do triển khai
  quy định, giá trị tối thiểu **32 ký tự** — và **xóa header cùng tên do client
  gửi lên trước khi gắn giá trị thật**, vì nếu trình duyệt tự cung cấp được
  credential thì câu trả lời của lớp chặn phụ thuộc vào request thay vì vào
  triển khai, tức là không chặn gì cả. Credential **không bao giờ** được nhúng
  vào bundle trình duyệt, không log, không echo lại trên response.
- Ở phía origin, request thiếu hoặc sai credential nhận **403** với thân lỗi
  canonical, so sánh theo **thời gian hằng**, và thông báo không được để lộ rằng
  chính credential mới là thứ sai. Lớp chặn này tồn tại **song song** với lớp
  chặn ở biên chứ không thay thế nó: nó khiến `403` là thứ kiểm chứng được ngay
  hôm nay qua socket, và vẫn còn hiệu lực nếu rule ở biên bị xóa hay xếp sai thứ
  tự. Mọi response trên đường API mang dữ liệu của **một** phiên đã xác thực nên
  phải **không cache được**.
- Cấu trúc chạy production phải trải trên **ít nhất hai vùng sẵn sàng**, với đầu
  vào công khai duy nhất là bộ cân bằng tải, các instance ứng dụng nằm ở mạng
  riêng và chỉ nhận lưu lượng **từ chính bộ cân bằng tải đó**, mỗi vùng có đường
  ra riêng, và **đúng một** tiến trình lên lịch job định kỳ trong toàn hệ thống —
  hai bản chạy song song sẽ nhân đôi mọi job. Danh sách **đích ra ngoài** phải
  liệt kê được hết; mọi đích không nằm trong danh sách là lỗi cấu hình.
- Phát hành theo thứ tự **migration trước, rollout sau**, và mỗi migration phải
  tương thích với bản mã nguồn liền trước, vì trong lúc rollout luôn có hai
  phiên bản cùng nói chuyện với một schema (§10.1).
- Toàn bộ những điều trên phải có **runbook tái lập được** (`docs/TRIEN_KHAI.md`)
  và ba lệnh kiểm chứng chạy được: **so trùng tài nguyên giữa các môi trường**,
  **chặn tuyên bố production sẵn sàng khi còn lựa chọn treo**, và **smoke test
  chứng minh request không kèm credential bị origin trả 403** — lệnh cuối chỉ in
  mã trạng thái, không in header và không in thân response.
- **Hạn mức số request là thuộc tính của triển khai, không phải của tiến trình.**
  Vì cấu trúc trên bắt buộc từ hai instance API trở lên, bộ đếm của mọi hạn mức
  (đăng nhập, làm mới phiên, đổi mật khẩu — §9.2) phải nằm ở **kho dùng chung cho
  mọi tiến trình**; nếu mỗi instance đếm riêng thì hạn mức công bố bị nhân lên
  theo số instance và mất hiệu lực sau mỗi lần khởi động lại. Kho này do **một
  biến môi trường** chọn, và ngoài `development` một lựa chọn cục bộ theo tiến
  trình **phải chặn khởi động** với thông báo gọi đúng tên biến — im lặng chấp
  nhận nó nghĩa là hạn mức trong tài liệu và hạn mức thật sự khác nhau mà không
  ai thấy. Bản kê môi trường phải ghi lựa chọn này để lệnh so trùng đọc và từ
  chối được từ bên ngoài tiến trình.

### 9.7.1 Hạn mức endpoint xác thực (R-112)

Các số từng xuất hiện ở R-109 nay được chốt thành contract nghiệp vụ/HTTP:

| Scope | Endpoint | Hạn mức | Khóa đếm |
|---|---|---:|---|
| `login` | `POST /api/v1/auth/login` | 10 request / 60 giây | Client IP canonical do server suy ra sau trusted-proxy normalization; không tin `X-Forwarded-For` tùy ý |
| `refresh` | `POST /api/v1/auth/refresh` | 120 request / 60 giây | Client IP canonical như trên, kể cả cookie thiếu/sai |
| `password_change` | `POST /api/v1/change-password` | 5 request / 60 giây | `User.id` đã xác thực |

Mọi request tới scope đều tính, bất kể sau đó credential/DTO đúng hay sai. Login
và refresh chạy throttle sau cổng hạ tầng nhưng trước parse DTO/nghiệp vụ;
password change chạy sau authentication và permission/account gate hiện hành,
trước DTO. Vượt hạn mức trả `429 THROTTLED` bằng error envelope canonical, có
`Retry-After`, không gọi service và không ghi AuditLog/OutboxEvent.

Ba scope dùng đúng `core.cache.THROTTLE_CACHE_ALIAS` và cache dùng chung của
R-109; cấm alias/cache subsystem thứ hai. Kho đếm không truy cập được là
**fail-closed**: request dừng với `503 SERVICE_UNAVAILABLE` bằng envelope
canonical, không được coi như còn quota và không chạy nghiệp vụ. `THROTTLED` và
`SERVICE_UNAVAILABLE` là hai error code được R-112 phê duyệt; không dùng
`INVALID_CREDENTIALS`/`INVALID_TOKEN` để che lỗi throttle hay hạ tầng.

Kiểm thử bắt buộc dùng clock kiểm soát để chứng minh request trong/ngoài cửa sổ,
key độc lập và key dùng chung đúng phạm vi; kiểm thử integration dùng backend
cache chung để chứng minh hai process/worker không được mỗi bên một quota. Test
cache failure phải chứng minh fail-closed và không có side effect. Không thêm
dependency, Redis instance hay migration cache mới.

### 9.8 Nền tảng di trú, sao lưu và khôi phục (R-108)

- R-107 chứng minh ba môi trường **không dùng chung tài nguyên nào**; nó không
  nói gì về việc dữ liệu trong một môi trường có **quay lại được** hay không.
  Mục này bổ sung đúng phần còn thiếu đó: một thay đổi schema phải **an toàn khi
  áp lên dữ liệu thật**, một bản sao lưu phải **đã từng được khôi phục thật**,
  và mọi con số về khôi phục cũng như về năng lực phục vụ phải là **số đo được
  ghi lại**, không phải một câu khẳng định trong tài liệu. Bằng chứng nằm ở một
  file được commit, và có lệnh kiểm chứng đọc file đó.
- Phát hành vẫn theo thứ tự **migration trước, rollout sau** (§9.7), do **đúng
  một** job phát hành chạy qua kết nối trực tiếp hạn chế egress, không phải bởi
  tiến trình ứng dụng lúc khởi động. Schema sau migration **bắt buộc tương thích
  với bản mã nguồn liền trước**, vì suốt quá trình rollout luôn có hai phiên bản
  cùng nói chuyện với một schema: một cột `NOT NULL` mới phải mang `db_default`
  để tiến trình cũ vẫn ghi được, và một thao tác **xóa** cột hay bảng phải chờ
  một lần phát hành sau (mở rộng — chuyển dữ liệu — thu hẹp, §10.1). Đây là quy
  tắc **không test nào bắt được**: database dùng để test được dựng từ chính các
  file migration đó, nên nó luôn thấy schema mới. Vì vậy phải có **lệnh kiểm tra
  đọc tĩnh** các file migration và chạy trong CI ở mọi thay đổi.
- Database phải được **bảo vệ hằng ngày** với thời gian lưu **tối thiểu 30
  ngày**; mục tiêu là **RPO ≤ 24 giờ** và **RTO ≤ 4 giờ**. Đây là **mục tiêu**,
  không phải mô tả hiện trạng: các lựa chọn phía nhà cung cấp quyết định chúng
  có đạt được hay không (`plan`, `pitr_retention_days`, cơ chế sao lưu, lịch
  chạy) **chưa được người có thẩm quyền chọn** và phải nằm ở `UNRESOLVED` trong
  bản kê cho tới khi được chọn, đúng theo §9.7. Một mục tiêu chưa có lựa chọn hạ
  tầng đỡ phía dưới là **một ý định**, và phải đọc ra như vậy.
- **Một bản sao lưu thành công không bao giờ là bằng chứng có thể khôi phục.**
  Thứ duy nhất chứng minh được điều đó là **một lần khôi phục đã thực sự chạy**:
  ít nhất **mỗi 90 ngày**, khôi phục vào **một project mới, cô lập**, không bao
  giờ nối vào bất kỳ consumer nào của production, rồi kiểm tra bản khôi phục đó
  trên các bất biến mà một bản sao hỏng sẽ vi phạm — bảng người dùng, `AuditLog`,
  token còn hiệu lực và token đã thu hồi, hàng đợi sự kiện đi ra, và **phiên bản
  schema** so với mã nguồn đang chạy. Việc kiểm tra đó **chỉ đọc**, và phải bị
  **từ chối trước khi mở kết nối** nếu chuỗi kết nối được giao trỏ tới chính
  database runtime hay database admin: một lần kiểm tra chạy nhầm trên production
  sẽ **luôn xanh** và không chứng minh gì cả — kết quả tệ nhất trong mọi kết quả.
- Mỗi lần khôi phục và mỗi lần đo năng lực phải ghi lại **thời điểm chạy, số đo
  thu được, và một trong hai kết luận `passed` / `failed`**. Số đo **vượt mục
  tiêu là `failed`, kèm tên người chịu trách nhiệm khắc phục** — không có “đạt
  gần đủ”, không có kết luận để trống. Một số đo tệ được ghi thành `passed` còn
  nguy hiểm hơn không đo, vì nó biến một rủi ro đã biết thành một rủi ro đã được
  ai đó ký nhận là không tồn tại.
- Khôi phục **làm sống lại** những gì bản sao có tại thời điểm đó: token còn hạn
  của các phiên đã bị thu hồi sau đó, và các sự kiện trong hàng đợi đi ra đã gửi
  xong — kèm cả lease của tiến trình gửi đã không còn tồn tại (§9.5, §9.6). Vì
  vậy **thu hồi toàn bộ phiên** và **xóa lease treo trước khi bật lại tiến trình
  gửi** là **một phần bắt buộc của thủ tục khôi phục**, không phải việc dọn dẹp
  làm sau.
- Năng lực phục vụ là thứ **đo**, không phải thứ tuyên bố. Số đo chỉ được coi là
  bằng chứng cho mục tiêu p95 nếu nó được lấy trên **ít nhất 50 tài khoản thật**
  và ở **mức đồng thời không thấp hơn mức mà mục tiêu được phát biểu**; đo trên
  một tài khoản lặp lại là đo một dòng dữ liệu, không phải đo hệ thống. File tài
  khoản dùng cho phép đo là **file bí mật**: không được commit và phải xóa sau
  khi đo. Không công cụ nào trong mục này được in ra chuỗi kết nối, token, mật
  khẩu, hay URL có kèm thông tin đăng nhập — chỉ tên bảng, tên cột, tên biến môi
  trường và các con số.
- Toàn bộ những điều trên phải kiểm chứng được bằng các hiện vật được commit —
  `deploy/environments.yaml` (khối `backup:`) và `deploy/recovery-evidence.yaml`
  (mục tiêu, lần khôi phục gần nhất, lần đo năng lực gần nhất) — cùng các lệnh:
  `scripts/migration_check.py check` (chạy trong CI), `manage.py verify_restore`,
  `scripts/deployment_check.py recovery-ready`, `scripts/capacity_check.py`
  (`measure`), và một kiểm tra sức khỏe báo động khi **lần khôi phục gần nhất đã
  quá hạn 90 ngày** (§9.6). Thủ tục đầy đủ nằm ở `docs/TRIEN_KHAI.md` §9.

## 10. API contract và kiểm thử bắt buộc

Ví dụ request Check In tại tọa độ có hai ứng viên (`HCM000079` và `HCM010005`
trùng tọa độ, §2), lần đầu chưa chọn:

```json
{
  "latitude": 10.785850,
  "longitude": 106.692600,
  "accuracy_m": 8,
  "captured_at": "2026-08-11T09:00:00+07:00"
}
```

Server trả `409 LOCATION_CHOICE_REQUIRED`:

```json
{
  "error": "LOCATION_CHOICE_REQUIRED",
  "location_candidates": [
    {"id": 1, "code": "HCM000079", "name": "Cửa Hàng MobiFone Trực Tuyến Tại HCM", "distance_m": 0.0},
    {"id": 61, "code": "HCM010005", "name": "Cửa Hàng 54 Phạm Ngọc Thạch (MobiFone TTKD Sài Gòn-CH ND cũ)", "distance_m": 0.0}
  ]
}
```

Client gửi lại đúng payload cũ kèm `"selected_location_id": 61`; server tính lại
danh sách ứng viên và chỉ chấp nhận lựa chọn nằm trong danh sách đó. Lựa chọn
nằm ngoài danh sách **không rỗng** vừa tính lại — vì client gửi sai id, hoặc vì
người dùng đã đi tới một vùng phủ khác giữa hai request — trả `422
INVALID_LOCATION_CHOICE` kèm danh sách ứng viên mới nhất để client hiển thị lại.
Nếu người dùng đã đi ra ngoài mọi vùng và danh sách rỗng thì §5.1 bước 8 trả
`OUTSIDE_RADIUS` trước khi xét id.

`POST /api/attendance/check-in` và `POST /api/attendance/check-out` không nhận
`recorded_at`, `work_date` hay `kind`; server tự tạo chúng, `kind` suy từ route
(§5.4). Request có GPS và tùy chọn `captured_at`, `selected_location_id`, **không
có `user_id`, không có `kind`**. Payload chứa `user_id` hoặc `kind` trả
`400 SERVER_OWNED_FIELD`. Response thành công trả `recorded_at`, `work_date`,
`location`, `validation_result`; nhiều ứng viên trả `409
LOCATION_CHOICE_REQUIRED` kèm danh sách Location (mỗi phần tử có `code` và `name`,
§3.1). `accuracy_m > Config.max_attendance_accuracy_m` trả `422 WEAK_GPS`; không
ứng viên nào trả `422 OUTSIDE_RADIUS`; `selected_location_id` ngoài tập ứng viên
**không rỗng** trả `422 INVALID_LOCATION_CHOICE`. Check Out khi không có phiên mở trả
`409 NO_OPEN_SESSION`; Check In khi đang có phiên mở trả `409
SESSION_ALREADY_OPEN` (kể cả khi thua race ở partial unique index, §5.3). Mọi
request đã qua xác thực/phân quyền — kể cả request thành công — ghi đúng một
`AttendanceAttempt` với `outcome` tương ứng (§5.2); request bị chặn ở `401`/`403`
hoặc `400 SERVER_OWNED_FIELD` **không** ghi attempt (§5.1).

**Mã lỗi canonical khi không có ứng viên là `OUTSIDE_RADIUS`**, trùng tên với
`AttendanceAttemptOutcome.OUTSIDE_RADIUS` và với báo cáo lần bị từ chối ở §9.
`OUTSIDE_GEOFENCE` chỉ là giá trị của `LocationValidationResult` (§4.2), **không**
dùng làm mã lỗi API — hai khái niệm khác nhau nên giữ hai tên khác nhau.

Response Check In/Out trả thêm `session` (`id`, `work_date`, `check_in_at`,
`check_out_at`, `check_in_location_id`, `check_out_location_id`,
`duration_minutes`) và `punch_index` để client hiển thị đúng khi
một ngày có nhiều lượt. **`punch_index` là số thứ tự trong một dãy duy nhất gồm
cả IN lẫn OUT** của cùng `(user, work_date)`, sắp theo `recorded_at` tăng dần,
bắt đầu từ **1** (R-79). Một ngày bấm `IN → OUT → IN → OUT` cho ra
`1 → 2 → 3 → 4`, **không** phải hai dãy `IN#1, OUT#1, IN#2, OUT#2`: mục đích của
trường này là đọc dòng thời gian ra/vào trong ngày, mà hai dãy song song thì
không nói được lượt nào xảy ra trước. Đây là **giá trị dẫn xuất, không phải cột**
trên `Attendance` (§7). `GET
/api/attendance/today` trả danh sách phiên trong ngày kèm tổng giờ công và cờ
`has_open_session`; client dùng cờ này để quyết định hiện nút Check In hay Check
Out, nhưng server vẫn là nơi quyết định cuối cùng.

Mọi response chứa tọa độ (`Attendance`, `AttendanceAttempt`, `TaskUpdate`) trả
kèm `maps_url` dạng `https://www.google.com/maps?q={lat},{lng}` và
`resolved_address` theo §6.2.1; `resolved_address` là `null` khi không khớp
`Location` nào.

`POST /api/tasks/` và `PATCH /api/tasks/{task_id}/` nhận `assignee_ids` (mảng id
Helpdesk). Phần tử trỏ tới user `is_active = False` làm cả request trả
`422 INACTIVE_ASSIGNEE` kèm danh sách id vi phạm — từ chối trọn gói, không tạo
task rồi im lặng bỏ bớt người (§6.1). Task đã giao từ trước cho người sau đó bị
khóa **không** bị đụng tới, nên `PATCH` chỉ kiểm các id **mới thêm** trong request
này, không kiểm lại toàn bộ assignee cũ; nếu không thì mọi lần sửa tiêu đề task
cũ đều vấp lỗi vì trong đó có một người đã nghỉ.

`POST /api/tasks/{task_id}/status` nhận `status` và `note`/`block_reason`; status
`BLOCKED` thiếu lý do trả `422 BLOCK_REASON_REQUIRED`. `POST
/api/tasks/{task_id}/evidence-uploads` nhận metadata của 1 ảnh (`mime`,
`size_bytes`, `checksum_sha256`), kiểm quyền/scope/Task chưa terminal và trả
`upload_id`, object key cùng presigned `PUT`. `POST
/api/tasks/{task_id}/complete-field` bắt 1-5 `upload_ids` +
`latitude`/`longitude`/`accuracy_m`, header `Idempotency-Key`, nhận tùy chọn
`selected_location_id`, cho
phép mọi `gps_quality`. GPS `GOOD` có nhiều ứng viên mà chưa gửi
`selected_location_id` trả `409 LOCATION_CHOICE_REQUIRED` kèm candidates và
không tạo `TaskUpdate`; client phải gửi lại để hoàn thành. `selected_location_id`
không nằm trong danh sách tính lại trả `422 INVALID_LOCATION_CHOICE`. Response
thành công luôn trả `gps_quality`,
`resolution_method` và `location_candidates` (mảng, rỗng khi không có ứng viên) —
đúng giá trị đã lưu trên `TaskUpdate`, không tính lại. `POST /api/tasks/{task_id}/complete-override` cho 0-5 ảnh,
không cần GPS, bắt `completion_note`; task đã hoàn thành trả
`409 TASK_ALREADY_COMPLETED` ở cả hai endpoint.

`GET /api/notifications/`, `PATCH /api/notifications/{id}/read`, `POST
/api/push-subscriptions/` và `DELETE /api/push-subscriptions/{id}/` chỉ thao tác
trên `request.user`; không nhận `user_id`. `GET /api/v1/operations/job-health` yêu
cầu `operations.job_health.view`, cho MANAGER/LEADER đọc health model §9;
response LEADER không chứa account/AuditLog link. HELPDESK nhận `403
PERMISSION_DENIED`. Không có endpoint rerun/repair job trong MVP.

Ba endpoint xác thực theo §9.2.1: `POST /api/v1/auth/login` nhận `username` +
`password`, trả JSON chỉ có `access` và trạng thái account/role; refresh token
được đặt trong cookie host-only `Secure; HttpOnly; SameSite=Strict`, không có
`Domain`, `Path=/api/v1/auth/` và không xuất hiện trong JSON; sai thông tin
đăng nhập hoặc `is_active = False` đều trả `401 INVALID_CREDENTIALS` với cùng một
thông báo, không phân biệt để tránh dò tài khoản. `POST /api/v1/auth/refresh` đọc
cookie, trả access mới, xoay cookie và blacklist token cũ; token hết hạn,
sai chữ ký hoặc đã bị blacklist đều trả `401 INVALID_TOKEN`. `POST
/api/v1/auth/logout` xác định actor bằng access token, luôn gọi helper thu hồi
**toàn bộ** refresh token đang mở của actor (không chỉ token gửi kèm), clear
cookie rồi trả `204` theo ma trận idempotent §9.2.2. Refresh cookie thiếu/sai/
hết hạn/đã blacklist/thuộc user khác không đổi kết quả logout; chỉ lần thực sự
thu hồi ít nhất một phiên mới ghi một AuditLog + một OutboxEvent và tăng version.
Access token đang cầm không bị blacklist. Request thiếu, sai hoặc hết hạn access
token trả `401 INVALID_TOKEN`; token còn hợp lệ nhưng user đã
bị `is_active = False` trả `401 ACCOUNT_INACTIVE` — hai mã khác nhau vì client xử
lý khác nhau: `INVALID_TOKEN` thì thử refresh, `ACCOUNT_INACTIVE` thì dừng hẳn và
báo tài khoản bị khóa (§9.2.1). `must_change_password = True` trả
`403 PASSWORD_CHANGE_REQUIRED` ở mọi endpoint trừ `/api/change-password/`. Thiếu
quyền vẫn là `403 PERMISSION_DENIED` — lỗi xác thực và lỗi phân quyền không dùng
chung mã.

**Endpoint quản trị người dùng (§8).** Hai nhánh tách hẳn nhau, không gộp
ViewSet: nhánh quản trị dưới `/api/users/` cần `user.view`/`user.manage`, nhánh
self chỉ cần đã đăng nhập và luôn tác động lên `request.user`.

| Method + path | Action | Ghi chú |
|---|---|---|
| `GET /api/v1/users/` | `user.view` | Lọc **tùy chọn** theo `q` (tên/username), `role`, `is_active`; phân trang theo số trang với tham số `page` (R-103); không truyền filter thì trả **cả user đang khóa**; **không** ẩn tài khoản `MANAGER` |
| `GET /api/v1/users/{id}/` | `user.view` | Trả cả target `MANAGER` |
| `POST /api/v1/users/` | `user.manage` | Tạo user; bắt buộc đúng **ba** trường `username`, `full_name`, `role` (§7), `role` phải thuộc `ASSIGNABLE_ROLES`; `phone`/`email` tùy chọn; **không** nhận `password`, server sinh và trả một lần; `must_change_password = True` (§9.2) |
| `PATCH /api/v1/users/{id}/` | `user.manage` | Sửa họ tên, số điện thoại, email; **không** nhận `role`, `password`, `is_active` |
| `PATCH /api/v1/users/{id}/role` | `user.assign_role` | Đổi vai trò, thân request đúng một trường `role` |
| `PATCH /api/v1/users/{id}/status` | `user.manage` | Khóa/mở khóa, thân request đúng một trường `is_active` |
| `POST /api/v1/users/{id}/reset-password` | `user.manage` | Thân request **rỗng**; server sinh mật khẩu và trả một lần, bật `must_change_password`, thu hồi toàn bộ refresh token (§9.2.1) |
| `GET`/`PATCH /api/v1/me/` | — | Thông tin cá nhân của chính actor; payload mang `user_id` trả `400 SERVER_OWNED_FIELD` |
| `POST /api/v1/change-password` | — | Tự đổi mật khẩu; thu hồi toàn bộ refresh token **rồi** cấp cặp token mới (§9.2.1); payload mang `user_id` trả `400 SERVER_OWNED_FIELD` |

**Endpoint self không bỏ qua `user_id`, nó từ chối (chốt, R-76).** Hai endpoint
`/api/me/` và `/api/change-password/` luôn tác động lên `request.user`; nếu
payload có trường `user_id`, server trả `400 SERVER_OWNED_FIELD` chứ **không**
âm thầm bỏ qua. Lý do: bỏ qua im lặng khiến một client gửi `user_id` của người
khác tin rằng nó vừa đổi mật khẩu cho người đó và nhận `200` — hệ thống trả lời
"thành công" cho một việc nó không làm. Từ chối thẳng biến nhầm lẫn đó thành lỗi
đọc được ngay ở lần chạy đầu. Đây cũng chính là luật §8.3 áp cho nhánh self,
không phải ngoại lệ mới: `user_id` là dữ liệu server-owned, và mọi trường
server-owned có mặt trong input đều `400`.

Sửa hồ sơ, đổi vai trò, khóa/mở khóa và reset mật khẩu tách thành bốn endpoint
riêng thay vì dồn vào một `PATCH` chung
để mỗi endpoint kiểm đúng một action và không có trường nhạy cảm nào đi lẫn trong
payload sửa hồ sơ. `PATCH /api/users/{id}/` nhận `role`, `password` hay
`is_active` trả `400 SERVER_OWNED_FIELD` — cùng mã đã dùng cho payload lấn quyền
server ở Attendance, vì bản chất giống nhau: client gửi trường không thuộc quyền
nó ở endpoint đó.

Hai luật của §8 có **phạm vi khác nhau**, đừng gộp làm một guard:

| Luật | Áp cho | Vi phạm trả |
|---|---|---|
| `target.role = MANAGER` | đúng **bốn** endpoint ghi có target: `PATCH .../`, `PATCH .../role`, `PATCH .../status`, `POST .../reset-password` | `403 PERMISSION_DENIED`, kể cả khi `target == actor` |
| `role` trong payload ngoài `ASSIGNABLE_ROLES` | đúng hai endpoint nhận `role`: `POST /api/users/`, `PATCH .../role` | `403 PERMISSION_DENIED` |
| có mặt `role`/`password`/`is_active` trong payload | `PATCH /api/users/{id}/` (sửa hồ sơ) | `400 SERVER_OWNED_FIELD`, bất kể giá trị |

Cả hai mã `403` đều không phải `422` (§8). `GET` không đi qua guard nào. Luật
`target.role = MANAGER` áp cho **bốn** chứ không phải năm endpoint vì
`POST /api/users/` **không có target** — nó tạo user mới, nên chỗ chặn tương ứng
là luật `role` trong payload ở dòng kế tiếp (R-75).

Khi một request phạm nhiều luật cùng lúc, thứ tự trả về theo đúng pipeline §8:
**action → role của target → payload**. Cụ thể, `PATCH /api/users/{id}/` lên một
target đang là `MANAGER` mà payload có kèm `role` trả `403 PERMISSION_DENIED`
(chặn ở bước target), **không** phải `400 SERVER_OWNED_FIELD` — kiểm quyền luôn
chạy trước kiểm trường, để thông tin về hình dạng payload không rò ra cho actor
không đủ quyền. Test phải khẳng định đúng mã này, đừng để hai người viết hai kỳ
vọng ngược nhau.

**`POST /api/users/` thiếu `role` là lỗi, không có mặc định (chốt).** `role` khai
báo `required=True` ở serializer, thiếu thì DRF trả `400` với lỗi theo trường
(`{"role": ["This field is required."]}`). **Không** âm thầm mặc định `HELPDESK`:
tạo nhầm vai trò rồi mới phát hiện thì đã có người đăng nhập được vào chỗ không
định cho họ vào. Cũng **không** đặt mã riêng kiểu `ROLE_REQUIRED` — `role` là
trường bắt buộc vô điều kiện, giống `username` hay `full_name`, nên nó thuộc về
lỗi validate mặc định của DRF. Mã riêng chỉ dành cho ràng buộc **có điều kiện**,
nơi lỗi theo trường không nói được vì sao trường đó đột nhiên bắt buộc — ví dụ
`422 BLOCK_REASON_REQUIRED` (chỉ bắt buộc khi `status = BLOCKED`). Đặt mã riêng
cho mọi trường bắt buộc là mở đầu cho `USERNAME_REQUIRED`, `FULL_NAME_REQUIRED`…
và một bảng mã lỗi lặp lại nguyên bộ serializer.

Endpoint self không nhận `user_id`/`username` trong payload; có gửi thì trả
`400 SERVER_OWNED_FIELD` (R-76, luật đã nêu ngay dưới bảng trên). Nhờ vậy Manager
vẫn tự đổi được mật khẩu và thông tin cá nhân của mình dù mọi thao tác quản trị
lên `MANAGER` bị chặn. `username` là bất biến sau khi tạo: không endpoint nào đổi
được, kể cả `PATCH /api/me/`.

Hai endpoint `GET` chỉ mở cho `MANAGER`: `LEADER` và `HELPDESK` gọi đều trả
`403 PERMISSION_DENIED` (§8). Riêng picker chọn người nhận việc dùng
`GET /api/users/?is_active=true` (thêm `&role=HELPDESK` nếu muốn thu hẹp) — cùng
endpoint, cùng action `user.view`, không mở view thứ hai không kiểm quyền chỉ để
lấy danh sách tên (§6.1). **Không có endpoint picker riêng (chốt, R-81):** chỉ
tồn tại một `GET /api/users/` với query tùy chọn, và khi không truyền filter thì
nó trả cả user đang khóa — vì đây cũng là endpoint của màn quản trị người dùng,
nơi Manager phải nhìn thấy tài khoản đã khóa để mở lại. Lọc `is_active` ở màn
giao việc vì thế là trách nhiệm của **client**, không phải filter cứng ở server;
server vẫn chặn hậu kiểm bằng `422 INACTIVE_ASSIGNEE` nếu client gửi nhầm id đã
khóa, nên bỏ sót filter ở UI là lỗi hiển thị chứ không phải lỗ hổng dữ liệu.

**Endpoint quản trị cấu hình và xuất báo cáo (chốt, R-83).** Các endpoint dưới
đây trước nay chỉ được nhắc gián tiếp qua tên action; khai báo tại đây để §8 và
§10 khớp một-một, không còn action nào không có endpoint và không endpoint nào
không có action.

| Method + path | Action | Ghi chú |
|---|---|---|
| `GET /api/v1/locations/` | `location.view` | Cả ba vai trò; lọc tùy chọn theo `kind`, `parent`, `is_active` |
| `PATCH /api/v1/locations/{id}/` | `location.manage` | Sửa tên/địa chỉ/tọa độ/`radius_m`/`is_active`; **không** đổi `code`; bắt `version`, tính lại overlap trong transaction, stale trả `409 LOCATION_VERSION_CONFLICT`; same-value candidate là no-op `200` theo R-115 |
| `GET /api/v1/config/` | `config.view` | Cả ba vai trò — client cần đọc ngưỡng để dựng UI (§8) |
| `PATCH /api/v1/config/` | `config.manage_attendance` | Sửa singleton `pk=1`; cùng URL với `GET` nhưng khác action, kiểm theo method; hạ `max_radius_m` dưới bất kỳ Location hiện hữu nào bị từ chối theo R-114; same-value candidate là no-op `200` theo R-115 |
| `GET /api/v1/holidays/` | `holiday.manage` | Chỉ `MANAGER`; job cuối ngày **không** đọc bảng này (§5.3, R-82) |
| `POST /api/v1/holidays/` | `holiday.manage` | Thêm ngày nghỉ; `date` là `UNIQUE`, trùng trả `400` |
| `DELETE /api/v1/holidays/{id}/` | `holiday.manage` | Xóa ngày nghỉ |
| `GET /api/v1/reports/attendance/export/` | `report.export` | Xuất bảng công (§9.3); `LEADER` và `MANAGER` |
| `GET /api/v1/reports/tasks/export/` | `report.export` | Xuất báo cáo task (§9.3); `LEADER` và `MANAGER` |

Mọi thao tác ghi ghi `AuditLog` kèm actor, target, action và giá trị cũ/mới;
riêng reset mật khẩu **không** ghi mật khẩu vào `AuditLog`. `username` là bất
biến sau khi tạo: đổi `username` không nằm trong MVP, muốn thêm thì mở endpoint
riêng để không lẫn vào `PATCH` hồ sơ.

**PATCH không đổi state (chốt, R-115).** Với Location hoặc Config, payload phải
có ít nhất một field mutable; `reason` riêng lẻ không đủ. Sau khi khóa và dựng
complete candidate, nếu mọi field mutable bằng state hiện tại thì response vẫn
`200` và trả resource/warnings hiện hành, nhưng không gọi save, không tăng
Location version, không tạo AuditLog/OutboxEvent và không tăng aggregate version.
Đây là idempotent no-op, không phải một mutation có bằng chứng. Với Location,
version được so trước khi xét no-op: version stale luôn `409` và không được hợp
thức hóa chỉ vì candidate trùng state mới.

**ID route sai hình dạng (chốt, R-116).** Mọi route Feature 003 dùng string
converter để authentication, action RBAC và account gate chạy trước parse id.
Sau khi qua các gate đó, id Location/Holiday không parse thành số nguyên dương và
id hợp lệ nhưng không tồn tại đều trả cùng `404 NOT_FOUND`; không để lộ target,
không mutation/audit/outbox. Quy tắc này áp nhất quán cho `PATCH Location` và
`DELETE Holiday`.

### 10.1 Hợp đồng API có phiên bản và client sinh tự động (chốt, R-103)

**Namespace canonical là `/api/v1/`.** Mọi route REST JSON của MVP nằm dưới
`/api/v1/`; tiền tố khai báo đúng một chỗ ở `backend/config/urls.py`. Hai bảng
endpoint ở trên đã viết đủ tiền tố. Những chỗ còn viết tắt `/api/...` trong phần
văn xuôi của tài liệu này là cách viết có từ trước R-103 và **chỉ ra đúng cùng
route** dưới `/api/v1/` — không tồn tại route nào ngoài `/api/v1/`. Thay đổi phá
vỡ hợp đồng mở namespace major mới (`/api/v2/`), không sửa tại chỗ trong v1.

**Thân lỗi canonical là `{error_code, message, details, request_id}`.**
`error_code` là mã lỗi ở §9.2.1 và §10 (ví dụ `INVALID_CREDENTIALS`,
`PERMISSION_DENIED`, `SERVER_OWNED_FIELD`, `VALIDATION_FAILED`); `message` là câu
tiếng Việt hiển thị được; `details` là `{tên_trường: [thông báo]}` cho lỗi theo
trường và `{}` khi không có; `request_id` là id server sinh cho request đó, trả
kèm ở header `X-Request-Id` để đối chiếu log. Server **không** tin `X-Request-Id`
do client gửi lên.

Chuyển đổi theo lối expand–migrate–contract, **không** đổi gãy: suốt vòng đời v1
thân lỗi vẫn mang thêm hai thứ đã ship và nay là **mirror deprecated** —
trường `error` (bằng đúng `error_code`) và các khóa lỗi theo trường nằm ở
**cấp cao nhất** (`{"username": [...]}`) song song với bản sao trong `details`.
Lý do: khi triển khai bản mới, bundle frontend của lần triển khai trước vẫn đang
chạy và vẫn đọc `error`; bỏ ngay hai mirror này sẽ làm bản cũ mất thông báo lỗi
giữa chừng. Bước gỡ mirror là pha *contract*, chỉ làm khi mọi client đã triển
khai đều đọc `error_code`. Ví dụ `POST /api/v1/users/` với `username` trùng:

```json
{
  "error_code": "VALIDATION_FAILED",
  "message": "Dữ liệu không hợp lệ.",
  "details": {"username": ["Tên đăng nhập đã tồn tại."]},
  "request_id": "7c1f0f0a-2c1e-4a1e-9d0f-6b2f0f5a1c3d",
  "error": "VALIDATION_FAILED",
  "username": ["Tên đăng nhập đã tồn tại."]
}
```

Thứ tự mã lỗi ở §8 và §9.2.1 **không** đổi: `403 PERMISSION_DENIED` /
`403 PASSWORD_CHANGE_REQUIRED` / `401 ACCOUNT_INACTIVE` vẫn chạy trước
`400 SERVER_OWNED_FIELD`. Envelope chỉ đổi *hình dạng thân*, không đổi mã lẫn
HTTP status của bất kỳ nhánh nào.

**Phân trang theo số trang, chỉ cho danh bạ người dùng.** `GET /api/v1/users/`
nhận `page` và trả `{count, next, previous, results}` — bộ sưu tập quản trị nhỏ,
đọc theo trang là đủ. **Không** khai báo `page_size`, **không** cursor pagination,
và **không** khai báo trước hợp đồng phân trang cho module chưa tồn tại; log ghi
nối đuôi (Attendance, TaskUpdate) sẽ chốt cursor pagination ở story của chính nó.
`page` ngoài phạm vi trả `400` với `details.page`, không phải `404` (§10).

**Wire field giữ nguyên `snake_case` ở cả hai đầu.** Không có lớp ánh xạ
camelCase nào ở MVP (QUY_TAC §1). `capabilities` và trường `role` của endpoint
đổi vai trò khai báo là chuỗi mở, **không** phải enum trong schema: enum sẽ khóa
cứng danh sách action/vai trò vào hợp đồng và làm mọi bổ sung sau này thành
breaking change.

**Artifact hợp đồng được commit và gác ở CI.** `contracts/openapi.yaml` (schema
OpenAPI sinh từ backend) và `frontend/src/shared/api/schema.ts` (client
TypeScript sinh từ schema đó) là **artifact sinh tự động, được commit vào repo**.
CI bắt buộc kiểm ba thứ: sinh lại schema phải trùng byte với bản đã commit; sinh
lại client phải trùng với bản đã commit; và so schema mới với schema ở merge-base
phải không có thay đổi phá vỡ (xóa path/operation/trường response, đổi kiểu, hay
thêm trường bắt buộc vào request). Thay đổi kiểu cộng thêm–tùy chọn thì hợp lệ.
Schema **không** chứa token, mật khẩu, cookie, tọa độ hay presigned URL — kể cả
trong example (§9, AD-11). Route đọc schema (`GET /api/v1/schema/`) chỉ được đăng
ký khi bật cờ `API_DOCS_ENABLED`; mặc định nó **không có trong URLconf**, gọi vào
trả `404`, và không có giao diện HTML kiểu Swagger/ReDoc.

- Seed tạo đúng 76 `Location`; `HCM020129.parent_id` trỏ `HCM020000`;
  `HCM000079.parent_id IS NULL`; 7 dòng TTKD có `parent_id IS NULL`; chạy seed
  hai lần không đổi số dòng.
- GPS trong đúng một Location: Check In/Out thành công, `AUTO_SINGLE`.
- GPS trong hai Location cùng/trùng địa chỉ: API yêu cầu chọn; lựa chọn không nằm
  trong các ứng viên `INSIDE_GEOFENCE` bị từ chối `422 INVALID_LOCATION_CHOICE`
  và ghi `AttendanceAttempt(outcome=INVALID_LOCATION_CHOICE)` — tách bạch với
  `LOCATION_CHOICE_REQUIRED` của lần chưa chọn.
- Request có `selected_location_id` nhưng tập candidates tính lại rỗng trả
  `422 OUTSIDE_RADIUS`; chỉ tập không rỗng mới được xét
  `INVALID_LOCATION_CHOICE` (§5.1, R-122).
- Hai cổng độc lập (§4.2): `a <= t` và `d <= r` mới `INSIDE_GEOFENCE`. Test phải
  có case `d = 40`, `a = 20`, `r = 50`, `t = 25` → **thành công** (công thức cũ
  `d + a <= r` sẽ trượt case này), và case `d = 60`, `a = 5`, `r = 50` →
  `OUTSIDE_GEOFENCE`.
- `LocationValidationResult` chỉ có hai giá trị; không tồn tại `UNCERTAIN` trong
  enum, DB hay response.
- `accuracy_m > Config.max_attendance_accuracy_m`: không tạo Attendance, trả
  `422 WEAK_GPS`, và ghi `AttendanceAttempt(outcome=WEAK_GPS)`.
- Mỗi nhánh từ chối ở §5.1 ghi đúng một `AttendanceAttempt` với `outcome` tương
  ứng và `attendance = NULL`; lần thành công ghi `outcome = ACCEPTED` trỏ tới
  `Attendance` vừa tạo. Test phải khẳng định request **thành công cũng sinh
  attempt** — không chỉ log lần bị từ chối.
- Ép writer AttendanceAttempt hậu-transaction lỗi phải giữ nguyên
  response/exception nghiệp vụ gốc, không retry, không rollback state đã commit;
  telemetry lỗi không chứa tọa độ/device/IP (R-120).
- Ranh giới ngược lại cũng có test: request không token, token hỏng, actor
  `MANAGER`, actor còn `must_change_password = True`, hoặc payload mang `kind`
  đều **không** thêm dòng `AttendanceAttempt` nào (§5.1). Đếm số dòng trước và
  sau request, không chỉ kiểm mã lỗi.
- Không có ứng viên nào: mã lỗi trả về là `OUTSIDE_RADIUS`, không phải
  `OUTSIDE_GEOFENCE`; chuỗi `OUTSIDE_GEOFENCE` chỉ xuất hiện như giá trị
  `validation_result`, không xuất hiện ở trường mã lỗi của bất kỳ response nào.
- Payload Check In/Out chứa `kind` bị trả `400 SERVER_OWNED_FIELD`; `kind` lưu
  trong DB luôn khớp route đã gọi.
- Check In/Out ở bất kỳ `Location` đang hoạt động nào cũng thành công và **không**
  sinh anomaly nào vì lý do "khác nơi phân công": `AttendanceAnomalyReason` chỉ
  còn **bốn** giá trị và không có `OFF_ASSIGNMENT` (§5.2, R-73). Test phải khẳng
  định `len(AttendanceAnomalyReason.choices) == 4` và chuỗi `OFF_ASSIGNMENT`
  không xuất hiện ở enum, migration hay response nào.
- Check Out muộn quá `late_checkout_grace_minutes`: thành công và tạo
  `LATE_CHECK_OUT`.
- Một ngày bấm `IN → OUT → IN → OUT`: cả bốn lượt thành công, tạo đúng **hai**
  `AttendanceSession`, giờ công bằng **tổng** hai phiên chứ không phải hiệu giữa
  lượt đầu và lượt cuối.
- Duration dùng một fixture có microsecond không biểu diễn hữu hạn theo phút và
  khẳng định lượng tử hóa đúng 6 chữ số bằng `ROUND_HALF_UP` (R-123).
- Check In tại Location A, rời geofence để di chuyển và hoàn thành Task ngoài 76
  Location, rồi Check Out tại Location B: phiên vẫn mở suốt khoảng đó, không có
  auto-close khi rời A; Check Out thành công nếu qua policy tại B;
  `check_in_location_id = A`, `check_out_location_id = B`, và duration bằng đúng
  `check_out.recorded_at - check_in.recorded_at` không trừ thời gian ngoài geofence.
- Không có polling/background job nào đọc vị trí thiết bị để đóng phiên hoặc cập
  nhật duration trong lúc phiên mở; test service không tạo side effect khi chỉ có
  Task GPS ngoài known Location.
- Check In khi đang có phiên mở trả `409 SESSION_ALREADY_OPEN`; Check Out khi
  không có phiên mở trả `409 NO_OPEN_SESSION`; cả hai ghi `AttendanceAttempt` với
  `outcome` tương ứng và không tạo `Attendance`.
- Không tồn tại `UNIQUE(user_id, work_date, kind)` trong migration; test phải
  khẳng định lượt Check In thứ hai trong ngày **không** bị lỗi unique.
- Ngày nhiều lượt: `LATE_CHECK_IN` chỉ gắn vào lượt Check In đầu tiên,
  `EARLY_CHECK_OUT`/`LATE_CHECK_OUT` chỉ gắn vào lượt Check Out cuối cùng; lượt
  giữa ngày không sinh anomaly. Bấm thêm một cặp `IN/OUT` sau đó phải gỡ anomaly
  ra ca đã gắn ở lượt trước (§5.3).
- Lượt Check In thứ hai trong ngày ở vị trí ngoài mọi bán kính vẫn bị từ chối
  `OUTSIDE_RADIUS` — luật vị trí áp dụng cho mọi lượt, không chỉ lượt đầu.
- Job cuối ngày đóng phiên còn mở: tạo `MISSING_CHECK_OUT`, giữ `check_out` và
  `duration_minutes` = `NULL`, đặt `closed_by_job = True`, phiên không cộng vào
  tổng giờ; sau job, Check In hôm sau thành công.
- Sau khi job chạy, phiên `closed_by_job = True` **không** bị partial unique index
  coi là phiên mở: test tạo phiên bị job đóng rồi Check In lần nữa phải thành công
  (không dính `IntegrityError`, không trả `409 SESSION_ALREADY_OPEN`), và
  `has_open_session` ở `GET /api/attendance/today` trả `false`.
- Job `MISSING_CHECK_OUT` **chạy mọi ngày**, kể cả Chủ nhật và ngày có `Holiday`
  (§5.3, R-82). Test bắt buộc: tạo một phiên mở vào ngày làm việc, cho job chạy
  vào ngày nghỉ kế tiếp, phiên đó **phải** bị đóng — bản cũ bỏ qua ngày nghỉ nên
  phiên treo qua cả kỳ nghỉ và user dính `409 SESSION_ALREADY_OPEN` vĩnh viễn.
- Phiên mở có `work_date` **rơi vào Chủ nhật hoặc ngày có `Holiday`** vẫn nhận
  `AttendanceAnomaly(MISSING_CHECK_OUT)` khi job chạy (§9.3, R-85). Test bắt
  buộc kiểm cả hai vế: phiên bị đóng (`closed_by_job = True`) **và** anomaly
  được ghi. Sau mọi lần job chạy, số phiên `closed_by_job = True` bằng đúng số
  anomaly `MISSING_CHECK_OUT` — không có nhánh nào đóng phiên mà bỏ anomaly.
- `maps_url` dựng từ tọa độ đã lưu của bản ghi (không phải tọa độ `Location`) và
  khớp đúng định dạng `https://www.google.com/maps?q={lat},{lng}`.
- `resolved_address` bằng tên + địa chỉ Location khi có `location`; bằng `null`
  khi `location IS NULL`. Không có lời gọi HTTP ra dịch vụ geocoding nào trong
  toàn bộ luồng — test khẳng định bằng cách chặn network/mock client.
- Ảnh thiếu EXIF GPS: không có ảnh hưởng đến luồng nào.
- Hoàn thành hiện trường GPS `LOW_ACCURACY`/`UNRELIABLE`: cảnh báo, vẫn hoàn
  thành; lưu `accuracy_m`, `gps_quality`, `resolution_method = GPS_ONLY`, không tự
  gán Location.
- `complete-field` với hai ứng viên và không có `selected_location_id`: trả `409
  LOCATION_CHOICE_REQUIRED`, không tạo `TaskUpdate` và trả đủ hai candidate. Gửi
  lại với lựa chọn hợp lệ trả `201`, lưu `location`, `USER_SELECTED` và toàn bộ
  `location_candidates` để audit.
- Hiển thị/báo cáo cho `location IS NULL` xét `gps_quality` trước (§6.2.1):
  `gps_quality != GOOD` hiện “GPS không đủ tin cậy để đối chiếu địa điểm”; trong
  nhánh `GOOD`, mảng rỗng hiện “Ngoài mọi địa điểm đã đăng ký”. Không tồn tại
  TaskUpdate đã commit có GPS `GOOD`, nhiều candidates nhưng chưa chọn.
- Sau khi tạo `TaskUpdate`, đổi `Location.radius_m` hoặc tắt `is_active` không làm
  đổi `location_candidates` của bản ghi cũ — mảng là dữ liệu lịch sử, không tính lại.
- `complete-field` với `selected_location_id` ngoài danh sách ứng viên trả
  `422 INVALID_LOCATION_CHOICE`.
- `complete-field` thiếu ảnh hoặc quá 5 ảnh bị từ chối; `complete-override` với
  0 ảnh được chấp nhận.
- Upload staging test đủ: cross-user/cross-Task `upload_id` bị từ chối; object
  hết hạn/đã bind/checksum sai/MIME sai/size quá 5 MB không finalize; 3/4 ảnh đã
  upload không phải gửi lại khi ảnh 4 lỗi; retry cùng `Idempotency-Key` không tạo
  TaskUpdate thứ hai; key cũ với payload khác trả conflict; cleanup không xóa
  object đã bind.
- `LOCATION_CHOICE_REQUIRED`/`INVALID_LOCATION_CHOICE` không consume
  Idempotency-Key: gửi lại cùng key với `selected_location_id` hợp lệ phải hoàn
  thành. Sau khi transaction đã bind key, payload khác mới trả conflict.
- Các outcome `SESSION_ALREADY_OPEN`, `NO_OPEN_SESSION`, `WEAK_GPS` sau boundary
  đều có nearest metadata; test spy khẳng định phép tính quan trắc không gọi
  geofence business gate sớm và WEAK_GPS response/report gắn nhãn approximate.
- Client GPS watch dừng khi tab hidden/rời màn/timeout/submit; không submit sample
  quá 60 giây, không auto Check In/Out và không ghi chuỗi fix vào storage.
- Draft local test namespace theo account, xóa khi logout/account switch/finalize,
  hết hạn 7 ngày, không chứa GPS/token/presigned URL và không báo lưu thành công
  khi IndexedDB quota/storage unavailable.
- Notification test đủ recipient/dedupe/quiet-hours/TTL/suppression: người hoàn
  thành không nhận event “người khác hoàn thành”; Check Out hủy reminder còn mở;
  logout/khóa account vô hiệu hóa push subscription; deep-link kiểm lại RBAC.
- Job-health response đối chiếu `scanned/closed/anomaly`, phát hiện invariant
  mismatch và stale run; cutoff equality là late; trước cutoff chỉ prior-day
  RUNNING là stale, từ cutoff mọi RUNNING chưa terminal alert. Identity trả typed
  access scope và LEADER không nhận account/AuditLog link.
- Deployment test kiểm `deploy/scheduled-jobs.yaml` có đúng `15 0 * * *`, timezone
  Asia/Ho_Chi_Minh, management command canonical, một binding/môi trường và enabled
  ở staging/production; lịch không có nhánh bỏ weekend/Holiday (R-133).
- Usability job-health trước release dùng ít nhất 10 MANAGER/LEADER đại diện;
  100% xác định đúng state và một reason active khi có trong dưới 30 giây; với
  `ok` không có reason active phải xác định đúng là không có cảnh báo. Evidence chỉ
  giữ số liệu/role tổng hợp, timing và pass/fail, không username/GPS (R-134).
- `PATCH Location` với version cũ trả conflict; overlap được tính lại trong
  transaction lưu và AuditLog giữ before/after/reason.
- `PATCH Location` current-version và `PATCH Config` có field nhưng candidate
  không đổi trả `200` no-op: không save/audit/outbox/version; Location stale vẫn
  `409` dù candidate bằng state hiện tại (R-115).
- Hạ `Config.max_radius_m` bằng bán kính Location lớn nhất thì thành công; thấp
  hơn bán kính của Location active **hoặc inactive** thì `400`, toàn bộ
  Config/Location/AuditLog/OutboxEvent/version không đổi. Race Config-lowering
  với Location update và hai Location update khác nhau phải dùng PostgreSQL thật,
  hai connection/barrier và chứng minh thứ tự khóa Config → Location (R-114).
- Location `name`/`address` rỗng, `is_active = NULL` và mọi constraint/default
  Location phải có test PostgreSQL; không dùng SQLite/mock làm bằng chứng.
- `PATCH Location`/`DELETE Holiday` với id sai hình dạng: actor thiếu quyền vẫn
  `403`; actor đủ quyền nhận `404 NOT_FOUND`, giống id hợp lệ không tồn tại, và
  không có side effect (R-116).
- Mọi response Feature 003, cả success/error/conflict, có `Cache-Control:
  private, no-store`; error `request_id` khớp `X-Request-Id`.
- Gate readiness fail nếu Config thiếu/không hợp lệ hoặc Location không đúng
  76/7/69/source/hierarchy; pass chỉ sau initialization + seed canonical và
  tuyệt đối không tự sửa state (R-117).
- Failure-rate response luôn có numerator/denominator/excluded/observed/nearest
  coverage; denominator 0 trả `rate = NULL`/`N/A`, không `0%`.
- Export mặc định không có tọa độ/Maps/photo/presigned URL; opt-in MANAGER/LEADER
  có tọa độ, ghi AuditLog metadata nhưng không ghi chính tọa độ và response
  `Cache-Control: no-store`.
- `BLOCKED` thiếu lý do bị từ chối; chuyển `BLOCKED -> IN_PROGRESS -> COMPLETED`
  không tạo task mới.
- Hai request Check In cùng lúc: partial unique index chỉ cho một phiên mở, request
  thua nhận `409 SESSION_ALREADY_OPEN`; hai request complete cùng lúc: chỉ một
  request thắng và có một `TaskUpdate COMPLETED`.
- Hai request Check Out cùng lúc trên một phiên mở: đúng một request tạo OUT và
  đóng phiên, request còn lại nhận `409 NO_OPEN_SESSION`; cả hai giữ attempt khi
  persistence quan trắc hoạt động.
- Lỗi hạ tầng bất ngờ sau boundary: trả 5xx canonical, không ghi attempt, không
  relabel thành một trong bảy outcome và telemetry không chứa GPS/device/IP
  (R-125).
- Check In/Out thành công tạo đúng một AuditLog action tương ứng trong cùng
  transaction, payload đã lọc và không outbox; mọi nhánh từ chối không tạo
  AuditLog/OutboxEvent (R-121).
- Acceptance latency Feature 004 chạy 100 chu kỳ command + today-read trên
  PostgreSQL với 50 user, đúng 76 Location và actor có 20 session cùng ngày; ít
  nhất 95 chu kỳ không quá 2 giây; đây là acceptance trước phát hành có evidence,
  **không phải cổng CI** hay wall-clock assertion trong test suite. Usability dùng ít nhất 20 HELPDESK đại diện,
  ít nhất 19 người hoàn thành cả punch không mơ hồ và bước chọn Location mà không
  cần trợ giúp; evidence không lưu GPS (R-124).
- `recorded_at` ở ranh giới ngày UTC phải cho đúng `work_date` Asia/Ho_Chi_Minh;
  thay đổi `captured_at` không làm đổi late/early/work_date.
- Phiên mở lúc gần nửa đêm không kéo sang `work_date` hôm sau: `work_date` của
  phiên luôn bằng `work_date` của Check In (§5.3).
- Attendance lưu `device_metadata`; chỉ dùng audit/risk signal, không chống gian lận.
- Hoàn thành manager override: chỉ Manager được phép, thiếu ghi chú bị từ chối,
  có `AuditLog`.
- Task tương lai vào `UPCOMING` và không tăng KPI hôm nay.
- `TaskAssignee` không có cột `status`: task hai assignee, một người hoàn thành
  thì `Task.status = COMPLETED` cho cả hai; báo cáo đếm “Việc được giao đã đóng”
  = 2 và “Việc tự tay hoàn thành” = 1 cho người bấm, 0 cho người kia.
- Mọi action RBAC có test allow/deny ở backend.
- `LEADER` bị `403` trên mọi mutation, gồm cả `task.create.assign` và
  `task.update.any`.
- Đúng năm implication trong `PERMISSION_IMPLIES` (§8.1) được kiểm bằng test, gồm
  `photo.view.all -> photo.view.self`; action không nằm trong map không được tự
  kế thừa, và test phải khẳng định `len(PERMISSION_IMPLIES) == 5`.
- Helpdesk dùng URL `task_id` của task ngoài scope bị `403`/`404` theo policy;
  anonymous request bị chặn trước object query.
- `POST /api/users/` và `PATCH /api/users/{id}/role` với `role = MANAGER` đều trả
  `403 PERMISSION_DENIED`; sau request không có thêm user `MANAGER` nào trong DB.
- Với target đang là `MANAGER`, cả bốn endpoint ghi (`PATCH .../`,
  `PATCH .../role`, `PATCH .../status`, `POST .../reset-password`) trả
  `403 PERMISSION_DENIED`, kể cả khi actor thao tác lên chính mình; nhưng
  `GET /api/users/` và `GET /api/users/{id}/` vẫn trả tài khoản đó với `200`.
- `PATCH /api/users/{id}/` mang `role`, `password` hoặc `is_active` trả
  `400 SERVER_OWNED_FIELD`, kể cả khi `role = HELPDESK` là giá trị hợp lệ — lỗi
  do trường có mặt, không do giá trị.
- `PATCH /api/users/{id}/` lên target `MANAGER` mà payload có `role` trả
  `403 PERMISSION_DENIED` chứ không `400 SERVER_OWNED_FIELD` (thứ tự §8, R-87):
  luật target đứng trong cổng phân quyền nên chạy trước DTO validation. Test
  cùng bộ: gửi body **rỗng** lên target `MANAGER` cũng trả `403`, chứng minh kết
  quả không phụ thuộc nội dung body.
- `POST /api/users/` thiếu `role` trả `400` với lỗi theo trường
  `{"role": ["This field is required."]}`; sau request không có user nào được
  tạo, đặc biệt không có user `HELPDESK` mặc định.
- Manager gọi `POST /api/change-password/` và `PATCH /api/me/` thành công dù mọi
  thao tác quản trị lên `MANAGER` bị chặn; hai endpoint này bỏ qua `user_id` gửi
  kèm payload và trả `400 SERVER_OWNED_FIELD`.
- `MANAGER` gọi `POST /api/attendance/check-in` và `/check-out` trả
  `403 PERMISSION_DENIED`, không tạo `Attendance` lẫn `AttendanceAttempt` (§5).
- `LEADER` và `HELPDESK` gọi `GET /api/users/` và `GET /api/users/{id}/` đều trả
  `403 PERMISSION_DENIED` (§8).
- `POST /api/users/` và `POST /api/users/{id}/reset-password` trả mật khẩu sinh
  ra đúng một lần trong response; hai lần gọi liên tiếp sinh hai chuỗi khác nhau;
  `GET` lại user không có trường mật khẩu; `AuditLog` của hai thao tác này không
  chứa chuỗi đó. Gửi kèm `password` trong payload trả `400 SERVER_OWNED_FIELD`.
- Mật khẩu server sinh đăng nhập được **nhiều lần** (đăng nhập, bỏ đó, đăng nhập
  lại vẫn `200`) — nó không phải OTP; cái chặn là cờ: mọi endpoint nghiệp vụ trả
  `403 PASSWORD_CHANGE_REQUIRED` cho tới khi đổi, riêng `/api/change-password/`
  gọi được. Sau khi đổi, mật khẩu cũ mới hết hiệu lực (§9.2).
- `POST /api/tasks/` với `assignee_ids` chứa user `is_active = False` trả
  `422 INACTIVE_ASSIGNEE`; sau request không có `Task` lẫn `TaskAssignee` nào được
  tạo (§6.1).
- Khóa một Helpdesk đang có task `TODO`/`IN_PROGRESS`: số dòng `TaskAssignee` và
  `Task.status` không đổi, task vẫn hiện ở nhóm Quá hạn, và báo cáo tháng trước
  của user đó giữ nguyên số liệu.
- Task quá hạn **không** bị ghi đè ngày (§6.1, R-86): tạo task
  `assigned_date = today - 3`, để qua ngày, đọc lại thì `assigned_date` vẫn là
  giá trị cũ, task nằm ở nhóm Quá hạn và response mang nhãn trễ `3` ngày tính
  tại thời điểm đọc. Test khẳng định không có job/endpoint nào `UPDATE`
  `assigned_date`, và báo cáo của ngày `today - 3` vẫn đếm task đó.
- `GET /api/users/?role=HELPDESK&is_active=true` không trả user đã khóa, trong khi
  `GET /api/users/` không lọc vẫn trả đủ.
- `latitude`/`longitude`/`accuracy_m` invalid bị từ chối trước Haversine.
- Concurrency Attendance/Task chạy integration test với PostgreSQL thật,
  `TransactionTestCase` hoặc tương đương; SQLite/mock không đủ bằng chứng.
- Transition matrix test đủ mọi transition hợp lệ, mọi transition từ `COMPLETED`
  bị từ chối, và kết hợp permission + object scope.
- Access token hết hạn (quá 15 phút) bị `401`; dùng refresh token lấy được cặp
  token mới; refresh token **đã xoay vòng** dùng lại bị từ chối, không cấp token
  mới.
- Sau `POST /api/v1/auth/logout`, refresh token bị blacklist: gọi lại
  `/api/v1/auth/refresh` với cookie đó trả `401`.
- Logout với access hợp lệ và lần lượt cookie thiếu, sai, hết hạn, thuộc user
  khác, đã blacklist, đang active đều trả `204`, clear cookie và gọi revoke theo
  actor. Có active session thì đúng một audit+outbox; gọi lặp khi count = 0 không
  thêm evidence/version.
- `PATCH .../status` với giá trị đang có trả `200` nhưng số User write,
  AuditLog, OutboxEvent và version đều không đổi. Reset hai lần vẫn sinh hai mật
  khẩu khác nhau và hai reset evidence; lần thứ hai chỉ có revocation evidence
  nếu lại có active refresh.
- Clock-controlled throttle test: request thứ 11 login/IP, 121 refresh/IP và 6
  password-change/User trong 60 giây trả `429 THROTTLED` + `Retry-After`; key
  khác còn quota, hai worker dùng chung counter; cache hỏng trả
  `503 SERVICE_UNAVAILABLE`, không mutation/audit/outbox.
- Manager reset mật khẩu, user tự đổi mật khẩu, hoặc đặt `is_active = False`: mọi
  refresh token đang mở của user đó bị blacklist và có `AuditLog`; refresh sau đó
  đều `401`.
- User bị `is_active = False` nhưng access token còn hạn: request tiếp theo trả
  đúng `401 ACCOUNT_INACTIVE` (không phải `INVALID_TOKEN`, không phải `403`) —
  test khẳng định server kiểm `is_active` sau khi giải mã token, không tin token
  suông.
- Payload JWT không chứa `role` hay danh sách permission; đổi role của user có
  hiệu lực ngay ở request kế tiếp mà không cần phát lại token.
- `must_change_password = True`: mọi endpoint trừ `/api/change-password/` bị chặn
  `403 PASSWORD_CHANGE_REQUIRED` kể cả khi access token hợp lệ (§9.2).
- Token không xuất hiện trong log, `AuditLog` hay query string ở bất kỳ luồng nào.
- Sinh schema OpenAPI hai lần trên cùng một cây mã cho ra **byte giống hệt nhau**;
  mọi path đều bắt đầu bằng `/api/v1/` và mọi operation có `operationId` duy nhất,
  ổn định qua các lần sinh (R-103).
- Artifact đã commit lệch với mã nguồn: lệnh kiểm drift thoát khác `0` và **gọi
  tên** đúng file lệch (`contracts/openapi.yaml` hoặc `src/shared/api/schema.ts`).
- So hợp đồng: thêm trường response **tùy chọn** hoặc thêm endpoint mới dưới
  `/api/v1/` thì kiểm tra tương thích **pass**; xóa trường, đổi kiểu, hoặc thêm
  trường bắt buộc vào request thì **fail** và in ra `operationId` + tên trường.
- Mọi response lỗi có `error_code`, `message`, `details`, `request_id`, kèm mirror
  deprecated `error` bằng đúng `error_code`; `request_id` khớp header
  `X-Request-Id`; lỗi theo trường vẫn còn khóa ở cấp cao nhất **và** có bản sao
  trong `details` (R-103).
- `API_DOCS_ENABLED` không bật: `GET /api/v1/schema/` trả `404` vì route không
  được đăng ký (không phải bị từ chối). Bật cờ thì trả schema YAML.
- Schema và client sinh ra không chứa property JSON `refresh_token`, không chứa
  giá trị example là mật khẩu, token hay tọa độ.
