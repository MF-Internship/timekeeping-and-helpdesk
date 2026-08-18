import pytest

from audit.domain.records import AuditAction, AuditEntry, IdentityEventType, OutboxRecord
from core.event_payload import ProtectedPayloadError


@pytest.mark.unit
def test_records_are_immutable_and_use_closed_vocabularies() -> None:
    entry = AuditEntry(1, AuditAction.USER_CREATED, "User", "2", {}, {"role": "HELPDESK"})
    with pytest.raises(AttributeError):
        entry.actor_id = 3  # type: ignore[misc]
    assert len(AuditAction) == 7
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
