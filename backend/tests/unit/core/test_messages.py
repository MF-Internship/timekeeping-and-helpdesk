from core.messages import ERROR_MESSAGES


def test_messages_are_centralized_safe_vietnamese_text() -> None:
    assert ERROR_MESSAGES == {
        "VALIDATION_FAILED": "Dữ liệu không hợp lệ.",
        "PERMISSION_DENIED": "Bạn không có quyền thực hiện thao tác này.",
    }
