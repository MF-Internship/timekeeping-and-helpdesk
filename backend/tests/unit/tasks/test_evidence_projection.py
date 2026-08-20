from datetime import UTC, datetime

from tasks.adapters.api.serializers import _update_evidence_payload
from tasks.domain.tasks import LocationDisplay, TaskStatus, TaskUpdateSnapshot


def update(**overrides: object) -> TaskUpdateSnapshot:
    values: dict[str, object] = {
        "id": 1,
        "task_id": 7,
        "user_id": 9,
        "status": TaskStatus.COMPLETED,
        "recorded_at": datetime(2026, 8, 20, tzinfo=UTC),
        "note": None,
        "block_reason": None,
        "completion_method": None,
        "completion_note": None,
        "captured_latitude": "10.123456789012345",
        "captured_longitude": "106.987654321098765",
        "actual_location_id": 3,
        "actual_location": LocationDisplay(3, "HCM", "Kho Quận 7", True, "12 Nguyễn Văn Linh"),
    }
    values.update(overrides)
    return TaskUpdateSnapshot(**values)  # type: ignore[arg-type]


def test_address_uses_only_the_selected_location_snapshot() -> None:
    payload = _update_evidence_payload(update())
    assert payload["resolved_address"] == "Kho Quận 7 — 12 Nguyễn Văn Linh"
    assert payload["actual_location_id"] == 3


def test_address_is_null_without_a_resolved_location() -> None:
    payload = _update_evidence_payload(update(actual_location=None, actual_location_id=None))
    assert payload["resolved_address"] is None


def test_maps_url_preserves_exact_stored_capture_coordinates() -> None:
    payload = _update_evidence_payload(update())
    assert payload["maps_url"] == (
        "https://www.google.com/maps?q=10.123456789012345%2C106.987654321098765"
    )


def test_maps_url_is_null_without_a_complete_capture_pair() -> None:
    assert _update_evidence_payload(update(captured_longitude=None))["maps_url"] is None
