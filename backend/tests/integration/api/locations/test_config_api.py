from decimal import Decimal

import pytest

from audit.models import AuditLog, OutboxEvent
from tests.integration.api.identity.helpers import authenticated_client, create_user, manager_client
from tests.integration.api.locations.helpers import create_config, create_location


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_config_read_manage_noop_and_active_inactive_cap_rejection() -> None:
    create_config()
    active = create_location("ACTIVE")
    inactive = create_location("INACTIVE")
    inactive.is_active = False
    inactive.radius_m = Decimal("65")
    inactive.save(update_fields=["is_active", "radius_m"])
    for role in ("LEADER", "MANAGER", "HELPDESK"):
        api = authenticated_client(create_user(f"config-{role.lower()}", role))
        assert api.get("/api/v1/config/").status_code == 200
    api, _manager = manager_client("config-manager-update")
    noop = api.patch("/api/v1/config/", {"max_radius_m": "70.000"}, format="json")
    assert noop.status_code == 200
    assert AuditLog.objects.count() == OutboxEvent.objects.count() == 0
    rejected = api.patch("/api/v1/config/", {"max_radius_m": "64.000"}, format="json")
    assert rejected.status_code == 400
    assert inactive.code in rejected.json()["details"]["max_radius_m"]
    assert active.radius_m == Decimal("50")


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_config_non_manager_bad_body_is_denied_before_validation() -> None:
    create_config()
    api = authenticated_client(create_user("config-denied", "HELPDESK"))
    response = api.patch("/api/v1/config/", {"max_radius_m": "NaN"}, format="json")
    assert response.status_code == 403
    assert response.json()["error_code"] == "PERMISSION_DENIED"


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
@pytest.mark.parametrize(
    "payload,field",
    [
        ({"default_radius_m": "71"}, "default_radius_m"),
        ({"task_gps_good_accuracy_m": "101"}, "task_gps_good_accuracy_m"),
        ({"working_weekdays": [0, 0]}, "working_weekdays"),
        ({"shift_start": "18:00", "shift_end": "17:00"}, "shift_start"),
        ({"shift_start": "17:00", "shift_end": "17:00"}, "shift_start"),
        ({"late_grace_minutes": -1}, "late_grace_minutes"),
        ({"max_attendance_accuracy_m": "0"}, "max_attendance_accuracy_m"),
        ({"max_attendance_accuracy_m": "Infinity"}, "max_attendance_accuracy_m"),
    ],
)
def test_config_invalid_complete_candidate_has_field_feedback_and_no_evidence(
    payload: dict[str, object], field: str
) -> None:
    config = create_config()
    api, _manager = manager_client(f"config-invalid-{field}")
    response = api.patch("/api/v1/config/", payload, format="json")
    assert response.status_code == 400
    assert field in response.json()["details"]
    config.refresh_from_db()
    assert config.max_radius_m == Decimal("70")
    assert not AuditLog.objects.exists() and not OutboxEvent.objects.exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
@pytest.mark.parametrize(
    "field",
    [
        "default_radius_m",
        "max_radius_m",
        "max_attendance_accuracy_m",
        "task_gps_good_accuracy_m",
        "task_gps_low_accuracy_m",
    ],
)
@pytest.mark.parametrize("invalid", ["NaN", "Infinity", "-Infinity", "0", "-1"])
def test_every_invalid_meter_api_value_has_owning_field_and_no_side_effects(
    field: str, invalid: str
) -> None:
    config = create_config()
    original = getattr(config, field)
    api, _manager = manager_client("config-meter-boundary")

    response = api.patch("/api/v1/config/", {field: invalid}, format="json")

    assert response.status_code == 400
    assert response.json()["error_code"] == "VALIDATION_FAILED"
    assert field in response.json()["details"]
    config.refresh_from_db()
    assert getattr(config, field) == original
    assert not AuditLog.objects.exists() and not OutboxEvent.objects.exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
@pytest.mark.parametrize(
    "field",
    ["late_grace_minutes", "early_checkout_grace_minutes", "late_checkout_grace_minutes"],
)
def test_every_negative_grace_api_value_has_owning_field_and_no_side_effects(field: str) -> None:
    config = create_config()
    original = getattr(config, field)
    api, _manager = manager_client("config-grace-boundary")

    response = api.patch("/api/v1/config/", {field: -1}, format="json")

    assert response.status_code == 400
    assert response.json()["error_code"] == "VALIDATION_FAILED"
    assert field in response.json()["details"]
    config.refresh_from_db()
    assert getattr(config, field) == original
    assert not AuditLog.objects.exists() and not OutboxEvent.objects.exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_config_manager_state_change_is_persisted_with_evidence() -> None:
    create_config()
    api, _manager = manager_client("config-state-change")
    response = api.patch("/api/v1/config/", {"late_grace_minutes": 20}, format="json")
    assert response.status_code == 200
    assert response.json()["config"]["late_grace_minutes"] == 20
    assert AuditLog.objects.count() == OutboxEvent.objects.count() == 1
