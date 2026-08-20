from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone

from config import composition
from core.errors import IdentityAPIError
from locations.models import Location
from tasks.application.dto import CompleteTaskFieldCommand, CreateEvidenceUploadCommand
from tasks.models import TaskUpdate
from tests.integration.api.locations.helpers import create_config, create_location
from tests.integration.api.tasks.helpers import create_task, task_client
from tests.integration.postgres.tasks.test_task_evidence_atomicity import ConcurrentStorage

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


def setup(monkeypatch, username: str):
    storage = ConcurrentStorage()
    monkeypatch.setattr(composition, "S3EvidenceStorage", lambda: storage)
    composition.task_container.cache_clear()
    create_config()
    first = create_location("CANDIDATE-1")
    _, actor = task_client("HELPDESK", username)
    task = create_task(actor, actor, assigned_date=date.today(), status="IN_PROGRESS")
    return composition.task_container().evidence, actor, task, first


def command(service, actor, task, *, selected: int | None = None) -> CompleteTaskFieldCommand:
    upload = service.create_upload(
        CreateEvidenceUploadCommand(actor.pk, task.pk, "image/jpeg", 3, "a" * 64)
    )
    return CompleteTaskFieldCommand(
        actor.pk,
        task.pk,
        "candidate-key",
        (upload.upload_id,),
        Decimal("10"),
        Decimal("106"),
        Decimal("12"),
        timezone.now(),
        completion_note="done",
        selected_location_id=selected,
    )


def overlapping_location(code: str) -> Location:
    return Location.objects.create(
        code=code,
        name=code,
        kind="SHOP",
        address=f"Address {code}",
        latitude=Decimal("10"),
        longitude=Decimal("106"),
        radius_m=Decimal("50"),
    )


def test_candidate_snapshot_survives_later_location_catalog_changes(monkeypatch) -> None:
    service, actor, task, first = setup(monkeypatch, "pg-candidate-snapshot")
    second = overlapping_location("CANDIDATE-2")
    completion = command(service, actor, task, selected=first.pk)

    service.complete_field(completion)
    before = TaskUpdate.objects.get(task=task).location_candidates
    assert before == [first.pk, second.pk]

    Location.objects.filter(pk=first.pk).update(is_active=False, radius_m=Decimal("1"))
    Location.objects.filter(pk=second.pk).update(
        latitude=Decimal("11"), longitude=Decimal("107"), radius_m=Decimal("1")
    )
    overlapping_location("CANDIDATE-3")
    assert TaskUpdate.objects.get(task=task).location_candidates == before
    composition.task_container.cache_clear()


def test_new_good_candidate_is_recomputed_before_commit_and_requires_selection(monkeypatch) -> None:
    service, actor, task, _ = setup(monkeypatch, "pg-candidate-race")
    completion = command(service, actor, task)
    prepared = service._prepare_field(completion)
    overlapping_location("CANDIDATE-RACE")

    with pytest.raises(IdentityAPIError) as raised:
        service._commit_field(completion, prepared)
    assert raised.value.error_code == "LOCATION_CHOICE_REQUIRED"
    assert not TaskUpdate.objects.filter(task=task, status="COMPLETED").exists()
    composition.task_container.cache_clear()
