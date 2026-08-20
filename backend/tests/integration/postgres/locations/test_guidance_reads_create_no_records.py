from __future__ import annotations

import pytest

from attendance.models import Attendance, AttendanceAttempt, AttendanceSession
from audit.models import AuditLog, OutboxEvent
from tests.integration.api.identity.helpers import authenticated_client, create_user
from tests.integration.api.locations.helpers import create_config, create_location

READ_ROUNDS = 3


def _record_counts() -> dict[str, int]:
    return {
        "attendance": Attendance.objects.count(),
        "session": AttendanceSession.objects.count(),
        "attempt": AttendanceAttempt.objects.count(),
        "audit": AuditLog.objects.count(),
        "outbox": OutboxEvent.objects.count(),
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_repeated_guidance_reference_reads_write_nothing_at_all() -> None:
    """Scenario O — guidance is a read, and a read leaves no trace.

    The two operations the on-device preview consumes are exercised repeatedly by
    an authenticated actor. Neither may produce an attendance record of any kind,
    because the preview is not a punch (FR-031, SC-003), and neither may produce
    an audit or outbox row, because nothing changed to record (FR-031, SC-003).
    Counts are compared against the state before the reads rather than against
    zero, so an unrelated fixture write could not mask a new row.
    """
    create_config()
    create_location()
    api = authenticated_client(create_user("guidance-reader", "HELPDESK"))
    before = _record_counts()

    for _ in range(READ_ROUNDS):
        assert api.get("/api/v1/locations/").status_code == 200
        assert api.get("/api/v1/config/").status_code == 200

    assert _record_counts() == before
