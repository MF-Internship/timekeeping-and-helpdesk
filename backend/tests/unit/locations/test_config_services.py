from __future__ import annotations

from datetime import time
from decimal import Decimal

import pytest

from audit.models import AuditLog, OutboxEvent
from config.composition import locations_container
from core.errors import IdentityAPIError
from locations.models import Location
from tests.integration.api.identity.helpers import create_user
from tests.integration.api.locations.helpers import create_config, create_location


@pytest.mark.django_db
@pytest.mark.unit
def test_config_overlay_noop_warning_cap_and_no_location_rewrite() -> None:
    config = create_config()
    target = create_location()
    actor = create_user("config-service-manager", "MANAGER")
    service = locations_container().config_admin
    same, warnings = service.update(actor.pk, {"late_grace_minutes": 15})
    assert same.late_grace_minutes == 15 and warnings == ()
    assert not AuditLog.objects.exists()
    updated, warnings = service.update(actor.pk, {"max_attendance_accuracy_m": Decimal("60")})
    assert updated.max_attendance_accuracy_m == Decimal("60")
    assert [warning.code.value for warning in warnings] == ["RADIUS_BELOW_ATTENDANCE_ACCURACY"]
    assert warnings[0].related_location_ids == (target.pk,)
    assert warnings[0].related_location_codes == (target.code,)
    assert warnings[0].radius_m == Decimal("50")
    assert warnings[0].threshold_m == Decimal("60")
    target.refresh_from_db()
    assert target.radius_m == 50 and target.version == 1
    assert AuditLog.objects.count() == OutboxEvent.objects.count() == 1
    assert AuditLog.objects.get().after["warning_codes"] == ["RADIUS_BELOW_ATTENDANCE_ACCURACY"]
    assert OutboxEvent.objects.get().payload == {
        "action": "locations.config.updated",
        "config_id": 1,
        "changed_fields": ["max_attendance_accuracy_m"],
        "warning_codes": ["RADIUS_BELOW_ATTENDANCE_ACCURACY"],
        "schema_version": 1,
    }
    Location.objects.filter(pk=target.pk).update(is_active=False)
    with pytest.raises(IdentityAPIError) as error:
        service.update(actor.pk, {"max_radius_m": Decimal("49")})
    assert error.value.error_code == "VALIDATION_FAILED"
    config.refresh_from_db()
    assert config.max_radius_m == 70


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.parametrize(
    "patch,field",
    [
        ({"default_radius_m": Decimal("71")}, "default_radius_m"),
        ({"task_gps_good_accuracy_m": Decimal("101")}, "task_gps_good_accuracy_m"),
        ({"working_weekdays": (0, 0)}, "working_weekdays"),
        ({"shift_start": time(18)}, "shift_start"),
    ],
)
def test_config_cross_field_validation_identifies_the_failing_field(
    patch: dict[str, object], field: str
) -> None:
    create_config()
    actor = create_user(f"config-field-{field}", "MANAGER")
    with pytest.raises(IdentityAPIError) as error:
        locations_container().config_admin.update(actor.pk, patch)
    assert error.value.details == {field: ["Giá trị không hợp lệ."]}


@pytest.mark.django_db
@pytest.mark.unit
def test_config_cap_equality_is_accepted() -> None:
    create_config()
    create_location()
    actor = create_user("config-cap-manager", "MANAGER")
    updated, _warnings = locations_container().config_admin.update(
        actor.pk, {"max_radius_m": Decimal("50")}
    )
    assert updated.max_radius_m == Decimal("50")
