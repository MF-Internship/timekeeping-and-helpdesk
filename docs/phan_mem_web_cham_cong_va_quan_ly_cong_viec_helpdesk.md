# **Phần mềm Web Chấm công và Quản lý công việc Helpdesk**

## **1. Giới thiệu**

Phần mềm Web Chấm công và Quản lý công việc Helpdesk được xây dựng nhằm hỗ trợ đội ngũ kỹ thuật, bảo trì, helpdesk và nhân viên hiện trường quản lý việc chấm công cũng như theo dõi quá trình thực hiện công việc hằng ngày.

Hệ thống được thiết kế với tiêu chí **đơn giản, dễ sử dụng**, hạn chế tối đa việc nhập liệu. Giao diện trực quan, các thao tác chỉ gồm một vài bước, phù hợp với nhân viên thường xuyên làm việc ngoài hiện trường hoặc lao động kỹ thuật, giúp giảm thời gian thao tác và tăng tính chính xác của dữ liệu.

## **2. Mục tiêu**

- Quản lý chấm công đúng thời gian và đúng địa điểm.
- Theo dõi công việc của từng nhân viên theo thời gian thực.
- Ghi nhận đầy đủ bằng chứng hoàn thành công việc.
- Hỗ trợ thống kê, báo cáo nhanh cho lãnh đạo và quản lý.
- Hạn chế nhập liệu thủ công, ưu tiên thao tác nhanh trên điện thoại.

Frontend: Nextjs

Backend: Django REST framework

Database: Postgres

## **3. Các chức năng chính**

### **3.1. Chấm công (Check In / Check Out)**

Hệ thống hỗ trợ chấm công trong ca làm việc, cho phép **nhiều lượt vào/ra trong
cùng một ngày**.

#### **Chức năng**

- Check In.
- Check Out.
- Cho phép nhiều lượt Check In / Check Out trong cùng một ngày.
- Quy định khung giờ chấm công.
- Quy định vị trí được phép chấm công.
- Sử dụng GPS của thiết bị để xác thực vị trí.
- Chỉ cho phép chấm công khi nhân viên đứng **trong một địa điểm đã đăng ký**
  (TTKD hoặc cửa hàng) và nằm trong bán kính cho phép (mặc định 50 mét). Ngoài
  bán kính thì **không** chấm công được — đây là cổng chặn, áp dụng cho mọi lượt
  bấm trong ngày chứ không riêng lượt đầu.
- Lưu lại:
  - Thời điểm server ghi nhận (nguồn sự thật tính công).
  - Thời điểm thiết bị lấy GPS, nếu có, chỉ phục vụ audit/debug.
  - Tọa độ GPS.
  - Sai số ngang của lần đo GPS.
  - Địa điểm (`Location`) đã xác định và khoảng cách tới tâm địa điểm đó. Bản ghi
    chấm công luôn gắn với đúng một địa điểm; hệ thống không lưu chuỗi địa chỉ
    riêng mà lấy địa chỉ từ chính `Location` khi hiển thị.
  - Metadata thiết bị/trình duyệt phục vụ audit.

Thời gian do server ghi nhận theo UTC, sau đó đổi về `Asia/Ho_Chi_Minh` để xác
định ngày công, Check In muộn và Check Out sớm. Hệ thống không dùng giờ do điện
thoại gửi để tính công.

#### **Sai số GPS trong kiểm tra vị trí**

Một lần đo GPS gồm hai đại lượng: tọa độ thiết bị báo về, và **sai số ngang** của
chính lần đo đó. Hệ thống kiểm tra chúng bằng **hai cổng độc lập**, đi lần lượt:

- **Cổng chất lượng** — `sai số ≤ trần sai số cho phép` (mặc định 25 m). Lần đo
  quá kém thì không dùng được: hệ thống báo tín hiệu GPS yếu, mời nhân viên đứng
  yên vài giây rồi đo lại, và không ghi bản ghi chấm công nào.
- **Cổng vị trí** — `khoảng cách tới tâm địa điểm ≤ bán kính cho phép`. Đạt thì
  **trong vùng**, không đạt thì **ngoài vùng**.

Chỉ có **hai** kết luận vị trí: trong vùng hoặc ngoài vùng. Không còn trạng thái
"chưa kết luận được".

Lý do bỏ trạng thái thứ ba: cách tính cũ `khoảng cách + sai số ≤ bán kính` biến
sai số thành một khoản **trừ thẳng vào bán kính**. Với bán kính 50 m và một lần
đo sai số 25 m đúng chuẩn cho phép, vùng chấm công thực tế chỉ còn 25 m — nhân
viên đứng ngay trong cửa hàng vẫn bị từ chối. Hai cổng độc lập tách bạch được
"phép đo có đủ tin cậy không" và "người có đứng trong vùng không", nên trần sai
số **không** cần nhỏ hơn bán kính nhỏ nhất; hai con số này không trừ lẫn nhau.

Hệ thống cũng không hỏi nhân viên "bạn có đang ở đây không?" — đó là phép đo hệ
thống phải tự làm.

Quản lý có thể cấu hình:

- Giờ bắt đầu ca.
- Giờ kết thúc ca.
- Số phút ân hạn Check In muộn, Check Out sớm và Check Out muộn (mặc định 60
  phút cho Check Out muộn).
- Ngày làm việc trong tuần và danh sách ngày nghỉ lễ. Hai thứ này dùng để **đọc
  báo cáo** — biết ngày nào đáng lẽ có người đi làm — chứ **không** chặn chấm
  công và **không** làm rà soát cuối ngày ngừng chạy (§3.1). Quản lý ngày nghỉ lễ
  là quyền riêng của **Quản lý**.
- Bán kính cho phép (mặc định 50 m, tối đa 70 m).
- Trần sai số GPS chấp nhận được cho chấm công (mặc định 25 m).
- Khi mở màn chấm công và đã cấp quyền vị trí, ứng dụng đo GPS foreground có giới
  hạn và hiển thị sai số trực tiếp để nhân viên chờ đạt ngưỡng rồi bấm. Ứng dụng
  dừng đo khi rời màn/tab ẩn/timeout/đã gửi, không theo dõi nền và không tự chấm
  công. Nếu chưa cấp quyền, người dùng chủ động bấm “Bật vị trí”.

#### **Nhiều lượt chấm công trong một ngày**

