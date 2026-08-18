import pytest

from tests.unit.attendance.test_commands import COMMAND, service


@pytest.mark.parametrize("failure", ["writer", "infrastructure"])
def test_failure_telemetry_contains_no_sensitive_attendance_evidence(
    failure: str, caplog: pytest.LogCaptureFixture
) -> None:
    commands, _repository, _attempts, _audit = service(
        writer_fails=failure == "writer", reference_fails=failure == "infrastructure"
    )
    if failure == "infrastructure":
        with pytest.raises(RuntimeError):
            commands.check_in(42, COMMAND)
    else:
        commands.check_in(42, COMMAND)
    for forbidden in ("10", "106", "accuracy", "device", "request_ip", "maps"):
        assert forbidden not in caplog.text
