from __future__ import annotations

from dataclasses import replace
from datetime import time
from decimal import Decimal

import pytest

from config.composition import locations_container
from core.errors import IdentityAPIError
from locations.application.config_admin import default_config
from locations.models import Config
from tests.integration.api.identity.helpers import create_user


@pytest.mark.django_db
@pytest.mark.unit
def test_default_config_is_complete_and_repeat_is_rejected() -> None:
    actor = create_user("config-init-manager", "MANAGER")
    candidate = default_config(
        shift_start=time(8),
        shift_end=time(17),
        late_grace_minutes=15,
        early_checkout_grace_minutes=10,
    )
    created = locations_container().config_admin.initialize(actor.pk, candidate)
    assert created.working_weekdays == (0, 1, 2, 3, 4, 5)
    assert created.late_checkout_grace_minutes == 60
    with pytest.raises(IdentityAPIError) as error:
        locations_container().config_admin.initialize(actor.pk, candidate)
    assert error.value.error_code == "VALIDATION_FAILED"
    assert Config.objects.count() == 1


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.parametrize("role", ["LEADER", "HELPDESK"])
def test_config_initialization_denies_non_manager(role: str) -> None:
    actor = create_user(f"config-init-{role.lower()}", role)
    candidate = default_config(
        shift_start=time(8),
        shift_end=time(17),
        late_grace_minutes=0,
        early_checkout_grace_minutes=0,
    )
    with pytest.raises(IdentityAPIError) as error:
        locations_container().config_admin.initialize(actor.pk, candidate)
    assert error.value.error_code == "PERMISSION_DENIED"


@pytest.mark.django_db
@pytest.mark.unit
def test_invalid_nonfinite_initialization_is_atomic() -> None:
    actor = create_user("config-init-invalid", "MANAGER")
    candidate = default_config(
        shift_start=time(8),
        shift_end=time(17),
        late_grace_minutes=0,
        early_checkout_grace_minutes=0,
    )
    invalid = replace(candidate, default_radius_m=Decimal("NaN"))
    with pytest.raises(IdentityAPIError):
        locations_container().config_admin.initialize(actor.pk, invalid)
    assert not Config.objects.exists()


@pytest.mark.django_db
@pytest.mark.unit
def test_inactive_manager_cannot_initialize() -> None:
    actor = create_user("config-init-inactive", "MANAGER", active=False)
    candidate = default_config(
        shift_start=time(8),
        shift_end=time(17),
        late_grace_minutes=0,
        early_checkout_grace_minutes=0,
    )
    with pytest.raises(IdentityAPIError) as error:
        locations_container().config_admin.initialize(actor.pk, candidate)
    assert error.value.error_code == "ACCOUNT_INACTIVE"
    assert not Config.objects.exists()