Một `AttendanceSession` là **ca làm việc từ Check In đến Check Out**, không phải
thời gian nhân viên liên tục đứng trong geofence. Sau Check In, nhân viên được
rời địa điểm để di chuyển hoặc xử lý công việc ở bất kỳ tọa độ nào mà không cần
Check Out. Hệ thống vẫn cho phép nhiều ca trong cùng ngày, với luật **vào trước,
ra sau, xen kẽ nhau**.

- Mỗi cặp Check In → Check Out là một **phiên làm việc**.
- Đang trong phiên thì màn hình chỉ hiện nút **Check Out**; đã ra ca thì chỉ hiện
  nút **Check In**. Không bấm Check In hai lần liên tiếp, cũng không bấm Check Out
  khi chưa vào ca.
- **Giờ công của ngày = tổng thời lượng các phiên**. Mỗi phiên tính từ server time
  của Check In tới server time của Check Out; không trừ thời gian di chuyển hoặc
  làm Task ngoài geofence khi phiên vẫn mở. Khoảng giữa hai phiên không được tính.
- Check Out có thể ở Location khác Check In nếu sự kiện Check Out qua policy;
  hệ thống hiển thị riêng địa điểm vào ca và địa điểm ra ca.
- Màn hình chấm công hiển thị danh sách các lượt trong ngày kèm giờ, địa điểm và
  tổng giờ công tạm tính.

**Đi muộn / về sớm tính theo ngày, không theo từng lượt.** Chỉ lượt Check In
**đầu tiên** trong ngày được xét đi muộn, và chỉ lượt Check Out **cuối cùng** được
xét về sớm hay ra muộn. Các lượt giữa ngày không bị đánh dấu bất thường — nếu
không thì mỗi lần ra ngoài buổi sáng đều bị ghi là "về sớm".

MVP chưa hỗ trợ ca qua ngày: một phiên luôn thuộc về đúng một ngày công. Nếu cuối
ngày còn phiên chưa Check Out, hệ thống tự đóng phiên đó và đánh dấu **thiếu Check
Out**; hệ thống **không tự điền giờ ra ca**, và phiên này không được cộng vào tổng
giờ công mà hiển thị cho quản lý xử lý. Việc rà soát này **chạy mọi ngày**, kể cả
Chủ nhật và ngày nghỉ lễ đã khai báo: một phiên mở từ thứ Bảy vẫn phải được đóng
vào sáng Chủ nhật chứ không nằm treo qua kỳ nghỉ. Sáng hôm sau nhân viên Check In
bình thường.

Dấu **thiếu Check Out** cũng được ghi **không phân biệt ngày**: phiên mở rơi vào
Chủ nhật hay ngày nghỉ lễ vẫn được đánh dấu như ngày thường. Lý do đơn giản —
người đó có bấm Check In thật, nên thiếu Check Out là dữ liệu thiếu cần quản lý
xử lý, không phải chuyện được im lặng bỏ qua. Nhờ vậy mọi phiên hệ thống tự đóng
đều xuất hiện trong báo cáo, không có phiên nào bị đóng âm thầm.

Mỗi lần bấm Check In/Check Out đều được ghi lại một dòng nhật ký riêng, kèm kết
quả — đúng **bảy** giá trị: được chấp nhận; chờ chọn địa điểm; hoặc bị từ chối vì
GPS yếu, ngoài mọi vùng cho phép, địa điểm chọn không hợp lệ, đang có phiên mở,
không có phiên mở. Nhật ký này lưu cả tọa độ, sai số và địa điểm gần nhất để phục
vụ báo cáo; nó **không phải** bản ghi chấm công và không được cộng vào bảng công.
Dòng nhật ký được ghi **độc lập** với việc ca công có được tạo hay không: một lượt
bấm bị từ chối vẫn để lại nhật ký, không bị xóa theo.

#### **Chấm công khác địa điểm được phân công**

Nhân viên chấm công tại một địa điểm khác với địa điểm đang được phân công thì
vẫn **được chấm công bình thường** — điều động chéo giữa các cửa hàng là việc
diễn ra hằng ngày. Hệ thống **không đánh dấu, không cảnh báo và không báo cáo**
việc này: mọi Location đang hoạt động đều hợp lệ như nhau. Bản thân địa điểm đã
được ghi trên từng bản ghi chấm công nên quản lý vẫn tra được ai bấm ở đâu, nhưng
đó là dữ liệu thường, không phải bất thường.

### **3.2. Quản lý công việc (Task)**

Hệ thống cho phép quản lý toàn bộ công việc hằng ngày của nhân viên.

#### **Nguồn tạo công việc**

**Quản lý giao việc**

Người quản lý tạo công việc và phân công trực tiếp cho một hoặc nhiều nhân viên.
Quản lý được phép giao việc cho ngày tương lai để lập kế hoạch trước. Công việc
tương lai hiển thị trong nhóm **Sắp tới** và không tính vào KPI của ngày hiện tại
trước khi tới ngày được giao.

**Helpdesk tự tạo việc**

Trong quá trình làm việc, nhân viên có thể tự tạo công việc phát sinh mà không cần chờ quản lý giao.

#### **Thông tin công việc**

- Tên công việc.
- Mô tả ngắn.
- Người thực hiện (một hoặc nhiều người được giao).
- Ngày thực hiện được giao — quyết định công việc nằm ở nhóm **Hôm nay**,
  **Sắp tới** hay **Quá hạn**.
- Địa điểm dự kiến, nếu quản lý chọn khi giao việc.
- Thời gian tạo.
- Trạng thái.

Thiết kế biểu mẫu tối giản, chỉ yêu cầu các thông tin cần thiết để thao tác nhanh trên điện thoại.

Danh sách công việc tối thiểu có bốn nhóm:

- **Quá hạn** — việc từ ngày trước còn đang mở. Nhóm này hiển thị **trên cùng**,
  trước nhóm Hôm nay, để việc chưa xong đập vào mắt trước việc mới.
- **Hôm nay**.
- **Sắp tới**.
- **Đã hoàn thành**.

Việc quá hạn “trôi” sang ngày mới **chỉ ở phần hiển thị**: ngày thực hiện được
giao giữ nguyên như lúc giao, hệ thống không tự viết lại nó. Mỗi dòng quá hạn
hiện đúng ngày được giao ban đầu kèm nhãn **“trễ N ngày”**, tính tại thời điểm
xem. Nhờ vậy người xem biết ngay việc này là của hôm trước chưa xong, còn báo
cáo của những ngày đã qua không bị đổi số mỗi đêm (CHOT §6.1).

