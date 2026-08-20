from __future__ import annotations

import pytest

from core.errors import IdentityAPIError
from identity.application.authorization import DjangoAuthorizationGateway
from identity.domain.authorization import JobHealthAccessScope, PermissionAction
from tests.integration.api.identity.helpers import create_user


@pytest.mark.django_db
@pytest.mark.unit
def test_denied_action_precedes_forced_password_and_allowed_action_then_gates() -> None:
    denied = create_user("gateway-denied", "HELPDESK", must_change=True)
    with pytest.raises(IdentityAPIError) as error:
        DjangoAuthorizationGateway().authorize(denied.pk, PermissionAction.LOCATION_MANAGE)
    assert error.value.error_code == "PERMISSION_DENIED"

    manager = create_user("gateway-forced", "MANAGER", must_change=True)
    with pytest.raises(IdentityAPIError) as error:
        DjangoAuthorizationGateway().authorize(manager.pk, PermissionAction.LOCATION_MANAGE)
    assert error.value.error_code == "PASSWORD_CHANGE_REQUIRED"


@pytest.mark.django_db
@pytest.mark.unit
def test_gateway_returns_permission_provenance() -> None:
    manager = create_user("gateway-provenance", "MANAGER")
    result = DjangoAuthorizationGateway().authorize(manager.pk, PermissionAction.LOCATION_VIEW)
    assert result.requested_action is PermissionAction.LOCATION_VIEW
    assert result.allowed is True
    assert result.granted_by is PermissionAction.LOCATION_VIEW


@pytest.mark.django_db
@pytest.mark.unit
def test_gateway_owns_job_health_scope_and_denies_before_issuing_it() -> None:
    manager = create_user("gateway-health-manager", "MANAGER")
    leader = create_user("gateway-health-leader", "LEADER")
    helpdesk = create_user("gateway-health-helpdesk", "HELPDESK")
    gateway = DjangoAuthorizationGateway()

    assert gateway.authorize_job_health(manager.pk) is JobHealthAccessScope.INVESTIGATE
    assert gateway.authorize_job_health(leader.pk) is JobHealthAccessScope.ESCALATE_ONLY
    with pytest.raises(IdentityAPIError) as error:
        gateway.authorize_job_health(helpdesk.pk)
    assert error.value.error_code == "PERMISSION_DENIED"
