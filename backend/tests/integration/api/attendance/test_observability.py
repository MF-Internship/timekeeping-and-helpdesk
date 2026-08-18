import pytest

from audit.models import AuditLog, OutboxEvent
from tests.integration.api.attendance.helpers import (
    create_reference_data,
    gps_payload,
    helpdesk_client,
)

pytestmark = pytest.mark.django_db


def test_success_audit_is_exact_and_rejections_create_no_audit_or_outbox() -> None:
    create_reference_data()
    client, user = helpdesk_client("attendance-observability")
    assert (
        client.post("/api/v1/attendance/check-in", gps_payload(), format="json").status_code == 201
    )
    assert (
        client.post("/api/v1/attendance/check-out", gps_payload(), format="json").status_code == 201
    )
    entries = list(AuditLog.objects.filter(actor=user).order_by("id"))
    assert [item.action for item in entries] == [
        "attendance.check_in.created",
        "attendance.check_out.created",
    ]
    for entry in entries:
        assert entry.target_type == "Attendance" and entry.before == {}
        assert entry.target_id == str(entry.after["attendance_id"])
        assert set(entry.after) == {
            "attendance_id",
            "kind",
            "work_date",
            "location_id",
            "session_id",
        }
    before = len(entries)
    client.post("/api/v1/attendance/check-out", gps_payload(), format="json")
    assert AuditLog.objects.filter(actor=user).count() == before
    assert not OutboxEvent.objects.exists()
