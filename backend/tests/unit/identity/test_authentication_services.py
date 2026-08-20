import pytest

from core.errors import IdentityAPIError
from identity.application.authentication import AuthenticationService
from identity.ports.push_subscriptions import PushSubscriptionRevocationReason
from identity.ports.sessions import IssuedSession, RevocationReason
from tests.unit.identity.helpers import account, dependency_mocks


def test_login_is_non_enumerating_and_issues_only_after_password_verification() -> None:
    dependencies, users, passwords, sessions, _audit = dependency_mocks()
    users.get_by_username_for_update.return_value = None
    with pytest.raises(IdentityAPIError) as missing:
        AuthenticationService(dependencies).login("missing", "wrong")
    assert missing.value.error_code == "INVALID_CREDENTIALS"
    sessions.issue.assert_not_called()

    users.get_by_username_for_update.return_value = account()
    users.password_hash.return_value = "encoded"
    passwords.verify.return_value = True
    sessions.issue.return_value = IssuedSession("access", "refresh")
    issued, current, capabilities = AuthenticationService(dependencies).login(
        " worker ", "password"
    )
    assert issued.access == "access" and current.username == "worker"
    assert capabilities
    users.get_by_username_for_update.assert_called_with("worker")


def test_refresh_rechecks_state_before_rotation_and_logout_revokes_globally() -> None:
    dependencies, users, _passwords, sessions, audit = dependency_mocks()
    sessions.refresh_owner.return_value = 7
    users.get_for_update.return_value = account(active=False)
    with pytest.raises(IdentityAPIError) as inactive:
        AuthenticationService(dependencies).refresh("refresh")
    assert inactive.value.error_code == "ACCOUNT_INACTIVE"
    sessions.rotate.assert_not_called()

    users.get_for_update.return_value = account()
    sessions.revoke_all.return_value = 2
    AuthenticationService(dependencies).logout(7)
    sessions.revoke_all.assert_called_once_with(7, RevocationReason.LOGOUT)
    dependencies.push_subscriptions.revoke_all.assert_called_once_with(
        7, PushSubscriptionRevocationReason.LOGOUT
    )
    assert audit.append_audit_entry.called and audit.append_outbox_event.called
    entry = audit.append_audit_entry.call_args.args[0]
    event = audit.append_outbox_event.call_args.args[0]
    assert entry.before == {"active_refresh_sessions": 2}
    assert entry.after == {
        "active_refresh_sessions": 0,
        "reason": "LOGOUT",
        "revoked_refresh_session_count": 2,
    }
    assert event.payload == {
        "user_id": 7,
        "reason": "LOGOUT",
        "revoked_refresh_session_count": 2,
    }


def test_logout_zero_session_revocation_has_no_evidence() -> None:
    dependencies, users, _passwords, sessions, audit = dependency_mocks()
    users.get_for_update.return_value = account()
    sessions.revoke_all.return_value = 0

    AuthenticationService(dependencies).logout(7)

    sessions.refresh_owner.assert_not_called()
    sessions.revoke_all.assert_called_once_with(7, RevocationReason.LOGOUT)
    dependencies.push_subscriptions.revoke_all.assert_called_once_with(
        7, PushSubscriptionRevocationReason.LOGOUT
    )
    audit.append_audit_entry.assert_not_called()
    audit.append_outbox_event.assert_not_called()
