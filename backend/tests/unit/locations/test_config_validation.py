from dataclasses import replace
from datetime import time
from decimal import Decimal

import pytest

from locations.application.config_admin import default_config
from locations.domain.config import METER_FIELDS, validate_config


def valid_config():
    return default_config(
        shift_start=time(8),
        shift_end=time(17),
        late_grace_minutes=15,
        early_checkout_grace_minutes=10,
    )


@pytest.mark.parametrize("field", METER_FIELDS)
@pytest.mark.parametrize(
    "value",
    [
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
        Decimal("0"),
        Decimal("-1"),
    ],
)
def test_every_nonfinite_or_nonpositive_meter_value_is_rejected(field: str, value: Decimal) -> None:
    with pytest.raises(ValueError):
        validate_config(replace(valid_config(), **{field: value}))


def test_schedule_weekday_and_ordering_invariants() -> None:
    for candidate in (
        replace(valid_config(), working_weekdays=(0, 0)),
        replace(valid_config(), working_weekdays=(7,)),
        replace(valid_config(), shift_start=time(18)),
        replace(valid_config(), default_radius_m=Decimal("71")),
        replace(valid_config(), task_gps_good_accuracy_m=Decimal("101")),
    ):
        with pytest.raises(ValueError):
            validate_config(candidate)
