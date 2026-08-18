from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from audit.models import AuditLog, OutboxEvent
from config.composition import locations_container
from locations.models import Config, Location
from tests.integration.api.identity.helpers import create_user
from tests.integration.api.locations.helpers import create_config, create_location

ROOT = Path(__file__).parents[5]


def _seed_ready_state(label: str) -> tuple[int, int]:
    create_config()
    actor = create_user(f"readiness-{label}-manager", "MANAGER")
    locations_container().seed.seed(
        actor.pk, ROOT / "docs/dia_chi_ttkd.csv", ROOT / "docs/dia_chi_cua_hang.csv"
    )
    return AuditLog.objects.count(), OutboxEvent.objects.count()


def _assert_readiness_failure(expected: str, evidence_before: tuple[int, int]) -> None:
    with pytest.raises(CommandError) as error:
        call_command("verify_location_reference_ready")
    assert str(error.value) == f"reference data not ready: {expected}"
    assert (AuditLog.objects.count(), OutboxEvent.objects.count()) == evidence_before


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_readiness_requires_complete_config_and_exact_canonical_data_without_mutation() -> None:
    with pytest.raises(CommandError, match="config_missing"):
        call_command("verify_location_reference_ready")
    create_config()
    actor = create_user("readiness-manager", "MANAGER")
    locations_container().seed.seed(
        actor.pk, ROOT / "docs/dia_chi_ttkd.csv", ROOT / "docs/dia_chi_cua_hang.csv"
    )
    before = (AuditLog.objects.count(), OutboxEvent.objects.count())
    output = StringIO()
    call_command("verify_location_reference_ready", stdout=output)
    assert "ready" in output.getvalue().lower()
    assert (AuditLog.objects.count(), OutboxEvent.objects.count()) == before
    Location.objects.filter(code="HCM020129").update(latitude="10.000000000000000")
    with pytest.raises(CommandError, match="location_drift:HCM020129") as error:
        call_command("verify_location_reference_ready")
    assert "10.000" not in str(error.value)
    assert (AuditLog.objects.count(), OutboxEvent.objects.count()) == before


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.parametrize(
    "field,value",
    [("is_active", False), ("radius_m", "49.000")],
)
def test_readiness_rejects_active_and_default_radius_drift(field: str, value: object) -> None:
    before = _seed_ready_state(field)
    Location.objects.filter(code="HCM020129").update(**{field: value})
    drifted = getattr(Location.objects.get(code="HCM020129"), field)
    _assert_readiness_failure("location_drift:HCM020129", before)
    assert getattr(Location.objects.get(code="HCM020129"), field) == drifted


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_readiness_rejects_domain_invalid_config_without_repair() -> None:
    before = _seed_ready_state("invalid-config")
    Config.objects.filter(pk=1).update(working_weekdays=[0, 0])

    _assert_readiness_failure("config_invalid", before)
    assert Config.objects.get(pk=1).working_weekdays == [0, 0]


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", "BUSINESS_CENTER"),
        ("parent_id", None),
        ("latitude", "10.000000000000000"),
    ],
)
def test_readiness_rejects_kind_hierarchy_and_coordinate_drift_without_repair(
    field: str, value: object
) -> None:
    before = _seed_ready_state(f"drift-{field}")
    Location.objects.filter(code="HCM020129").update(**{field: value})
    drifted = getattr(Location.objects.get(code="HCM020129"), field)

    _assert_readiness_failure("location_drift:HCM020129", before)
    assert getattr(Location.objects.get(code="HCM020129"), field) == drifted


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.parametrize("change", ["missing", "extra"])
def test_readiness_rejects_missing_or_extra_codes_and_count_without_repair(change: str) -> None:
    before = _seed_ready_state(change)
    if change == "missing":
        Location.objects.get(code="HCM020129").delete()
    else:
        create_location("EXTRA0001")

    _assert_readiness_failure("location_count,location_codes", before)
    assert Location.objects.filter(code="HCM020129").exists() is (change == "extra")
    assert Location.objects.filter(code="EXTRA0001").exists() is (change == "extra")
