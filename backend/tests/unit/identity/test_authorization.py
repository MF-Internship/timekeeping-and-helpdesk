import pytest

from identity.domain.authorization import (
    ASSIGNABLE_ROLES,
    PERMISSION_IMPLIES,
    ROLE_PERMISSIONS,
    PermissionAction,
    Role,
    decide_permission,
    effective_capabilities,
    is_task_assignee_eligible,
)


@pytest.mark.unit
def test_canonical_policy_shape() -> None:
    assert len(Role) == 3
    assert len(PermissionAction) == 30
    assert len(PERMISSION_IMPLIES) == 5
    assert frozenset({Role.LEADER, Role.HELPDESK}) == ASSIGNABLE_ROLES


@pytest.mark.unit
@pytest.mark.parametrize("role", list(Role))
@pytest.mark.parametrize("action", list(PermissionAction))
def test_every_decision_matches_direct_or_documented_implication(
    role: Role, action: PermissionAction
) -> None:
    decision = decide_permission(role, action)
    direct = action if action in ROLE_PERMISSIONS[role] else None
    implied = next(
        (grant for grant in ROLE_PERMISSIONS[role] if PERMISSION_IMPLIES.get(grant) == action),
        None,
    )
    assert decision.allowed is (direct is not None or implied is not None)
    assert decision.granted_by == (direct or implied)


@pytest.mark.unit
def test_role_specific_denials_are_closed() -> None:
    leader_mutations = {
        action for action in effective_capabilities(Role.LEADER) if action.is_mutation
    }
    assert leader_mutations == {
        PermissionAction.NOTIFICATION_UPDATE_SELF,
        PermissionAction.PUSH_SUBSCRIPTION_MANAGE_SELF,
    }
    for role in Role:
        for action in {
            PermissionAction.NOTIFICATION_VIEW_SELF,
            PermissionAction.NOTIFICATION_UPDATE_SELF,
            PermissionAction.PUSH_SUBSCRIPTION_MANAGE_SELF,
        }:
            assert decide_permission(role, action).granted_by is action
    assert not decide_permission(Role.MANAGER, PermissionAction.ATTENDANCE_CHECK_IN_SELF).allowed
    assert not decide_permission(Role.MANAGER, PermissionAction.ATTENDANCE_CHECK_OUT_SELF).allowed
    assert not decide_permission(Role.HELPDESK, PermissionAction.USER_MANAGE).allowed
    assert not decide_permission(Role.MANAGER, PermissionAction.TASK_CREATE_SELF).allowed
    assert decide_permission(Role.MANAGER, PermissionAction.TASK_CREATE_ASSIGN).allowed
    assert decide_permission(Role.MANAGER, PermissionAction.TASK_COMPLETE_FIELD).allowed


@pytest.mark.unit
def test_task_assignee_eligibility_is_identity_owned_and_closed() -> None:
    assert is_task_assignee_eligible(Role.HELPDESK, is_active=True)
    assert not is_task_assignee_eligible(Role.HELPDESK, is_active=False)
    assert not is_task_assignee_eligible(Role.MANAGER, is_active=True)
    assert not is_task_assignee_eligible(Role.LEADER.value, is_active=True)
