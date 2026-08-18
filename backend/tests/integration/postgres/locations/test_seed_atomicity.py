from __future__ import annotations

from pathlib import Path

import pytest

from audit.models import AuditLog, OutboxEvent
from config.composition import locations_container
from core.errors import IdentityAPIError
from locations.adapters.source_data.csv_source import SourceDataError
from locations.models import Config, Location
from tests.integration.api.identity.helpers import create_user
from tests.integration.api.locations.helpers import create_config

ROOT = Path(__file__).parents[5]


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
@pytest.mark.parametrize("recorder_method", ["append_audit_entry", "append_outbox_event"])
def test_seed_rolls_back_locations_and_evidence_when_recorder_fails(
    monkeypatch: pytest.MonkeyPatch, recorder_method: str
) -> None:
    create_config()
    actor = create_user("seed-rollback-manager", "MANAGER")
    service = locations_container().seed
    monkeypatch.setattr(
        service._dependencies.audit,
        recorder_method,
        lambda event: (_ for _ in ()).throw(RuntimeError("injected")),
    )
    with pytest.raises(RuntimeError, match="injected"):
        service.seed(actor.pk, ROOT / "docs/dia_chi_ttkd.csv", ROOT / "docs/dia_chi_cua_hang.csv")
    assert Location.objects.count() == AuditLog.objects.count() == OutboxEvent.objects.count() == 0


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_seed_preflight_and_missing_config_leave_no_partial_state(tmp_path: Path) -> None:
    actor = create_user("seed-preflight-manager", "MANAGER")
    bad = tmp_path / "bad.csv"
    bad.write_text("wrong\n", encoding="utf-8")
    with pytest.raises(SourceDataError):
        locations_container().seed.seed(actor.pk, bad, ROOT / "docs/dia_chi_cua_hang.csv")
    assert not Location.objects.exists() and not AuditLog.objects.exists()
    with pytest.raises(IdentityAPIError) as error:
        locations_container().seed.seed(
            actor.pk, ROOT / "docs/dia_chi_ttkd.csv", ROOT / "docs/dia_chi_cua_hang.csv"
        )
    assert error.value.error_code == "NOT_FOUND"
    assert not Location.objects.exists() and not OutboxEvent.objects.exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_seed_rejects_domain_invalid_locked_config_before_writes() -> None:
    create_config()
    Config.objects.filter(pk=1).update(working_weekdays=[0, 0])
    actor = create_user("seed-invalid-config-manager", "MANAGER")
    with pytest.raises(IdentityAPIError) as error:
        locations_container().seed.seed(
            actor.pk, ROOT / "docs/dia_chi_ttkd.csv", ROOT / "docs/dia_chi_cua_hang.csv"
        )
    assert error.value.error_code == "VALIDATION_FAILED"
    assert not Location.objects.exists() and not AuditLog.objects.exists()
    assert not OutboxEvent.objects.exists()
