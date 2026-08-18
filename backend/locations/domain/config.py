from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import time
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class ConfigSnapshot:
    id: int
    timezone: str
    working_weekdays: tuple[int, ...]
    default_radius_m: Decimal
    max_radius_m: Decimal
    max_attendance_accuracy_m: Decimal
    task_gps_good_accuracy_m: Decimal
    task_gps_low_accuracy_m: Decimal
    shift_start: time
    shift_end: time
    late_grace_minutes: int
    early_checkout_grace_minutes: int
    late_checkout_grace_minutes: int


METER_FIELDS = (
    "default_radius_m",
    "max_radius_m",
    "max_attendance_accuracy_m",
    "task_gps_good_accuracy_m",
    "task_gps_low_accuracy_m",
)


def validate_config(config: ConfigSnapshot) -> None:
    if config.id != 1 or config.timezone != "Asia/Ho_Chi_Minh":
        raise ValueError("config")
    _validate_meter_fields(config)
    _validate_schedule(config)


def _validate_meter_fields(config: ConfigSnapshot) -> None:
    for field in METER_FIELDS:
        value = getattr(config, field)
        if not value.is_finite() or value <= 0:
            raise ValueError(field)
    if config.default_radius_m > config.max_radius_m:
        raise ValueError("default_radius_m")
    if config.task_gps_good_accuracy_m > config.task_gps_low_accuracy_m:
        raise ValueError("task_gps_good_accuracy_m")


def _validate_schedule(config: ConfigSnapshot) -> None:
    weekdays = config.working_weekdays
    if len(set(weekdays)) != len(weekdays) or any(day < 0 or day > 6 for day in weekdays):
        raise ValueError("working_weekdays")
    if config.shift_start >= config.shift_end:
        raise ValueError("shift_start")
    for field in (
        "late_grace_minutes",
        "early_checkout_grace_minutes",
        "late_checkout_grace_minutes",
    ):
        value = getattr(config, field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(field)


def overlay_config(config: ConfigSnapshot, patch: dict[str, Any]) -> ConfigSnapshot:
    candidate = replace(config, **patch)
    validate_config(candidate)
    return candidate
