from dataclasses import replace

import pytest

from core.errors import IdentityAPIError
from identity.application.dto import ProfileUpdateRequest, UserCreateRequest
from identity.application.user_admin import UserAdminService
from identity.domain.authorization import Role
from identity.ports.sessions import RevocationReason
from tests.unit.identity.helpers import account, dependency_mocks


def test_create_uses_full_audit_snapshot_and_minimal_event_payload() -> None:
    dependencies, users, passwords, _sessions, audit = dependency_mocks()
    created = account(must_change=True)
    passwords.generate.return_value = "generated"
    passwords.encode.return_value = "encoded"
    users.create.return_value = created

    UserAdminService(dependencies).create(1, UserCreateRequest("worker", "Worker", Role.HELPDESK))

    entry = audit.append_audit_entry.call_args.args[0]
    event = audit.append_outbox_event.call_args.args[0]
    assert entry.after == {
        "user_id": 7,
        "username": "worker",
        "full_name": "Worker",
        "phone": None,
        "email": None,
        "role": "HELPDESK",
        "is_active": True,
        "must_change_password": True,
    }
    assert event.payload == {
        "user_id": 7,
        "role": "HELPDESK",
        "is_active": True,
        "must_change_password": True,
    }


def test_admin_profile_event_contains_names_not_contact_values() -> None:
    dependencies, users, _passwords, _sessions, audit = dependency_mocks()
    before = account()
    after = replace(before, phone="0900")
    users.get_for_update.return_value = before
    users.save.return_value = after

    UserAdminService(dependencies).update_profile(
        1,
        7,
        ProfileUpdateRequest(phone="0900", provided_fields=frozenset({"phone"})),
    )

    entry = audit.append_audit_entry.call_args.args[0]
    event = audit.append_outbox_event.call_args.args[0]
    assert entry.before == {"phone": None}
    assert entry.after == {"phone": "0900"}
    assert event.payload == {"user_id": 7, "changed_fields": ["phone"]}


def test_manager_role_cannot_be_created_or_assigned() -> None:
    dependencies, _users, passwords, _sessions, _audit = dependency_mocks()
    service = UserAdminService(dependencies)
    with pytest.raises(IdentityAPIError) as create_error:
        service.create(1, UserCreateRequest("manager", "Manager", Role.MANAGER))
    with pytest.raises(IdentityAPIError) as role_error:
        service.change_role(1, 7, Role.MANAGER)
    assert create_error.value.error_code == role_error.value.error_code == "PERMISSION_DENIED"
    passwords.generate.assert_not_called()


@pytest.mark.parametrize("operation", ["profile", "role", "status", "reset"])
def test_locked_manager_target_recheck_blocks_every_admin_mutation(operation: str) -> None:
    dependencies, users, _passwords, sessions, audit = dependency_mocks()
    users.get_for_update.return_value = account(role=Role.MANAGER)
    service = UserAdminService(dependencies)
    with pytest.raises(IdentityAPIError) as caught:
        if operation == "profile":
            service.update_profile(1, 7, ProfileUpdateRequest())
        elif operation == "role":
            service.change_role(1, 7, Role.LEADER)
        elif operation == "status":
            service.change_status(1, 7, False)
        else:
            service.reset_password(1, 7)
    assert caught.value.error_code == "PERMISSION_DENIED"
    users.save.assert_not_called()
    sessions.revoke_all.assert_not_called()
    audit.append_audit_entry.assert_not_called()


def test_deactivation_revokes_refresh_and_records_both_mutation_events() -> None:
    dependencies, users, _passwords, sessions, audit = dependency_mocks()
    before = account()
    users.get_for_update.return_value = before
    users.save.return_value = replace(before, is_active=False)
    sessions.revoke_all.return_value = 3
    UserAdminService(dependencies).change_status(1, 7, False)
    sessions.revoke_all.assert_called_once_with(7, RevocationReason.ACCOUNT_DEACTIVATED)
    assert audit.append_audit_entry.call_count == 2
    assert audit.append_outbox_event.call_count == 2