Mỗi công việc có một trong bốn trạng thái:

- **Chưa bắt đầu** (`TODO`).
- **Đang thực hiện** (`IN_PROGRESS`).
- **Có vướng mắc** (`BLOCKED`) — bắt buộc ghi lý do/vướng mắc.
- **Đã hoàn thành** (`COMPLETED`).

Task `BLOCKED` được tiếp tục ở ngày sau trên chính task đó, không tạo task mới.

### **3.3. Hoàn thành công việc**

Khi đến hiện trường và hoàn thành công việc, nhân viên thực hiện:

- Đánh dấu hoàn thành.
- Chụp ảnh hiện trường: bắt buộc từ 1 đến 5 ảnh.
- Hệ thống tự động lấy GPS hiện tại.
- Lưu thời gian hoàn thành.
- Lưu tọa độ GPS.
- Lưu hình ảnh minh chứng.
- Ảnh được kiểm tra/chuyển đổi/nén trước khi gửi; ảnh HEIC đọc được chuyển sang
  JPEG, ảnh không đọc được được báo ngay trước upload. Mỗi ảnh upload riêng vào
  vùng staging private; ảnh đã gửi xong không phải gửi lại khi ảnh khác timeout.
  Task chỉ hoàn thành sau một lần finalize nhẹ với GPS mới và server xác nhận đủ
  ảnh đọc lại được.
- Bản nháp ảnh đã nén và ghi chú có thể giữ tối đa 7 ngày theo đúng tài khoản và
  Task để phục hồi khi khóa máy/rời màn. Bản nháp không giữ GPS/token/URL upload,
  bị xóa khi logout/đổi account/hoàn thành đã xác minh hoặc user tự xóa. Web app
  không hứa upload nền.

Ràng buộc ảnh và GPS ở trên **chỉ áp dụng cho hoàn thành tại hiện trường**
(`FIELD_EVIDENCE`): trong luồng này ảnh minh chứng luôn phải kèm tọa độ.
**`MANAGER_OVERRIDE` là ngoại lệ** — 0 đến 5 ảnh và không bắt buộc GPS, bù lại
bắt buộc ghi chú lý do (xem cuối §3.3). Ngoài tọa độ, nếu xác định được thì hệ
thống hiển thị luôn **địa chỉ đã xác nhận** — xem §3.4.

GPS của Task là bằng chứng hiện trường, khác với GPS xác thực chấm công. Nếu
sai số GPS cao, hệ thống cảnh báo và mời lấy lại vị trí; nếu vẫn cao vẫn cho hoàn
thành khi đủ ảnh/toạ độ, đồng thời lưu nguyên sai số và phân loại chất lượng GPS:
**tốt** (tối đa 25 m), **sai số cao** (trên 25 đến 100 m), hoặc **không tin cậy**
(trên 100 m). Báo cáo tách rõ các nhóm này.

Với công việc giao cho nhiều người: **một người hoàn thành là việc xong**, và hệ
thống đánh dấu hoàn thành cho **toàn bộ người được giao**. Những người còn lại
không phải làm lại và không phải chụp ảnh — ảnh cùng GPS ở trên chỉ đòi ở người
thực sự hoàn thành. Việc vẫn hiện trong danh sách "đã xong hôm nay" của họ, kèm
tên người đã làm.

Công việc chỉ có **một trạng thái duy nhất** dùng chung cho mọi người được giao;
không có trạng thái riêng theo từng người. Vì vậy báo cáo phải tách "việc được
giao đã đóng" khỏi "việc tự tay hoàn thành" (§4).

Nếu công việc chưa hoàn tất và có vướng mắc, nhân viên có thể chọn trạng thái:

**Chưa xong — có vướng mắc**

Khi đó công việc vẫn được giữ lại để tiếp tục xử lý vào ngày khác mà không cần tạo mới.

Ngoài luồng hoàn thành tại hiện trường, Quản lý được phép đóng việc hộ trong
trường hợp quản trị hoặc xác nhận ngoại lệ. Khi đó hệ thống ghi
`completion_method = MANAGER_OVERRIDE`, bắt buộc có ghi chú lý do, cho phép 0 đến
5 ảnh và không cần GPS, có ghi nhật ký thao tác, và báo cáo phải tách riêng với
hoàn thành có bằng chứng hiện trường (`FIELD_EVIDENCE`).

Luồng hoàn thành tại hiện trường vẫn giữ phạm vi "người tạo hoặc người được
giao", kể cả với Quản lý: bằng chứng hiện trường khẳng định chính người bấm đã
tới nơi. Quản lý muốn đóng việc của người khác thì dùng đường `MANAGER_OVERRIDE`.

### **3.4. Xác định địa điểm thực hiện**

Hệ thống có **76 địa điểm (`Location`)**, tương ứng trực tiếp 7 trung tâm kinh
doanh và 69 cửa hàng trong dữ liệu nguồn. Đây là tập đóng: không tạo hoặc xóa
địa điểm thủ công; Quản lý chỉ được sửa thông tin cho phép trên 76 địa điểm hiện
có. Mỗi địa điểm bao gồm:

- Tên địa điểm.
- Địa chỉ.
- Tọa độ GPS.
- Bán kính cho phép.

Không gộp các địa điểm có cùng địa chỉ **hoặc cùng tọa độ**. Nếu một địa chỉ có
hai hoặc nhiều trung tâm/cửa hàng, chúng vẫn là những `Location` riêng; geofence
giao nhau là hợp lệ và hệ thống chỉ cảnh báo khi quản lý cấu hình. Dữ liệu hiện
tại có một cặp cửa hàng trùng đúng tọa độ và hai cặp cách nhau dưới 50 m, nên
màn hình chọn địa điểm luôn hiển thị **mã kèm tên** để nhân viên phân biệt được.

Khi Quản lý sửa Location hoặc Config nhưng các giá trị thực tế không đổi, hệ
thống trả thành công như một no-op và không tạo thêm lịch sử giả. Riêng Location
vẫn kiểm version trước: màn hình cũ phải refresh khi conflict, không được coi là
no-op. Nếu Quản lý hạ bán kính tối đa xuống thấp hơn bán kính của bất kỳ Location
nào (kể cả đang tắt), toàn bộ thay đổi bị từ chối và giao diện liệt kê mã địa điểm
cần xử lý; hệ thống không tự thu nhỏ bán kính hàng loạt.

