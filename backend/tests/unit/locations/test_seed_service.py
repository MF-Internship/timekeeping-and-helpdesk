from __future__ import annotations

from dataclasses import replace
from datetime import time
from decimal import Decimal
from pathlib import Path

import pytest

from audit.models import AuditLog, OutboxEvent
from config.composition import locations_container
from core.errors import IdentityAPIError
from locations.application.config_admin import default_config
from locations.application.seed import _seed_overlap_warnings, _validate_seed_config
from locations.domain.locations import LocationKind, LocationSnapshot
from locations.models import Location
from tests.integration.api.identity.helpers import create_user
from tests.integration.api.locations.helpers import create_config, create_location

ROOT = Path(__file__).parents[4]


@pytest.mark.unit
def test_seed_config_validation_reports_domain_field_before_persistence() -> None:
    invalid = replace(
        default_config(
            shift_start=time(8),
            shift_end=time(17),
            late_grace_minutes=15,
            early_checkout_grace_minutes=10,
        ),
        working_weekdays=(0, 0),
    )
    with pytest.raises(IdentityAPIError) as error:
        _validate_seed_config(invalid)
    assert error.value.error_code == "VALIDATION_FAILED"
    assert error.value.details == {"working_weekdays": ["Giá trị không hợp lệ."]}


@pytest.mark.unit
def test_seed_overlap_warning_keeps_duplicate_coordinates_as_separate_safe_identities() -> None:
    def snapshot(location_id: int, code: str) -> LocationSnapshot:
        return LocationSnapshot(
            location_id,
            code,
            code,
            LocationKind.SHOP,
            None,
            None,
            "redacted",
            Decimal("10"),
            Decimal("106"),
            Decimal("50"),
            True,
            1,
        )

    warnings = _seed_overlap_warnings((snapshot(1, "SHOP1"), snapshot(2, "SHOP2")))
    assert len(warnings) == 1
    assert warnings[0].code.value == "GEOFENCE_OVERLAP"
    assert warnings[0].related_location_ids == (1, 2)
    assert warnings[0].related_location_codes == ("SHOP1", "SHOP2")


@pytest.mark.django_db
@pytest.mark.unit
def test_seed_rejects_unexpected_identity_without_changing_code_or_evidence() -> None:
    create_config()
    unexpected = create_location("UNEXPECTED")
    actor = create_user("seed-service-manager", "MANAGER")
    with pytest.raises(IdentityAPIError) as error:
        locations_container().seed.seed(
            actor.pk, ROOT / "docs/dia_chi_ttkd.csv", ROOT / "docs/dia_chi_cua_hang.csv"
        )
    assert error.value.error_code == "VALIDATION_FAILED"
    unexpected.refresh_from_db()
    assert unexpected.code == "UNEXPECTED"
    assert Location.objects.count() == 1
    assert not AuditLog.objects.exists() and not OutboxEvent.objects.exists()
