export const UI_MESSAGES = Object.freeze({
  loading: "Đang tải dữ liệu…",
  empty: "Không có dữ liệu để hiển thị.",
  unexpectedResponse: "Phản hồi không hợp lệ. Vui lòng thử lại.",
  networkFailure: "Không thể kết nối. Vui lòng kiểm tra mạng và thử lại.",
  retry: "Thử lại",
  invalidCredentials: "Tên đăng nhập hoặc mật khẩu không đúng.",
  invalidToken: "Phiên đăng nhập không hợp lệ hoặc đã hết hạn.",
  accountInactive: "Tài khoản đã bị khóa, liên hệ quản lý.",
  passwordChangeRequired: "Bạn phải đổi mật khẩu trước khi tiếp tục.",
  permissionDenied: "Bạn không có quyền thực hiện thao tác này.",
  serverOwnedField: "Dữ liệu chứa trường do hệ thống quản lý.",
  validationFailed: "Dữ liệu không hợp lệ.",
  throttled: "Bạn đã gửi quá nhiều yêu cầu. Vui lòng thử lại sau",
  serviceUnavailable: "Dịch vụ tạm thời không khả dụng. Vui lòng thử lại sau.",
  notifications: Object.freeze({
    title: "Thông báo",
    empty: "Bạn chưa có thông báo nào.",
    loadFailure: "Không thể tải hộp thư thông báo.",
    refreshFailure: "Không thể làm mới; danh sách trước đó vẫn được hiển thị.",
    readFailure: "Chưa thể đánh dấu đã đọc.",
  }),
  tasks: Object.freeze({
    title: "Công việc",
    empty: "Không có công việc trong các nhóm hiện tại.",
    loadFailure: "Không thể tải danh sách công việc.",
    staleFailure: "Không thể làm mới; dữ liệu trước đó vẫn đang được hiển thị.",
    create: "Tạo công việc",
    save: "Lưu thay đổi",
    created: "Đã tạo công việc.",
    saved: "Đã lưu thay đổi.",
    statusSaved: "Đã cập nhật trạng thái.",
    completed: "Đã hoàn thành công việc.",
    blockedReason: "Cần nhập lý do khi chuyển sang Bị chặn.",
    completionNote: "Cần nhập ghi chú hoàn thành.",
    mutationFailure: "Không thể lưu. Nội dung đã nhập được giữ lại để bạn thử lại.",
    conflict: "Công việc đã thay đổi. Dữ liệu mới nhất đã được tải lại.",
    noAutomaticRetry: "Hệ thống không tự gửi lại thao tác ghi.",
    expectedLocation: "Địa điểm dự kiến (chỉ là kế hoạch)",
    activeAssignees: "Nhân viên Helpdesk đang hoạt động",
    retainedAssignees: "Người đang được giao",
    overdue: "Quá hạn",
    today: "Hôm nay",
    upcoming: "Sắp tới",
    completedGroup: "Đã hoàn thành",
  }),

  /**
   * Location awareness and geofence guidance. Every string here describes an
   * on-device preview: none of it states an acceptance decision, and none of it
   * offers an action that would relax a server-side rule (FR-021, FR-039).
   */
  guidance: Object.freeze({
    title: "Vị trí và vùng chấm công",
    advisory:
      "Thông tin tham khảo tính trên thiết bị. Máy chủ mới là nơi quyết định khi chấm công.",
    trigger: "Xem vị trí",
    refresh: "Làm mới vị trí",

    /**
     * Said out loud on the Attendance screen, where the preview sits beside the
     * punch controls: it is a reading, not a permission (FR-040).
     */
    previewOnly: "Đây là bản xem trước, không phải kết quả chấm công.",
    previewNotAGate:
      "Bản xem trước này không bật, không tắt, không ẩn và không chặn nút Check In hay Check Out.",

    positionHeading: "Vị trí thiết bị",
    positionPending: "Đang lấy vị trí từ thiết bị…",
    latitudeLabel: "Vĩ độ",
    longitudeLabel: "Kinh độ",

    accuracyHeading: "Chất lượng tín hiệu GPS",
    accuracyLabel: "Sai số hiện tại",
    accuracyThresholdLabel: "Ngưỡng sai số cho phép khi chấm công",
    accuracySufficient: "Sai số đạt yêu cầu chấm công.",
    accuracyInsufficient:
      "Sai số vượt ngưỡng. Chấm công sẽ bị từ chối vì GPS yếu, bất kể bạn đang ở đâu.",
    accuracyIndependent: "Chất lượng tín hiệu được đánh giá tách biệt với vị trí.",
    accuracyUnevaluated: "Chưa có ngưỡng cấu hình nên chưa đánh giá được sai số.",

    capturedAtLabel: "Thời điểm đọc",
    ageLabel: "Đã đọc cách đây",
    secondsUnit: "giây",
    fresh: "Số liệu còn mới.",
    stale: "Số liệu đã cũ.",
    punchTakesNewReading: "Khi chấm công, hệ thống sẽ đọc lại vị trí mới.",
    advisoryLabel: "Chỉ mang tính tham khảo.",

    remediationHeading: "Cách cải thiện tín hiệu trên thiết bị",
    remediation: Object.freeze([
      "Bật định vị chính xác cao cho trình duyệt.",
      "Bật dịch vụ vị trí của thiết bị.",
      "Ra khu vực thoáng, tránh đứng trong nhà hoặc sát vật cản.",
      "Bật Wi-Fi hoặc dữ liệu di động nếu thiết bị cần để định vị.",
      "Chờ một lát để thiết bị bắt được tín hiệu tốt hơn.",
      "Bấm Làm mới vị trí.",
    ]),
    remediationNote:
      "Các thao tác này chỉ cải thiện tín hiệu trên thiết bị, không thay đổi quy tắc của máy chủ.",

    nearbyHeading: "Địa điểm gần bạn",
    nearestLabel: "Gần nhất",
    distanceLabel: "Khoảng cách",
    radiusLabel: "Bán kính",
    inside: "Trong vùng",
    outside: "Ngoài vùng",
    distanceToBoundaryLabel: "Còn cách ranh giới",
    insideMarginLabel: "Cách ranh giới từ bên trong",
    estimateOnly: "giá trị ước tính để tham khảo",
    estimateNote:
      "Khoảng cách tới ranh giới là ước tính để tham khảo, không phải quy tắc chấp nhận chấm công.",

    insideOne: "Bạn đang ở trong vùng của đúng một địa điểm đã đăng ký.",
    insideMany: "Bạn đang ở trong vùng của nhiều địa điểm đã đăng ký chồng lấn.",
    insideManyNote:
      "Khi bạn chấm công, máy chủ sẽ hỏi bạn chọn một trong số đó. Bản xem trước này không chọn thay bạn.",
    outsideAll: "Bạn đang ở ngoài vùng của mọi địa điểm gần đây.",
    noActiveLocations: "Không có địa điểm đang hoạt động nào để đối chiếu.",
    referenceLoading: "Đang tải danh mục địa điểm và cấu hình…",
    referenceUnavailable:
      "Không tải được danh mục địa điểm hoặc cấu hình. Chưa thể đối chiếu vị trí.",
    positionUnevaluated: "Vị trí đọc được vẫn hiển thị nhưng chưa được đối chiếu.",

    /**
     * Acquisition failures, closed at exactly the four outcomes of FR-008a. No
     * wording here reuses an Attendance error code, and every remedy is a
     * device-side action (FR-008b, FR-021).
     */
    failureHeading: "Không lấy được vị trí",
    failure: Object.freeze({
      PERMISSION_DENIED: Object.freeze({
        title: "Trình duyệt đã bị từ chối quyền truy cập vị trí.",
        remedy:
          "Mở cài đặt quyền của trình duyệt hoặc thiết bị, cho phép trang này truy cập vị trí, rồi bấm Làm mới vị trí.",
      }),
      UNAVAILABLE: Object.freeze({
        title: "Thiết bị hoặc trình duyệt này không cung cấp dịch vụ định vị.",
        remedy:
          "Bật dịch vụ vị trí của thiết bị, hoặc mở trang bằng thiết bị và trình duyệt có hỗ trợ định vị.",
      }),
      TIMEOUT: Object.freeze({
        title: "Quá thời gian chờ khi lấy vị trí.",
        remedy: "Ra khu vực thoáng, chờ thiết bị bắt tín hiệu, rồi bấm Làm mới vị trí.",
      }),
      UNKNOWN: Object.freeze({
        title: "Đã xảy ra sự cố không xác định khi lấy vị trí.",
        remedy: "Bấm Làm mới vị trí để thử lại.",
      }),
    }),
    failureNoPosition:
      "Chưa ghi nhận được vị trí nào. Hệ thống không suy đoán vị trí thay cho bạn.",
    failureDeviceOnly:
      "Đây là sự cố phía thiết bị. Không thao tác nào ở đây thay đổi quy tắc của máy chủ.",

    referenceHeading: "Danh mục địa điểm đang hoạt động",
    referenceIndependent: "Danh sách này không phụ thuộc vào vị trí nên vẫn xem được.",

    /**
     * Focus is a way of reading the list, not a choice of Location. The wording
     * says so out loud so the preview is never mistaken for a punch (FR-023).
     */
    targetHeading: "Địa điểm đang xem",
    targetChooser: "Chọn địa điểm để xem chi tiết",
    targetDisplayOnly:
      "Lựa chọn này chỉ để xem trên thiết bị. Nó không được gửi đi, không được lưu, và không chọn sẵn địa điểm cho lần chấm công sau.",

    /**
     * The diagram is drawn on the device from data already in memory. It is a
     * picture of the same numbers the list shows, never a second opinion about
     * them, and never a map fetched from anywhere (FR-025, FR-028, FR-029a).
     */
    diagramHeading: "Sơ đồ tương đối",
    diagramSelfContained:
      "Sơ đồ được vẽ trên thiết bị từ dữ liệu đã có. Không có bản đồ, ảnh nền hay liên kết bên ngoài nào được tải.",
    diagramYou: "Vị trí của bạn",
    diagramTarget: "Địa điểm đang xem trên sơ đồ",
    diagramGeofence: "Vùng đăng ký của địa điểm đang xem",
    diagramAccuracy: "Vòng sai số của thiết bị",
    diagramAccuracyDiagnostic:
      "Vòng sai số chỉ mô tả chất lượng tín hiệu. Nó không nới rộng, không thu hẹp và không dịch chuyển vùng đăng ký.",
    diagramOther: "Địa điểm gần khác",
    diagramSelectHint: "Chạm vào một địa điểm gần khác để chuyển sang xem địa điểm đó.",
    diagramScaleLabel: "Tỉ lệ",
    diagramUnavailable:
      "Chưa đủ dữ liệu vị trí để vẽ sơ đồ. Các số liệu bên trên vẫn là số liệu đầy đủ.",
  }),
});