Task có thể hoàn thành tại bất kỳ tọa độ nào, kể cả công an phường, ủy ban,
trường học hoặc nơi khác ngoài 76 Location. Không khớp địa điểm đã biết không
chặn hoàn thành; chỉ GPS tốt khớp nhiều geofence mới yêu cầu chọn để giải quyết
mơ hồ. Trình tự là:

1. Lấy một mẫu GPS mới từ điện thoại ngay trước khi gửi: tọa độ, sai số ngang và
   thời điểm lấy mẫu. Đây là nguồn vị trí duy nhất; ảnh không dùng EXIF để lấy
   hoặc đối chiếu vị trí.
2. Với GPS chất lượng tốt, hệ thống đối chiếu các `Location` mà lần đo nằm
   **trong vùng** theo luật hai cổng ở §3.1:
   - **Không có địa điểm nào** → chỉ có tọa độ GPS.
   - **Đúng một** → tự động ghi nhận địa điểm đó.
   - **Từ hai trở lên** → bắt buộc nhân viên chọn một ứng viên theo mã + tên;
     backend kiểm lại lựa chọn trước khi cho hoàn thành.
   GPS sai số cao/không tin cậy bỏ qua bước đối chiếu, chỉ lưu tọa độ làm bằng
   chứng và không tự gán tên địa điểm.
3. Sau khi nhánh trên hợp lệ, hệ thống lưu tọa độ gốc, sai số, ảnh, Location nếu
   có và toàn bộ candidate dùng để audit, rồi đóng công việc.

Khi có nhiều ứng viên, việc chọn là **điều kiện để đóng việc**; không có luồng gán
Location sau hoàn thành. Hệ thống lưu cách địa điểm được xác định: một địa điểm
tự động, người dùng chọn, hoặc chỉ có tọa độ GPS. Không tự chọn bằng khoảng cách gần nhất, công việc,
ca làm hoặc lịch sử vì có thể ghi nhầm đơn vị khi địa chỉ trùng nhau.

Nhật ký thực hiện công việc là **lịch sử bất biến**: mỗi lần đổi trạng thái sinh
thêm một dòng mới, không dòng nào bị sửa hay xóa. Location mơ hồ được giải quyết
trước khi tạo dòng hoàn thành. Trạng thái hiển thị trên công việc luôn là **ảnh
chụp của dòng nhật ký mới nhất**, nên không bao giờ có chuyện công việc hiện "đã
hoàn thành" mà lịch sử không có dòng nào nói vậy.

Với bản ghi chưa có Location, màn hình và báo cáo phân biệt **GPS không đủ tin
cậy để đối chiếu** với **ngoài mọi địa điểm đã đăng ký**. GPS tốt có nhiều ứng
viên không tạo bản ghi cho tới khi người dùng chọn, nên không có trạng thái hoàn
thành “nhiều địa điểm phù hợp, chưa chọn”. Cả chấm công và hoàn thành Task đều
yêu cầu chọn khi có từ hai candidate.

#### **Địa chỉ minh chứng và mở Google Maps**

Với ảnh minh chứng hoàn thành công việc, tọa độ là **bắt buộc**; xác nhận địa chỉ
là phần "nếu được", không phải điều kiện để đóng việc. Hệ thống hiển thị theo ba
trường hợp:

| Trường hợp | Hiển thị |
|---|---|
| Xác định được đúng địa điểm (tự động hoặc nhân viên chọn) | Tên + địa chỉ của địa điểm đó, kèm nhãn **Đã xác nhận** và khoảng cách tới tâm |
| GPS tốt nhưng không thuộc địa điểm nào | Tọa độ + ghi chú "Ngoài mọi địa điểm đã đăng ký" |
| GPS sai số cao | Tọa độ + ghi chú "GPS sai số cao, chưa xác nhận địa chỉ" kèm sai số |

Địa chỉ xác nhận **chỉ đối chiếu với 76 địa điểm trong hệ thống**. MVP không gọi
dịch vụ tra cứu địa chỉ bên ngoài: không tốn phí API, không gửi vị trí nhân viên
ra dịch vụ thứ ba, và không đoán địa chỉ hành chính khi không khớp địa điểm nào.

Mọi bản ghi có tọa độ — cả chấm công lẫn minh chứng công việc — đều hiển thị tọa
độ dưới dạng **link mở Google Maps**: nhấn vào là mở ứng dụng Maps trên điện thoại
hoặc trang Google Maps trên trình duyệt, đúng ngay điểm nhân viên đã đứng (không
phải tâm của địa điểm đã đăng ký).

Tại màn hình chi tiết công việc:

- Hiển thị tên và địa chỉ địa điểm (nếu xác định được).
- Hiển thị tọa độ GPS và sai số.
- Nhấn vào tọa độ để mở Google Maps và xem vị trí trực tiếp.

### **3.5. Quản lý người dùng**

Hệ thống cho phép người quản lý quản lý danh sách người sử dụng trong phạm vi được phân quyền.

#### **Chức năng**

- Thêm mới người dùng.
- Chỉnh sửa thông tin người dùng.
- Khóa/Mở khóa tài khoản.
- Đặt lại mật khẩu.
- Gán vai trò cho người dùng: **Leader** hoặc **Helpdesk**. Quản lý **không** tự
  gán được vai trò Quản lý cho ai — tài khoản Quản lý chỉ tạo qua seed hoặc
  superuser, để một Quản lý không thể tự nhân bản quyền của mình.

Bốn chức năng đầu áp dụng cho tài khoản **Lãnh đạo** và **Helpdesk**. Với tài
khoản **Quản lý**, cả bốn đều bị từ chối — thêm mới không nhận vai trò Quản lý,
còn sửa/khóa/đặt lại mật khẩu trên một tài khoản Quản lý sẵn có đều không được
phép, kể cả khi đó là tài khoản của chính người đang thao tác (xem §5.2). Danh
sách người dùng vẫn hiển thị đầy đủ tài khoản Quản lý để tổng số nhân sự không
lệch; chỉ các thao tác ghi bị chặn.

Chỉ **Quản lý** vào được màn hình danh sách người dùng. Lãnh đạo giám sát qua báo
cáo chấm công và công việc — vốn đã hiện đủ tên nhân viên — nên không có màn hình
danh bạ kèm số điện thoại, email và trạng thái khóa.

