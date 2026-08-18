from __future__ import annotations

import json
import math
import os
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.db import transaction  # noqa: E402

from attendance.application.dto import AttendanceCommand  # type: ignore[import-untyped] # noqa: E402
from config.composition import attendance_container  # type: ignore[import-untyped] # noqa: E402
from identity.models import User  # type: ignore[import-untyped] # noqa: E402
from locations.domain.geofence import haversine_distance_m  # type: ignore[import-untyped] # noqa: E402
from locations.domain.locations import Coordinates  # type: ignore[import-untyped] # noqa: E402
from locations.models import Config, Location  # type: ignore[import-untyped] # noqa: E402

TRIALS = 100
USER_COUNT = 50
BASELINE_SESSIONS = 20
TARGET_SECONDS = 2


def main() -> int:
    with transaction.atomic():
        location = _unique_location()
        users = _users()
        service = attendance_container()
        command = AttendanceCommand(
            location.latitude,
            location.longitude,
            Decimal("0.000"),
            selected_location_id=None,
        )
        _seed_sessions(service, users[0].pk, command)
        durations = _measure(service, users[0].pk, command)
        transaction.set_rollback(True)
    result = _result(durations)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 1


def _unique_location() -> Location:
    if Config.objects.count() != 1 or Location.objects.count() != 76:
        raise RuntimeError("attendance reference data is not ready")
    locations = tuple(Location.objects.filter(is_active=True).order_by("code"))
    for candidate in locations:
        point = Coordinates(candidate.latitude, candidate.longitude)
        matches = sum(
            haversine_distance_m(point, Coordinates(item.latitude, item.longitude))
            <= float(item.radius_m)
            for item in locations
        )
        if matches == 1:
            return candidate
    raise RuntimeError("no unambiguous active Location available")


def _users() -> tuple[User, ...]:
    run_id = uuid4().hex[:12]
    return tuple(
        User.objects.create(
            username=f"latency-{run_id}-{index}",
            full_name=f"Latency Participant {index}",
            role="HELPDESK",
            password="!",
            must_change_password=False,
        )
        for index in range(USER_COUNT)
    )


def _seed_sessions(service: object, actor_id: int, command: AttendanceCommand) -> None:
    commands = service.commands  # type: ignore[attr-defined]
    for _ in range(BASELINE_SESSIONS):
        commands.check_in(actor_id, command)
        commands.check_out(actor_id, command)


def _measure(service: object, actor_id: int, command: AttendanceCommand) -> list[float]:
    commands = service.commands  # type: ignore[attr-defined]
    queries = service.queries  # type: ignore[attr-defined]
    values: list[float] = []
    for trial in range(TRIALS):
        started = perf_counter()
        if trial % 2 == 0:
            commands.check_in(actor_id, command)
        else:
            commands.check_out(actor_id, command)
        queries.today(actor_id)
        values.append(perf_counter() - started)
    return values


def _result(durations: list[float]) -> dict[str, object]:
    ordered = sorted(durations)
    p95 = ordered[math.ceil(len(ordered) * 0.95) - 1]
    within = sum(value < TARGET_SECONDS for value in durations)
    return {
        "run_at_utc": datetime.now(UTC).isoformat(),
        "trials": TRIALS,
        "users": USER_COUNT,
        "canonical_locations": 76,
        "baseline_sessions": BASELINE_SESSIONS,
        "target_seconds": TARGET_SECONDS,
        "within_target": within,
        "p95_ms": round(p95 * 1000, 3),
        "passed": within >= 95,
    }


if __name__ == "__main__":
    raise SystemExit(main())
