from datetime import time
from decimal import Decimal

from locations.models import Config, Location


def create_config() -> Config:
    return Config.objects.create(
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


def create_location(code: str = "TEST00001") -> Location:
    return Location.objects.create(
        code=code,
        name="Test Location",
        kind="SHOP",
        address="Test Address",
        latitude=Decimal("10.000000000000000"),
        longitude=Decimal("106.000000000000000"),
        radius_m=Decimal("50"),
    )