**Mật khẩu ban đầu do hệ thống sinh.** Người quản lý không tự đặt mật khẩu cho
nhân viên. Khi thêm mới người dùng hoặc đặt lại mật khẩu, hệ thống sinh một mật
khẩu ngẫu nhiên và **hiển thị đúng một lần** ngay trên màn hình để quản lý đọc
lại cho nhân viên; đóng thông báo đi là không xem lại được ở bất kỳ đâu, mất thì
đặt lại lần nữa. Cách này tránh việc cả đội dùng chung một mật khẩu dễ đoán. Mật
khẩu đó **chỉ dùng để đăng nhập ban đầu**: vào tới nơi, nhân viên buộc phải đổi
mật khẩu trước khi làm được bất cứ việc gì khác. Nói cho rõ để khỏi hiểu nhầm —
mật khẩu này không tự hết hạn: nhận hôm nay, tuần sau mới đăng nhập vẫn vào được,
và đăng nhập hụt giữa chừng thì cứ đăng nhập lại. Thứ chặn là yêu cầu đổi mật
khẩu, không phải cái đồng hồ đếm ngược.

**Khóa tài khoản không xóa công việc đang dở.** Khóa chỉ chặn đăng nhập và chặn
giao việc mới: ở **màn hình giao việc**, ô chọn người nhận chỉ hiện tài khoản
đang hoạt động — còn màn hình quản trị người dùng vẫn liệt kê đủ cả người đã
khóa. Dù chọn cách nào, giao việc cho tài khoản đã khóa vẫn bị hệ thống từ chối
ở phía máy chủ. Ngược lại, công việc đã giao trước đó vẫn
giữ nguyên người phụ trách và trạng thái, vẫn nằm ở nhóm Quá hạn để quản lý nhìn
thấy và tự xử — giao thêm người khác, hoặc tự xác nhận hoàn thành kèm ghi chú.
Báo cáo và lịch sử vẫn đếm đủ phần việc người đó đã làm; số liệu tháng trước
không được tự đổi chỉ vì hôm nay có người nghỉ việc.

Khóa một tài khoản đã khóa hoặc mở một tài khoản vốn đang mở vẫn trả về trạng
thái hiện tại nhưng không tạo thêm một lần thay đổi giả trong lịch sử. Ngược lại,
đặt lại mật khẩu lần nữa luôn là một yêu cầu mới: hệ thống sinh mật khẩu mới và
hiển thị lại đúng một lần; mật khẩu của lần reset trước hết hiệu lực.
- Cập nhật thông tin cá nhân:
  - **Họ và tên — bắt buộc, không được để trống.** Đây là tên hiển thị ở mọi danh
    sách, báo cáo và ô tìm kiếm, nên tên rỗng làm hỏng toàn bộ các màn đó.
  - Số điện thoại — **không bắt buộc**, và **được phép trùng nhau** giữa các tài
    khoản (nhiều nhân viên dùng chung một máy bàn cửa hàng là chuyện thường).
  - Email — **không bắt buộc**, cũng **được phép trùng**.
- Tìm kiếm và lọc danh sách người dùng theo tên, tài khoản, vai trò hoặc trạng
  thái khóa. Các bộ lọc đều **tùy chọn**: không chọn gì thì danh sách trả về
  **cả tài khoản đang khóa**, để quản lý còn thấy mà mở lại.

Khi thêm mới, hệ thống chỉ bắt buộc **ba** thông tin: **tên đăng nhập**, **họ và
tên**, **vai trò**. Số điện thoại và email điền sau lúc nào cũng được. Tên đăng
nhập là duy nhất và **không sửa được** sau khi tạo — muốn đổi thì tạo tài khoản
mới, vì tên đăng nhập là thứ mọi nhật ký và báo cáo cũ đã trỏ tới.

Người dùng chỉ được đăng nhập khi tài khoản đang hoạt động.

#### **Phiên đăng nhập**

Nhân viên hiện trường dùng điện thoại cả ngày nên **không phải đăng nhập lại
nhiều lần trong ca**: đăng nhập một lần, ứng dụng tự duy trì phiên trong khoảng
một tuần miễn là còn sử dụng. Đổi lại, quản lý phải cắt được truy cập khi cần:
khi người dùng bấm đăng xuất, khi quản lý khóa tài khoản, khi quản lý đặt lại
mật khẩu, hoặc khi chính người dùng đổi mật khẩu, hệ thống **thu hồi toàn bộ
phiên trên mọi thiết bị** của người đó. Thao tác mutation và lần thu hồi thực sự
có phiên bị cắt được ghi nhật ký; gọi lặp không đổi trạng thái không tạo lịch sử giả.

Mức độ tức thời khác nhau theo tình huống, và tài liệu không được nói mạnh hơn
thực tế — xem câu canonical ở [CHỐT §9.2.1](CHOT_YEU_CAU.md):

- **Khóa tài khoản** (và **buộc đổi mật khẩu**) chặn **ngay ở thao tác kế tiếp**,
  vì mọi request đều kiểm lại trạng thái tài khoản.
- **Đăng xuất, đặt lại mật khẩu, tự đổi mật khẩu** cắt đường gia hạn phiên ngay,
  nhưng thiết bị đang mở còn thao tác được **tối đa 15 phút** cho tới khi vé truy
  cập hiện hành hết hạn. Đây là đánh đổi đã chốt, không phải thiếu sót.

Riêng **tự đổi mật khẩu** có một ngoại lệ về trải nghiệm: người vừa đổi mật khẩu
không bị đá ra màn hình đăng nhập. Hệ thống thu hồi toàn bộ phiên cũ **rồi mới**
cấp lại phiên mới cho đúng thiết bị đang thao tác, nên các máy khác mất quyền còn
máy này dùng tiếp bình thường. Đây là chỗ duy nhất vừa thu hồi vừa cấp phiên mới
trong cùng một thao tác.

Vì vậy, khi máy bị mất, thao tác đúng là **khóa tài khoản** — chỉ đặt lại mật
khẩu thì vẫn còn cửa sổ tối đa 15 phút.

Đăng xuất là thao tác idempotent: chỉ cần access token còn hợp lệ, hệ thống luôn
trả thành công, xóa cookie và thử thu hồi toàn bộ phiên của đúng tài khoản đang
đăng nhập, kể cả cookie refresh đã thiếu/hỏng/hết hạn. Bấm lại không tạo thêm một
dòng lịch sử nếu không còn phiên nào để thu hồi. Cách này không biến cookie lỗi
thành lý do giữ các phiên khác sống sót.

