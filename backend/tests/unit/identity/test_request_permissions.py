from types import SimpleNamespace

import pytest

from core.errors import IdentityAPIError
from identity.adapters.api.permissions import CanonicalIdentityPermission
from identity.domain.authorization import PermissionAction


def test_action_denial_precedes_forced_password_gate() -> None:
    request = SimpleNamespace(
        user=SimpleNamespace(is_authenticated=True, role="HELPDESK", must_change_password=True)
    )
    view = SimpleNamespace(required_action=PermissionAction.USER_MANAGE)
    with pytest.raises(IdentityAPIError) as caught:
        CanonicalIdentityPermission().has_permission(request, view)
    assert caught.value.error_code == "PERMISSION_DENIED"


def test_authorized_actor_reaches_forced_password_gate() -> None:
    request = SimpleNamespace(
        user=SimpleNamespace(is_authenticated=True, role="MANAGER", must_change_password=True)
    )
    view = SimpleNamespace(required_action=PermissionAction.USER_MANAGE)
    with pytest.raises(IdentityAPIError) as caught:
        CanonicalIdentityPermission().has_permission(request, view)
    assert caught.value.error_code == "PASSWORD_CHANGE_REQUIRED"
