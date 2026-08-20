from __future__ import annotations

from datetime import time
from decimal import Decimal

import pytest
from django.db import DataError, IntegrityError, connection, transaction

from locations.models import Config


def values(**overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "id": 1,
        "timezone": "Asia/Ho_Chi_Minh",
        "working_weekdays": [0, 1, 2, 3, 4, 5],
        "default_radius_m": Decimal("50"),
        "max_radius_m": Decimal("70"),
        "max_attendance_accuracy_m": Decimal("25"),
        "task_gps_good_accuracy_m": Decimal("25"),
        "task_gps_low_accuracy_m": Decimal("100"),
        "shift_start": time(8),
        "shift_end": time(17),
        "late_grace_minutes": 5,
        "early_checkout_grace_minutes": 5,
        "late_checkout_grace_minutes": 60,
    }
    result.update(overrides)
    return result


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_config_is_singleton_and_database_rejects_invalid_meters_and_order() -> None:
    Config.objects.create(**values())
    for override in (
        {"id": 2},
        {"timezone": "UTC"},
        {"default_radius_m": Decimal("0")},
        {"default_radius_m": Decimal("80"), "max_radius_m": Decimal("70")},
        {"task_gps_good_accuracy_m": Decimal("101")},
        {"shift_start": time(18), "shift_end": time(17)},
        {"late_grace_minutes": -1},
    ):
        with pytest.raises(IntegrityError), transaction.atomic():
            Config.objects.create(**values(**override))


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
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
@pytest.mark.parametrize("invalid", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_every_meter_field_rejects_nonfinite_direct_write(field: str, invalid: Decimal) -> None:
    Config.objects.create(**values())
    with (
        pytest.raises((IntegrityError, DataError)),
        transaction.atomic(),
        connection.cursor() as cursor,
    ):
        cursor.execute(
            f'UPDATE locations_config SET "{field}" = %s WHERE id = 1',
            [str(invalid)],
        )
