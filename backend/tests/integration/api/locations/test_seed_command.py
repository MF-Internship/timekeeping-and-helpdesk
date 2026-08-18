from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from locations.models import Location
from tests.integration.api.identity.helpers import create_user
from tests.integration.api.locations.helpers import create_config


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_seed_command_authorizes_manager_and_output_has_no_coordinates() -> None:
    create_config()
    actor = create_user("seed-command-manager", "MANAGER")
    output = StringIO()
    call_command("seed_locations", actor_id=actor.pk, stdout=output)
    text = output.getvalue()
    assert "changed=76 total=76" in text
    assert "warnings=GEOFENCE_OVERLAP" in text
    assert "10." not in text and "106." not in text
    assert Location.objects.count() == 76


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_seed_command_denies_non_manager_without_side_effect() -> None:
    create_config()
    actor = create_user("seed-command-helpdesk", "HELPDESK")
    with pytest.raises(CommandError, match="PERMISSION_DENIED"):
        call_command("seed_locations", actor_id=actor.pk)
    assert not Location.objects.exists()
