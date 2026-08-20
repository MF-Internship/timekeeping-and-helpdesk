from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from django.utils import timezone

from config import composition
from core.errors import IdentityAPIError
from tasks.application.dto import CompleteTaskFieldCommand, CreateEvidenceUploadCommand
from tasks.models import EvidenceUpload, TaskPhoto
from tasks.ports.evidence import EvidenceObject, PresignedUpload, StoredEvidenceObject
from tests.integration.api.locations.helpers import create_config, create_location
from tests.integration.api.tasks.helpers import create_task, task_client

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


class CleanupStorage:
    def __init__(self) -> None:
        self.objects: dict[str, StoredEvidenceObject] = {}
        self.fail_delete: set[str] = set()

    def presign_put(self, evidence: EvidenceObject) -> PresignedUpload:
        self.objects[evidence.object_key] = StoredEvidenceObject(
            evidence.mime, evidence.size_bytes, evidence.checksum_sha256
        )
        return PresignedUpload(
            f"https://storage.invalid/{evidence.object_key}",
            {"Content-Type": evidence.mime},
            timezone.now() + timedelta(minutes=15),
        )

    def inspect(self, object_key: str) -> StoredEvidenceObject:
        return self.objects[object_key]

    def presign_get(self, object_key: str) -> tuple[str, object]:
        return f"https://storage.invalid/read/{object_key}", timezone.now()

    def delete(self, object_key: str) -> None:
        if object_key in self.fail_delete:
            raise RuntimeError("temporary storage failure")
        self.objects.pop(object_key, None)


def _setup(monkeypatch, username: str):
    storage = CleanupStorage()
    monkeypatch.setattr(composition, "S3EvidenceStorage", lambda: storage)
    composition.task_container.cache_clear()
    create_config()
    create_location("CLEANUP")
    _, actor = task_client("HELPDESK", username)
    task = create_task(actor, actor, assigned_date=date.today(), status="IN_PROGRESS")
    return composition.task_container(), storage, actor, task


def _stage(container, actor_id: int, task_id: int, checksum: str) -> EvidenceUpload:
    result = container.evidence.create_upload(
        CreateEvidenceUploadCommand(actor_id, task_id, "image/jpeg", 3, checksum)
    )
    return EvidenceUpload.objects.get(pk=result.upload_id)


def _complete(container, actor, task, upload_id: UUID) -> None:
    container.evidence.complete_field(
        CompleteTaskFieldCommand(
            actor.pk,
            task.pk,
            f"cleanup-{task.pk}",
            (str(upload_id),),
            Decimal("10"),
            Decimal("106"),
            Decimal("12"),
            timezone.now(),
            completion_note="Đã xử lý",
        )
    )


def test_cleanup_deletes_only_expired_unbound_and_retries_storage_failures(  # noqa: PLR0915
    monkeypatch,
) -> None:
    container, storage, actor, task = _setup(monkeypatch, "pg-cleanup")
    expired = _stage(container, actor.pk, task.pk, "a" * 64)
    unexpired = _stage(container, actor.pk, task.pk, "b" * 64)
    failed = _stage(container, actor.pk, task.pk, "c" * 64)
    bound = _stage(container, actor.pk, task.pk, "d" * 64)
    past = timezone.now() - timedelta(days=8)
    EvidenceUpload.objects.filter(pk__in=(expired.pk, failed.pk)).update(expires_at=past)
    _complete(container, actor, task, bound.pk)
    EvidenceUpload.objects.filter(pk=bound.pk).update(expires_at=past)
    storage.fail_delete.add(failed.object_key)

    first = container.evidence_cleanup.run()

    assert first.scanned_count == 2
    assert first.deleted_count == 1
    assert first.failed_count == 1
    assert not EvidenceUpload.objects.filter(pk=expired.pk).exists()
    assert EvidenceUpload.objects.filter(pk=unexpired.pk, status="PENDING").exists()
    assert EvidenceUpload.objects.filter(pk=bound.pk, status="BOUND").exists()
    assert TaskPhoto.objects.filter(evidence_upload_id=bound.pk).exists()
    assert EvidenceUpload.objects.filter(pk=failed.pk, status="EXPIRED").exists()
    assert bound.object_key in storage.objects

    storage.fail_delete.clear()
    retry = container.evidence_cleanup.run()
    assert retry.deleted_count == 1
    assert retry.failed_count == 0
    assert not EvidenceUpload.objects.filter(pk=failed.pk).exists()
    composition.task_container.cache_clear()


def test_cleanup_claim_wins_finalize_race_without_creating_bound_photo(monkeypatch) -> None:
    container, storage, actor, task = _setup(monkeypatch, "pg-cleanup-race")
    upload = _stage(container, actor.pk, task.pk, "e" * 64)
    EvidenceUpload.objects.filter(pk=upload.pk).update(
        expires_at=timezone.now() - timedelta(days=8)
    )

    assert container.evidence_cleanup._claim(upload.pk) == upload.object_key
    with pytest.raises(IdentityAPIError) as raised:
        _complete(container, actor, task, upload.pk)
    assert raised.value.error_code == "EVIDENCE_UPLOAD_NOT_READY"
    assert not TaskPhoto.objects.filter(evidence_upload_id=upload.pk).exists()

    outcome = container.evidence_cleanup.run()
    assert outcome.deleted_count == 1
    assert upload.object_key not in storage.objects
    composition.task_container.cache_clear()
