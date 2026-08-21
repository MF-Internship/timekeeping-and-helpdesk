from __future__ import annotations

import json
import math
import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.db import connection, transaction  # noqa: E402
from django.utils import timezone  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402

from identity.models import User  # noqa: E402
from tasks.models import Task, TaskAssignee, TaskUpdate  # noqa: E402

TRIALS = 100
USER_COUNT = 50
TASK_COUNT = 400
TARGET_SECONDS = 2.0
EXPECTED_GROUPS = {"overdue", "today", "upcoming", "completed"}


def main() -> int:
    _require_postgresql()
    run_id = uuid4().hex[:12]
    result: dict[str, object]
    with transaction.atomic():
        manager, helpdesk_users = _seed_users(run_id)
        _seed_task_history(manager, helpdesk_users, timezone.localdate())
        durations = _measure_authorized_reads(manager)
        result = _result(durations)
        transaction.set_rollback(True)
    _assert_rollback(run_id)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 1


def _require_postgresql() -> None:
    if connection.vendor != "postgresql":
        raise RuntimeError("Task-list capacity evidence requires PostgreSQL")


def _seed_users(run_id: str) -> tuple[User, tuple[User, ...]]:
    manager = User.objects.create(
        username=f"task-capacity-manager-{run_id}",
        full_name="Task Capacity Manager",
        role="MANAGER",
        password="!",
        must_change_password=False,
    )
    users = tuple(
        User(
            username=f"task-capacity-helpdesk-{run_id}-{index:02d}",
            full_name=f"Task Capacity Helpdesk {index:02d}",
            role="HELPDESK",
            password="!",
            must_change_password=False,
        )
        for index in range(USER_COUNT - 1)
    )
    return manager, tuple(User.objects.bulk_create(users))


def _seed_task_history(manager: User, users: tuple[User, ...], today: date) -> None:
    completed_at = timezone.now()
    tasks = tuple(
        _task_for_group(index, manager, today, completed_at)
        for index in range(TASK_COUNT)
    )
    created = tuple(Task.objects.bulk_create(tasks))
    TaskAssignee.objects.bulk_create(
        TaskAssignee(task=task, user=users[index % len(users)])
        for index, task in enumerate(created)
    )
    TaskUpdate.objects.bulk_create(
        _history_for(task, manager, completed_at)
        for task in created
        if task.status in {"BLOCKED", "COMPLETED"}
    )


def _task_for_group(
    index: int, manager: User, today: date, completed_at: datetime
) -> Task:
    group = index % 4
    assigned_dates = (
        today - timedelta(days=7),
        today,
        today + timedelta(days=7),
        today - timedelta(days=3),
    )
    statuses = ("TODO", "IN_PROGRESS", "BLOCKED", "COMPLETED")
    status = statuses[group]
    completed = status == "COMPLETED"
    return Task(
        title=f"Representative task {index:04d}",
        description="Synthetic capacity-history row",
        created_by=manager,
        assigned_date=assigned_dates[group],
        status=status,
        block_reason="Synthetic dependency" if status == "BLOCKED" else None,
        completed_by=manager if completed else None,
        completed_at=completed_at if completed else None,
        completion_method="MANAGER_OVERRIDE" if completed else None,
        completion_note="Synthetic capacity completion" if completed else None,
    )


def _history_for(task: Task, manager: User, recorded_at: datetime) -> TaskUpdate:
    completed = task.status == "COMPLETED"
    return TaskUpdate(
        task=task,
        user=manager,
        status=task.status,
        recorded_at=recorded_at,
        block_reason=task.block_reason,
        completion_method="MANAGER_OVERRIDE" if completed else None,
        completion_note="Synthetic capacity completion" if completed else None,
    )


def _measure_authorized_reads(manager: User) -> list[float]:
    client = APIClient(HTTP_X_ORIGIN_CREDENTIAL=str(settings.ORIGIN_CREDENTIAL))
    client.force_authenticate(user=manager)
    _read_once(client)
    durations: list[float] = []
    for _ in range(TRIALS):
        started = perf_counter()
        _read_once(client)
        durations.append(perf_counter() - started)
    return durations


def _read_once(client: APIClient) -> None:
    response: Any = client.get("/api/v1/tasks/")
    if response.status_code != 200:
        raise RuntimeError(f"Task-list read returned HTTP {response.status_code}")
    document = response.json()
    if not isinstance(document, dict) or not set(document) >= EXPECTED_GROUPS:
        raise RuntimeError("Task-list response omitted a canonical group")


def _result(durations: list[float]) -> dict[str, object]:
    ordered = sorted(durations)
    p95 = ordered[math.ceil(len(ordered) * 0.95) - 1]
    within = sum(value < TARGET_SECONDS for value in durations)
    return {
        "run_at_utc": datetime.now(UTC).isoformat(),
        "trials": TRIALS,
        "users": USER_COUNT,
        "representative_tasks": TASK_COUNT,
        "target_seconds": TARGET_SECONDS,
        "within_target": within,
        "p95_ms": round(p95 * 1000, 3),
        "passed": within >= 95 and p95 < TARGET_SECONDS,
    }


def _assert_rollback(run_id: str) -> None:
    if User.objects.filter(username__contains=run_id).exists():
        raise RuntimeError("Task-list capacity fixture rollback failed")


if __name__ == "__main__":
    raise SystemExit(main())
