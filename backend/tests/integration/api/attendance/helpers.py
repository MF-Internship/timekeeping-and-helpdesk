from __future__ import annotations

from datetime import time
from decimal import Decimal

from rest_framework.test import APIClient

from identity.models import User
from locations.models import Config, Location
from tests.integration.api.identity.helpers import authenticated_client, create_user


def create_reference_data(
    *, location_count: int = 1, location_codes: tuple[str, ...] | None = None
) -> tuple[Config, tuple[Location, ...]]:
    config = Config.objects.create(
        id=1,
        timezone="Asia/Ho_Chi_Minh",
        working_weekdays=[0, 1, 2, 3, 4, 5],
        default_radius_m=Decimal("50"),
        max_radius_m=Decimal("70"),
        max_attendance_accuracy_m=Decimal("25"),
        task_gps_good_accuracy_m=Decimal("25"),
        task_gps_low_accuracy_m=Decimal("100"),
        shift_start=time(8),
        shift_end=time(17),
        late_grace_minutes=15,
        early_checkout_grace_minutes=10,
        late_checkout_grace_minutes=60,
    )
    near_locations = tuple(
        Location.objects.create(
            code=(location_codes[index - 1] if location_codes else f"TEST{index:05d}"),
            name=f"Test Location {index}",
            kind="SHOP",
            address=f"Test Address {index}",
            latitude=Decimal("10.000000000000000"),
            longitude=Decimal("106.000000000000000"),
            radius_m=Decimal("50"),
        )
        for index in range(1, location_count + 1)
    )
    for index in range(location_count + 1, 77):
        Location.objects.create(
            code=f"TEST{index:05d}",
            name=f"Test Location {index}",
            kind="SHOP",
            address=f"Test Address {index}",
            latitude=Decimal("11.000000000000000") + Decimal(index) / Decimal("1000000"),
            longitude=Decimal("107.000000000000000"),
            radius_m=Decimal("50"),
        )
    return config, near_locations


def helpdesk_client(username: str = "attendance-user") -> tuple[APIClient, User]:
    user = create_user(username, "HELPDESK")
    return authenticated_client(user), user


def gps_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "latitude": "10.000000000000000",
        "longitude": "106.000000000000000",
        "accuracy_m": "5.000",
    }
    payload.update(overrides)
    return payload
