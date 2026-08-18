from core.messages import ERROR_MESSAGES


def test_messages_are_centralized_safe_vietnamese_text() -> None:
    assert ERROR_MESSAGES == {
        "VALIDATION_FAILED": "Dữ liệu không hợp lệ.",
        "PERMISSION_DENIED": "Bạn không có quyền thực hiện thao tác này.",
        "INVALID_CREDENTIALS": "Tên đăng nhập hoặc mật khẩu không đúng.",
        "INVALID_TOKEN": "Phiên đăng nhập không hợp lệ hoặc đã hết hạn.",
        "ACCOUNT_INACTIVE": "Tài khoản đã bị khóa, liên hệ quản lý.",
        "PASSWORD_CHANGE_REQUIRED": "Bạn phải đổi mật khẩu trước khi tiếp tục.",
        "SERVER_OWNED_FIELD": "Dữ liệu chứa trường do hệ thống quản lý.",
        "NOT_FOUND": "Không tìm thấy dữ liệu yêu cầu.",
        "LOCATION_VERSION_CONFLICT": "Dữ liệu địa điểm đã được thay đổi.",
        "THROTTLED": "Bạn đã gửi quá nhiều yêu cầu. Vui lòng thử lại sau.",
        "SERVICE_UNAVAILABLE": "Dịch vụ tạm thời không khả dụng. Vui lòng thử lại sau.",
    }