Khi bị chặn, ứng dụng phải nói rõ **lý do** thay vì báo lỗi chung chung: phiên
hết hạn thì tự làm mới hoặc yêu cầu đăng nhập lại, tài khoản bị khóa thì hiện
"Tài khoản đã bị khóa, liên hệ quản lý" và ngừng thử lại, tài khoản buộc đổi mật
khẩu thì đưa thẳng sang màn hình đổi mật khẩu, còn thiếu quyền thì báo không đủ
quyền. Riêng màn hình đăng nhập vẫn báo chung "sai tài khoản hoặc mật khẩu" cho
cả trường hợp tài khoản bị khóa, để không tiết lộ tài khoản nào có tồn tại.

## **4. Báo cáo và thống kê**

Hệ thống cung cấp các báo cáo phục vụ công tác quản lý.

Ví dụ:

- Danh sách nhân viên đang trong ca (còn phiên mở).
- Danh sách nhân viên chưa Check In lần nào trong ngày.
- Danh sách nhân viên đã ra ca.
- Bảng giờ công theo ngày: **số lượt** chấm công, danh sách phiên và **tổng thời
  lượng các phiên**. Giờ công không tính bằng hiệu giữa lần bấm đầu và lần bấm
  cuối; thời gian giữa hai phiên bị loại trừ, nhưng thời gian làm việc ngoài
  geofence trong một phiên vẫn được tính.
- Danh sách phiên bị hệ thống đóng cuối ngày vì thiếu Check Out — tách riêng,
  không cộng vào tổng giờ và không có giờ ra ca ước lượng.
- Tổng số công việc trong ngày.
- Công việc đã hoàn thành.
- Công việc đang thực hiện.
- Công việc đang mở.
- Báo cáo theo nhân viên — có **hai cột việc riêng biệt**: _"Việc tự tay hoàn
  thành"_ (người thực sự làm) và _"Việc được giao đã đóng"_ (mọi người được giao
  của việc đó). Việc giao nhiều người mà một người làm xong thì đóng cho tất cả,
  nên hai con số này khác nhau và **không được cộng chung**
  ([CHỐT §9.3](CHOT_YEU_CAU.md)).
- Báo cáo theo khoảng thời gian.
- Nhật ký chấm công.
- Nhật ký thực hiện công việc.
- Báo cáo bất thường chấm công, theo đúng **bốn** loại: vào ca trễ, ra ca sớm,
  ra ca muộn, thiếu Check Out. Đây là bất thường của những ca công **đã được ghi
  nhận**. Vào ca trễ chỉ xét lượt Check In đầu tiên; ra ca sớm/muộn chỉ xét lượt
  Check Out cuối cùng của ngày. **Không** có loại "khác địa điểm phân công": chấm
  công ở địa điểm nào cũng hợp lệ như nhau (§3.1), nên không có báo cáo nào liệt
  kê việc đó.
- Báo cáo **lần chấm công bị từ chối** — thống kê riêng, theo đúng **năm** lý do
  (GPS yếu, ngoài mọi vùng cho phép, địa điểm chọn không hợp lệ, đang có phiên
  mở, không có phiên mở) và **theo từng địa điểm gần nhất**. Nhiều lần "ngoài mọi
  vùng cho phép" lặp lại ở cùng một địa điểm là dấu hiệu bán kính địa điểm đó đặt
  quá nhỏ so với thực địa, cần quản lý nâng lên.

  "Chờ chọn địa điểm" **không** nằm trong năm lý do trên. Đó không phải thất bại
  mà là một bước hỏi bình thường khi nhân viên đứng trong vùng phủ của nhiều địa
  điểm; hệ thống vẫn ghi nhật ký lượt bấm đó, nhưng nó bị **loại khỏi cả tử số
  lẫn mẫu số** của tỉ lệ thất bại — tính vào mẫu số sẽ làm tỉ lệ trông đẹp giả
  tạo ở đúng những cụm cửa hàng gần nhau nhất. Ngoài trường hợp này, hệ thống ghi
  nhật ký **mọi** lần bấm chấm công kể cả lần thành công, nên mẫu số là tổng số
  lần bấm chứ không phải số ca công. Hai báo cáo này không được cộng chung vì
  nguồn dữ liệu khác nhau: một bên là ca công đã ghi, một bên là lần bấm không
  tạo ra ca công.
- Báo cáo hoàn thành công việc theo phương thức: tổng đã hoàn thành, hoàn thành
  có ảnh/GPS hiện trường, hoàn thành do quản lý xác nhận ngoại lệ.
- Mọi attempt đã vào luồng nghiệp vụ có địa điểm gần nhất để gom nhóm; nearest
  của GPS yếu được ghi rõ là xấp xỉ để chẩn đoán, không phải bằng chứng hiện diện.
  Tỉ lệ lỗi luôn hiện tử số/mẫu số, số lượt chọn Location bị loại, coverage và
  `N/A` khi không đủ mẫu; không biến “0 attempt” thành “không có vấn đề”.
- Dashboard hiển thị health của job xử lý thiếu Check Out. Quản lý có đường điều
  tra tài khoản/audit phù hợp; Lãnh đạo chỉ đọc trạng thái và chuyển cho Quản lý.
- Báo cáo theo trạng thái công việc và chất lượng GPS của bằng chứng hiện trường.

## **5. Phân quyền người dùng**

Hệ thống phân quyền theo RBAC. Mỗi endpoint kiểm tra một action cụ thể thay vì
chỉ dựa vào mô tả vai trò bằng câu chữ. Ba vai trò hiện hành là `LEADER`,
`MANAGER`, `HELPDESK`. Quản lý gán được `LEADER` và `HELPDESK` (§3.5); riêng
`MANAGER` chỉ tạo qua seed hoặc superuser, không gán được qua giao diện.

### **5.1. Lãnh đạo**

Có quyền theo dõi và xem báo cáo tổng quan.

Bao gồm:

- Theo dõi tình hình Check In/Check Out.
- Theo dõi công việc trong ngày.
- Xem tiến độ thực hiện.
- Xem hình ảnh hoàn thành.
- Xem báo cáo thống kê.
- Xem vị trí thực hiện công việc.

Lãnh đạo là vai trò **chỉ đọc tuyệt đối**: không tạo, không sửa, không giao, không
đóng việc, không chấm công hộ, không đổi cấu hình, không quản trị người dùng hay
địa điểm. Mọi action ghi đều bị backend từ chối, kể cả khi giao diện lỡ hiển thị
nút.

