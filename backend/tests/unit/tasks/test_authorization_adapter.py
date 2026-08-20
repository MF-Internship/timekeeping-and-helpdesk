import ast
from pathlib import Path

import pytest

from config.task_adapters import DjangoTaskAuthorization
from core.error_codes import ACCOUNT_INACTIVE, PASSWORD_CHANGE_REQUIRED, PERMISSION_DENIED
from core.errors import IdentityAPIError
from identity.domain.authorization import PERMISSION_IMPLIES, PermissionAction, Role
from identity.models import User
from tasks.ports.authorization import TaskCreateMode, TaskReadScope, TaskUpdateScope


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("role", "create", "read", "update"),
    [
        (Role.MANAGER, TaskCreateMode.ASSIGN, TaskReadScope.ALL, TaskUpdateScope.ANY),
        (Role.HELPDESK, TaskCreateMode.SELF, TaskReadScope.SELF, TaskUpdateScope.SELF),
    ],
)
def test_adapter_translates_identity_grants_to_task_owned_types(
    role: Role,
    create: TaskCreateMode,
    read: TaskReadScope,
    update: TaskUpdateScope,
) -> None:
    actor = User.objects.create_user(
        username=role.value.lower(),
        password="test-password",
        full_name=role.value,
        role=role.value,
        must_change_password=False,
    )
    adapter = DjangoTaskAuthorization()
    assert adapter.authorize_create(actor.pk) is create
    assert adapter.authorize_read(actor.pk) is read
    assert adapter.authorize_update(actor.pk) is update


@pytest.mark.django_db
def test_leader_is_read_only_and_override_is_exact() -> None:
    leader = User.objects.create_user(
        username="leader-task",
        password="test-password",
        full_name="Leader",
        role=Role.LEADER.value,
        must_change_password=False,
    )
    manager = User.objects.create_user(
        username="manager-task",
        password="test-password",
        full_name="Manager",
        role=Role.MANAGER.value,
        must_change_password=False,
    )
    adapter = DjangoTaskAuthorization()
    assert adapter.authorize_read(leader.pk) is TaskReadScope.ALL
    with pytest.raises(IdentityAPIError, match=PERMISSION_DENIED):
        adapter.authorize_create(leader.pk)
    with pytest.raises(IdentityAPIError, match=PERMISSION_DENIED):
        adapter.authorize_update(leader.pk)
    adapter.authorize_override(manager.pk)
    with pytest.raises(IdentityAPIError, match=PERMISSION_DENIED):
        adapter.authorize_override(leader.pk)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("fields", "code"),
    [
        ({"is_active": False}, ACCOUNT_INACTIVE),
        ({"must_change_password": True}, PASSWORD_CHANGE_REQUIRED),
    ],
)
def test_account_gates_remain_owned_by_identity(fields: dict[str, bool], code: str) -> None:
    account_fields: dict[str, object] = {
        "full_name": "Gate",
        "role": Role.HELPDESK.value,
        "must_change_password": False,
    }
    account_fields.update(fields)
    actor = User.objects.create_user(
        username=f"gate-{code.lower()}",
        password="test-password",
        **account_fields,
    )
    with pytest.raises(IdentityAPIError, match=code):
        DjangoTaskAuthorization().authorize_create(actor.pk)


def test_task_production_code_never_interprets_identity_roles() -> None:
    root = Path(__file__).parents[3] / "tasks"
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        assert "Role" not in names, path
    assert len(PERMISSION_IMPLIES) == 5
    assert set(PERMISSION_IMPLIES) == {
        PermissionAction.TASK_VIEW_ALL,
        PermissionAction.TASK_UPDATE_ANY,
        PermissionAction.ATTENDANCE_VIEW_ALL,
        PermissionAction.REPORT_VIEW_ALL,
        PermissionAction.PHOTO_VIEW_ALL,
    }
