from identity.domain.authorization import (
    PERMISSION_IMPLIES,
    PermissionAction,
    Role,
    decide_permission,
)


def test_direct_and_implied_permission_decisions_preserve_provenance() -> None:
    direct = decide_permission(Role.HELPDESK, PermissionAction.TASK_VIEW_SELF)
    implied = decide_permission(Role.LEADER, PermissionAction.TASK_VIEW_SELF)
    denied = decide_permission(Role.HELPDESK, PermissionAction.USER_VIEW)
    assert direct.allowed and direct.granted_by is PermissionAction.TASK_VIEW_SELF
    assert implied.allowed and implied.granted_by is PermissionAction.TASK_VIEW_ALL
    assert not denied.allowed and denied.granted_by is None


def test_only_the_five_canonical_implications_open_an_action_gate() -> None:
    assert len(PERMISSION_IMPLIES) == 5
    assert len(set(PERMISSION_IMPLIES.values())) == 5