Phạm vi đọc dừng ở dữ liệu nghiệp vụ: chấm công, công việc, ảnh, vị trí, báo cáo.
Lãnh đạo **không** xem được màn hình danh sách người dùng — tên nhân viên đã hiện
đủ trong báo cáo, nên không cần thêm danh bạ kèm số điện thoại, email và trạng
thái khóa. Đây là quyết định có chủ ý, không phải sót chức năng.

Hai thứ Lãnh đạo **đọc được**, vì thiếu chúng thì báo cáo không hiểu nổi: **danh
sách địa điểm** (để biết bản ghi chấm công trỏ tới đâu) và **cấu hình chấm công**
(để biết ca bắt đầu mấy giờ, ân hạn bao nhiêu phút — nếu không thì con số "vào ca
trễ" là vô nghĩa). Đọc được không kéo theo sửa được: mọi thao tác ghi lên hai thứ
này vẫn là quyền riêng của Quản lý.

### **5.2. Quản lý**

Có toàn bộ quyền của Lãnh đạo và bổ sung các chức năng quản trị hệ thống:

- Tạo và giao công việc cho nhân viên.
- Theo dõi tiến độ thực hiện công việc.
- Cập nhật trạng thái công việc.
- Trực tiếp hoàn thành công việc tại hiện trường bằng ảnh/GPS.
- Đóng việc hộ bằng `MANAGER_OVERRIDE` kèm ghi chú bắt buộc.
- Quản lý danh sách địa điểm làm việc.
- Quản lý danh sách ngày nghỉ lễ — thêm, xem, xóa. Đây là quyền **chỉ Quản lý**
  có, kể cả phần xem, vì danh sách này chỉ phục vụ việc đọc báo cáo chứ không có
  luồng nghiệp vụ nào của Lãnh đạo hay Helpdesk chạm tới.
- Cấu hình thời gian Check In/Check Out.
- Cấu hình bán kính GPS cho chấm công và xác định địa điểm.
- Không thể hạ bán kính tối đa xuống dưới bán kính Location hiện hữu; thao tác bị
  từ chối nguyên tử và không tự sửa Location.
- Cấu hình trần sai số GPS chấp nhận được cho chấm công. Đây là cổng chất lượng
  độc lập với bán kính, không bị ràng buộc phải nhỏ hơn bán kính nhỏ nhất.
- Quản lý người dùng — chỉ với tài khoản **Lãnh đạo** và **Helpdesk**:
  - Thêm, sửa, khóa/mở khóa tài khoản.
  - Đặt lại mật khẩu — hệ thống sinh mật khẩu và hiển thị một lần, quản lý không
    tự đặt (§3.5).
  - Phân quyền người dùng.
- Xem toàn bộ lịch sử chấm công và công việc của tất cả nhân viên.
- Xem và xuất các báo cáo thống kê.
- Export mặc định không chứa tọa độ/Maps URL/URL ảnh. Quản lý và Lãnh đạo phải
  bật tùy chọn rõ ràng để xuất tọa độ; thao tác được audit và file không cache.

Quản lý **không tác động được lên tài khoản Quản lý khác**: vẫn nhìn thấy trong
danh sách người dùng, nhưng không sửa, không khóa/mở khóa, không đặt lại mật khẩu
và không đổi vai trò được — kể cả tài khoản của chính mình. Đây là ranh giới
*đọc được, cấm mọi thao tác ghi*, đặt ra để một tài khoản Quản lý bị chiếm không
thể khóa hay hạ quyền các Quản lý còn lại. Quản lý tự đổi mật khẩu và sửa thông
tin cá nhân qua màn hình cá nhân riêng, không qua màn hình quản trị người dùng.

Quản lý **không chấm công** trong phạm vi hiện tại: không có Check In/Check Out
và không xuất hiện trên bảng công. Việc "trực tiếp hoàn thành công việc tại hiện
trường bằng ảnh/GPS" ở trên là luồng của **công việc**, không phải chấm công —
hai thứ này độc lập.

### **5.3. Helpdesk**

Nhân viên hiện trường sử dụng hằng ngày.

Các chức năng gồm:

- Check In / Check Out, nhiều lượt trong ngày theo thứ tự vào–ra xen kẽ.
- Xem các lượt chấm công và tổng giờ công trong ngày của bản thân.
- Xem danh sách công việc.
- Nhận công việc được giao.
- Tự tạo công việc phát sinh.
- Cập nhật trạng thái công việc.
- Đánh dấu hoàn thành.
- Đánh dấu chưa xong — có vướng mắc để tiếp tục xử lý vào ngày khác.
- Chụp ảnh hoàn thành.
- Gửi vị trí GPS khi hoàn thành công việc; xem lại địa chỉ đã xác nhận và mở vị
  trí trên Google Maps.
- Nhận thông báo trong app và web push (nếu tự bật) khi có Task mới, Task sắp tới
  ngày thực hiện, Task quá hạn, phiên còn mở gần cuối ngày hoặc Task nhiều người
  được người khác hoàn thành. Không gửi email/SMS và không dùng notification cho
  khóa/reset tài khoản.
- Xem lịch sử công việc của bản thân.

Helpdesk không được quản trị người dùng, không quản trị địa điểm, không xem toàn
bộ dữ liệu nếu không có action tương ứng, và không được đóng việc bằng
`MANAGER_OVERRIDE`.

Với chức năng mang hậu tố “của bản thân”, Helpdesk chỉ xem/cập nhật/hoàn thành
Task do mình tạo hoặc được giao. Hệ thống kiểm tra phạm vi Task ở backend, không
chỉ dựa vào việc ẩn nút trên giao diện.

### **5.4. Ma trận quyền chuẩn**

Chỉ có một ma trận `Role × Action` chuẩn ở
[CHOT_YEU_CAU.md](CHOT_YEU_CAU.md). Backend sử dụng trực tiếp ma trận này. Quyền
`.all` **không tự động** bao hàm `.self`; chỉ những cặp có tên trong bảng
`PERMISSION_IMPLIES` đóng ở [CHỐT §8.1](CHOT_YEU_CAU.md) mới suy diễn được, và
hiện có đúng năm cặp. PRD không lặp lại bảng action để tránh phát sinh hai nguồn
quyền mâu thuẫn.

**Sai quyền được báo trước sai dữ liệu.** Hệ thống kiểm quyền **trước** khi soi
nội dung request. Một Helpdesk gọi chức năng tạo người dùng với dữ liệu rỗng
tuếch vẫn nhận đúng một câu trả lời: *không đủ quyền* — chứ không phải danh sách
trường còn thiếu. Ngược lại sẽ để người không có quyền dò ra hệ thống đòi những
trường gì, và làm người dùng đi sửa dữ liệu cho một thao tác mà họ vốn không được
phép làm.

Luật này áp cho cả **đối tượng bị tác động**, không chỉ loại thao tác. Tài khoản
Quản lý nằm ngoài tầm với của mọi thao tác quản trị người dùng, nên một request
nhắm vào tài khoản Quản lý bị trả *không đủ quyền* ngay, bất kể nội dung gửi lên
đúng hay sai — kể cả khi không gửi gì cả. Chỉ khi đã qua được hai cửa này, hệ
thống mới bắt đầu nhận xét về dữ liệu trong request.

## **6. Đặc điểm nổi bật**

- Giao diện tối giản, phù hợp cho nhân viên hiện trường.
- Thao tác nhanh, ít trường nhập liệu.
- Chấm công bằng GPS nhằm đảm bảo đúng vị trí làm việc; bắt buộc đứng trong địa
  điểm đã đăng ký cho **mọi lượt** vào/ra.
- Cho phép nhiều lượt vào/ra trong ngày; giờ công tính bằng tổng thời lượng các
  phiên; rời geofence để làm Task không tự kết thúc phiên.
- Công việc có hình ảnh và vị trí xác thực.
- Tự động đối chiếu địa điểm làm việc từ tọa độ GPS khi xác định được **duy
  nhất** một địa điểm; nếu có nhiều địa điểm phù hợp thì cả chấm công và hoàn
  thành công việc đều bắt nhân viên chọn tại chỗ (§3.4).
- Hỗ trợ tiếp tục công việc đang mở mà không cần tạo lại.
- Báo cáo trực quan theo ngày, nhân viên và trạng thái công việc.
- Mọi bản ghi có tọa độ đều mở được trực tiếp trên Google Maps để kiểm tra hiện
  trường; nếu tọa độ khớp địa điểm đã đăng ký thì hiển thị luôn địa chỉ.

## **7. Nền tảng kỹ thuật và vận hành đã chốt**

Phần này đồng bộ các quyết định đã chốt trong CHOT; nó không chọn nhà cung cấp
hay tạo thêm hành vi nghiệp vụ.

- **FR-15 — Hợp đồng API có phiên bản.** Mọi REST JSON route dùng `/api/v1/`.
  Lỗi dùng thân canonical `{error_code, message, details, request_id}` và giữ
  mirror deprecated của v1; `request_id` do server sinh và khớp
  `X-Request-Id`. OpenAPI và kiểu/client TypeScript được sinh, commit, kiểm drift
  và kiểm tương thích ngược; frontend gọi API qua một `authenticatedFetch`.
- **NFR-27 — Quan trắc an toàn.** Correlation là hạ tầng sở hữu. Mọi trường chuỗi
  có thể mang dữ liệu nhạy cảm trước khi vào log/metric/alert phải đi qua đúng
  bộ làm sạch dùng chung; lỗi telemetry không được làm hỏng thao tác đang được
  quan sát, và thiếu bằng chứng quan trắc phải là `unknown`, không phải `ok`.
- **NFR-28 — Cô lập triển khai.** Development, staging và production không dùng
  chung database, bucket, Redis namespace, signing key hay credential biên.
  Trình duyệt chỉ gọi API qua proxy web; proxy xóa header credential do client
  gửi rồi gắn credential nguồn, còn origin kiểm tra theo thời gian hằng và trả
  lỗi 403 canonical khi thiếu/sai. Các lựa chọn chưa được duyệt giữ nguyên
  `UNRESOLVED`; vì thế không được tuyên bố production-ready.
- **NFR-29 — Di trú và khả năng khôi phục.** Migration chạy trước rollout, tương
  thích N-1 và theo expand–migrate–contract; cột `NOT NULL` mới có `db_default`,
  thao tác phá hủy hoãn sang release sau. Backup hằng ngày, giữ tối thiểu 30
  ngày, mục tiêu RPO không quá 24 giờ và RTO không quá 4 giờ. Bằng chứng chỉ có
  khi restore drill thật (không quá 90 ngày) và phép đo năng lực được ghi
  `passed`/`failed`; phép đo năng lực chỉ đủ điều kiện làm bằng chứng khi dùng ít
  nhất **50 tài khoản thật**, mức đồng thời ít nhất **20**, và p95 không quá
  **500 ms**. Dưới một trong hai ngưỡng đầu phải bị từ chối trước khi gọi mạng;
  p95 vượt 500 ms phải ghi `failed` kèm người chịu trách nhiệm khắc phục, không
  được ghi `passed`. Mọi kết nối/tài nguyên đã mở phải được đóng ở cả đường
  thành công lẫn thất bại. Danh tính, mật khẩu, token, giá trị Bearer, URL chứa
  thông tin xác thực và giá trị bí mật không được xuất hiện trong stdout,
  stderr hoặc kết quả/artifact trả về. Fixture kiểm thử không phải bằng chứng
  vận hành thật; đầu ra của lệnh không tự động làm production-ready hoặc
  recovery-ready. Bằng chứng thật bị `failed` phải có người chịu trách nhiệm
  khắc phục. Các lựa chọn hoặc số đo chưa có vẫn là `UNRESOLVED`.
- **NFR-30 — Hạn mức xác thực dùng chung.** Đăng nhập tối đa 10 request/phút
  theo client IP, refresh tối đa 120 request/phút theo client IP, và đổi mật khẩu
  tối đa 5 request/phút theo tài khoản đã xác thực. Vượt hạn mức trả `429` kèm
  thời gian chờ; kho đếm dùng chung hỏng thì trả `503` và không cho request đi
  tiếp. Các worker không có quota riêng và frontend không tự đoán thời gian chờ.
- **AD-7 / AD-10 / AD-11.** Schema tiến hóa không gãy; ranh giới runtime/admin,
  môi trường và origin được kiểm bằng lệnh chạy được; contract, correlation,
  thông báo và dữ liệu chẩn đoán có một chủ sở hữu dùng chung. Những control nằm
  trong repo phải có kiểm thử, nhưng thao tác nhà cung cấp, restore thật và phép
  đo năng lực vẫn cần người vận hành ký nhận theo CHOT §9.7–§9.8.
