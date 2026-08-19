from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from attendance.domain.reconciliation import ReconciliationOutcome


class Service:
    def __init__(self, status: str) -> None:
        self.status = status

    def run(self) -> ReconciliationOutcome:
        return ReconciliationOutcome(
            99,
            self.status,
            3,
            2,
            2,
            None if self.status == "SUCCEEDED" else "SESSION_PROCESSING_FAILED",
        )


def test_command_has_no_date_or_repair_arguments_and_zero_work_exits_zero(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "attendance.management.commands.reconcile_missing_checkouts.reconciliation_service",
        lambda: Service("SUCCEEDED"),
    )
    output = StringIO()
    call_command("reconcile_missing_checkouts", stdout=output)
    value = output.getvalue()
    assert "status=SUCCEEDED" in value
    assert "run_id" not in value and "99" not in value


@pytest.mark.parametrize("status", ["PARTIAL_FAILED", "FAILED"])
def test_failure_status_has_nonzero_command_semantics_and_sanitized_output(
    monkeypatch,
    status: str,  # type: ignore[no-untyped-def]
) -> None:
    monkeypatch.setattr(
        "attendance.management.commands.reconcile_missing_checkouts.reconciliation_service",
        lambda: Service(status),
    )
    with pytest.raises(CommandError) as caught:
        call_command("reconcile_missing_checkouts")
    message = str(caught.value)
    assert status in message
    assert all(
        term not in message.lower() for term in ("session_id", "user_id", "gps", "traceback")
    )
