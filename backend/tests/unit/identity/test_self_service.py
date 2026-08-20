from dataclasses import replace

import pytest

from identity.application.dto import PasswordChangeRequest, ProfileUpdateRequest
from identity.application.self_service import SelfService
from identity.ports.sessions import IssuedSession, RevocationReason
from tests.unit.identity.helpers import account, dependency_mocks


def test_self_profile_derives_target_from_actor_and_records_minimal_evidence() -> None:
    dependencies, users, _passwords, _sessions, audit = dependency_mocks()
    before = account()
    after = replace(before, full_name="Updated")
    users.get_for_update.return_value = before
    users.save.return_value = after
    result = SelfService(dependencies).update(
        7, ProfileUpdateRequest(full_name="Updated", provided_fields=frozenset({"full_name"}))
    )
    users.get_for_update.assert_called_once_with(7)
    assert result.full_name == "Updated"
    evidence = repr(audit.mock_calls)
    assert "password" not in evidence.casefold() and "refresh" not in evidence.casefold()
    entry = audit.append_audit_entry.call_args.args[0]
    event = audit.append_outbox_event.call_args.args[0]
    assert entry.before == {"full_name": "Worker"}
    assert entry.after == {"full_name": "Updated"}
    assert event.payload == {"user_id": 7, "changed_fields": ["full_name"]}


def test_password_change_validates_before_revoke_and_issues_replacement() -> None:
    dependencies, users, passwords, sessions, audit = dependency_mocks()
    users.get_for_update.return_value = account(must_change=True)
    users.password_hash.return_value = "encoded-old"
    passwords.verify.return_value = True
    passwords.encode.return_value = "encoded-new"
    sessions.revoke_all.return_value = 2
    sessions.issue.return_value = IssuedSession("new-access", "new-refresh")
    result = SelfService(dependencies).change_password(
        7, PasswordChangeRequest("old", "CompliantPassword123!")
    )
    passwords.validate.assert_called_once_with("worker", "CompliantPassword123!")
    sessions.revoke_all.assert_called_once_with(7, RevocationReason.PASSWORD_CHANGE)
    sessions.issue.assert_called_once_with(7)
    assert result.access == "new-access"
    password_event, revocation_event = [
        call.args[0] for call in audit.append_outbox_event.call_args_list
    ]
    assert password_event.payload == {"user_id": 7, "must_change_password": False}
    assert revocation_event.payload == {
        "user_id": 7,
        "reason": "PASSWORD_CHANGE",
        "revoked_refresh_session_count": 2,
    }


def test_wrong_current_password_has_no_mutation_side_effect() -> None:
    dependencies, users, passwords, sessions, audit = dependency_mocks()
    users.get_for_update.return_value = account()
    users.password_hash.return_value = "encoded"
    passwords.verify.return_value = False
    with pytest.raises(ValueError, match="current_password"):
        SelfService(dependencies).change_password(7, PasswordChangeRequest("bad", "new"))
    users.set_password.assert_not_called()
    sessions.revoke_all.assert_not_called()
    audit.append_audit_entry.assert_not_called()


def test_password_change_with_no_live_session_records_only_password_mutation() -> None:
    dependencies, users, passwords, sessions, audit = dependency_mocks()
    users.get_for_update.return_value = account(must_change=True)
    users.password_hash.return_value = "encoded-old"
    passwords.verify.return_value = True
    sessions.revoke_all.return_value = 0
    sessions.issue.return_value = IssuedSession("new-access", "new-refresh")

    SelfService(dependencies).change_password(
        7, PasswordChangeRequest("old", "CompliantPassword123!")
    )

    assert audit.append_audit_entry.call_count == 1
    assert audit.append_outbox_event.call_count == 1
