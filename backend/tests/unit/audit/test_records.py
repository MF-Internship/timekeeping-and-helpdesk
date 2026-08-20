from enum import StrEnum

import pytest

from audit.domain.records import AuditAction, AuditEntry, IdentityEventType, OutboxRecord
from core.event_payload import ProtectedPayloadError


@pytest.mark.unit
def test_records_are_immutable_and_use_closed_vocabularies() -> None:
    entry = AuditEntry(1, AuditAction.USER_CREATED, "User", "2", {}, {"role": "HELPDESK"})
    with pytest.raises(AttributeError):
        entry.actor_id = 3  # type: ignore[misc]
    assert len(AuditAction) == 12
    assert len(IdentityEventType) == 7


@pytest.mark.unit
def test_secret_payload_is_rejected_with_path_only() -> None:
    with pytest.raises(ProtectedPayloadError, match=r"\$\.nested\.password"):
        OutboxRecord(IdentityEventType.USER_CREATED, "User", "2", {"nested": {"password": "x"}})


@pytest.mark.unit
def test_url_value_is_rejected_without_echoing_the_value() -> None:
    with pytest.raises(ProtectedPayloadError) as raised:
        AuditEntry(
            1,
            AuditAction.USER_PROFILE_UPDATED,
            "User",
            "2",
            {},
            {"diagnostic": "private://credential"},
        )

    assert raised.value.path == "$.diagnostic"
    assert "credential" not in str(raised.value)


@pytest.mark.unit
def test_owner_defined_closed_enum_is_accepted_without_changing_identity_vocabulary() -> None:
    class LocationEvent(StrEnum):
        LOCATION_UPDATED = "location.updated"

    record = OutboxRecord(LocationEvent.LOCATION_UPDATED, "Location", "7", {"version": 2})
    assert record.event_type is LocationEvent.LOCATION_UPDATED
    assert len(IdentityEventType) == 7


@pytest.mark.unit
def test_attendance_audit_actions_are_closed_additions() -> None:
    assert AuditAction.ATTENDANCE_CHECK_IN_CREATED.value == "attendance.check_in.created"
    assert AuditAction.ATTENDANCE_CHECK_OUT_CREATED.value == "attendance.check_out.created"
    assert len(AuditAction) == 12


@pytest.mark.unit
def test_task_audit_actions_are_closed_additions() -> None:
    assert AuditAction.TASK_COMPLETION_OVERRIDDEN.value == "task.completion.overridden"
    assert AuditAction.TASK_COMPLETION_FIELD_EVIDENCE.value == "task.completion.field_evidence"
    assert AuditAction.TASK_SELF_DELETED.value == "task.self_deleted"
    assert [action for action in AuditAction if action.value.startswith("task.")] == [
        AuditAction.TASK_COMPLETION_OVERRIDDEN,
        AuditAction.TASK_COMPLETION_FIELD_EVIDENCE,
        AuditAction.TASK_SELF_DELETED,
    ]
