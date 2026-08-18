from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command

from audit.models import AuditLog, OutboxEvent
from tests.integration.api.identity.helpers import create_user
from tests.integration.api.locations.helpers import create_config

ROOT = Path(__file__).parents[4]


@pytest.mark.django_db(transaction=True)
@pytest.mark.contract
def test_source_coordinates_never_enter_schema_evidence_or_command_output() -> None:
    create_config()
    actor = create_user("coordinate-safety-manager", "MANAGER")
    center = ROOT / "docs/dia_chi_ttkd.csv"
    first_coordinate = center.read_text(encoding="utf-8-sig").splitlines()[1].split(",")[-2]
    output = StringIO()
    call_command("seed_locations", actor_id=actor.pk, stdout=output)
    serialized = " ".join(
        [Path("contracts/openapi.yaml").read_text(encoding="utf-8"), output.getvalue()]
        + [str(value) for value in AuditLog.objects.values_list("before", "after")]
        + [str(value) for value in OutboxEvent.objects.values_list("payload", flat=True)]
    )
    assert first_coordinate not in serialized
