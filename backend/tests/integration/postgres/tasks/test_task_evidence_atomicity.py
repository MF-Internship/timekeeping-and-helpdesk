from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal
from threading import Barrier, Lock

import pytest
from django.db import close_old_connections
from django.utils import timezone

from audit.models import AuditLog
from config import composition
from core.errors import IdentityAPIError
from tasks.application.dto import CompleteTaskFieldCommand, CreateEvidenceUploadCommand
from tasks.models import CompletionIdempotency, EvidenceUpload, TaskPhoto, TaskUpdate
from tasks.ports.evidence import EvidenceObject, PresignedUpload, StoredEvidenceObject
from tests.integration.api.locations.helpers import create_config, create_location
from tests.integration.api.tasks.helpers import create_task, task_client

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


class ConcurrentStorage:
    def __init__(self) -> None:
        self._objects: dict[str, StoredEvidenceObject] = {}
        self._lock = Lock()

    def presign_put(self, evidence: EvidenceObject) -> PresignedUpload:
        with self._lock:
            self._objects[evidence.object_key] = StoredEvidenceObject(
                evidence.mime, evidence.size_bytes, evidence.checksum_sha256
            )
        return PresignedUpload(
            f"https://storage.invalid/{evidence.object_key}",
            {"Content-Type": evidence.mime},
            timezone.now() + timedelta(minutes=15),
        )

    def inspect(self, object_key: str) -> StoredEvidenceObject:
        with self._lock:
            return self._objects[object_key]

    def presign_get(self, object_key: str) -> tuple[str, object]:
        return f"https://storage.invalid/read/{object_key}", timezone.now() + timedelta(minutes=15)

    def delete(self, object_key: str) -> None:
        with self._lock:
            self._objects.pop(object_key, None)


def evidence_setup(monkeypatch, username: str):
    storage = ConcurrentStorage()
    monkeypatch.setattr(composition, "S3EvidenceStorage", lambda: storage)
    composition.task_container.cache_clear()
    create_config()
    create_location("HCM")
    _, actor = task_client("HELPDESK", username)
    task = create_task(actor, actor, assigned_date=date.today(), status="IN_PROGRESS")
    return composition.task_container().evidence, actor, task


def stage(service, actor_id: int, task_id: int, checksum: str = "a" * 64) -> str:
    return service.create_upload(
        CreateEvidenceUploadCommand(actor_id, task_id, "image/jpeg", 3, checksum)
    ).upload_id


def completion(actor_id: int, task_id: int, upload_id: str, key: str) -> CompleteTaskFieldCommand:
    return CompleteTaskFieldCommand(
        actor_id,
        task_id,
        key,
        (upload_id,),
        Decimal("10"),
        Decimal("106"),
        Decimal("12"),
        timezone.now(),
        completion_note="Đã xử lý",
    )


def test_competing_field_completions_commit_exactly_one_evidence_set(monkeypatch) -> None:  # noqa: PLR0915
    service, actor, task = evidence_setup(monkeypatch, "pg-evidence-owner")
    upload_ids = (
        stage(service, actor.pk, task.pk, "a" * 64),
        stage(service, actor.pk, task.pk, "b" * 64),
    )
    barrier = Barrier(2)

    def complete(index: int) -> str:
        close_old_connections()
        barrier.wait()
        try:
            result = composition.task_container().evidence.complete_field(
                completion(actor.pk, task.pk, upload_ids[index], f"race-{index}")
            )
            outcome = result.status.value
        except IdentityAPIError as error:
            outcome = error.error_code
        finally:
            close_old_connections()
        return outcome

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = (pool.submit(complete, 0), pool.submit(complete, 1))
        outcomes = [future.result() for future in futures]

    task.refresh_from_db()
    assert set(outcomes) == {"COMPLETED", "TASK_ALREADY_COMPLETED"}
    assert task.status == "COMPLETED"
    assert TaskUpdate.objects.filter(task=task, status="COMPLETED").count() == 1
    assert TaskPhoto.objects.filter(task_update__task=task).count() == 1
    assert CompletionIdempotency.objects.filter(task=task).count() == 1
    assert (
        AuditLog.objects.filter(
            target_type="Task", target_id=str(task.pk), action="task.completion.field_evidence"
        ).count()
        == 1
    )
    assert EvidenceUpload.objects.filter(task=task, status="BOUND").count() == 1
    assert EvidenceUpload.objects.filter(task=task, status="PENDING").count() == 1
    composition.task_container.cache_clear()


def test_same_key_replays_and_different_key_cannot_rebind_upload(monkeypatch) -> None:
    service, actor, task = evidence_setup(monkeypatch, "pg-evidence-replay")
    upload_id = stage(service, actor.pk, task.pk)
    command = completion(actor.pk, task.pk, upload_id, "stable-key")

    first = service.complete_field(command)
    replay = service.complete_field(command)
    assert first.id == replay.id == task.pk
    with pytest.raises(IdentityAPIError) as different_key:
        service.complete_field(completion(actor.pk, task.pk, upload_id, "different-key"))
    assert different_key.value.error_code == "EVIDENCE_UPLOAD_INVALID"
    assert TaskUpdate.objects.filter(task=task, status="COMPLETED").count() == 1
    assert TaskPhoto.objects.filter(task_update__task=task).count() == 1
    assert CompletionIdempotency.objects.filter(task=task).count() == 1
    composition.task_container.cache_clear()


def test_failure_inside_finalize_rolls_back_update_photo_binding_and_task(monkeypatch) -> None:
    service, actor, task = evidence_setup(monkeypatch, "pg-evidence-rollback")
    upload_id = stage(service, actor.pk, task.pk)

    def fail_binding(*_args, **_kwargs):
        raise RuntimeError("simulated binding failure")

    monkeypatch.setattr(service._dependencies.repository, "bind_evidence_uploads", fail_binding)
    with pytest.raises(RuntimeError, match="simulated binding failure"):
        service.complete_field(completion(actor.pk, task.pk, upload_id, "rollback-key"))

    task.refresh_from_db()
    assert task.status == "IN_PROGRESS"
    assert not TaskUpdate.objects.filter(task=task, status="COMPLETED").exists()
    assert not TaskPhoto.objects.filter(task_update__task=task).exists()
    assert not CompletionIdempotency.objects.filter(task=task).exists()
    assert EvidenceUpload.objects.get(pk=upload_id).status == "PENDING"
    composition.task_container.cache_clear()


def test_failure_after_field_audit_append_rolls_back_all_completion_rows(monkeypatch) -> None:
    service, actor, task = evidence_setup(monkeypatch, "pg-evidence-audit-rollback")
    upload_id = stage(service, actor.pk, task.pk)
    recorder = service._dependencies.audit
    original = recorder.append_audit_entry

    def append_then_fail(entry) -> None:
        original(entry)
        raise RuntimeError("simulated post-audit failure")

    monkeypatch.setattr(recorder, "append_audit_entry", append_then_fail)
    with pytest.raises(RuntimeError, match="post-audit failure"):
        service.complete_field(completion(actor.pk, task.pk, upload_id, "audit-rollback-key"))

    task.refresh_from_db()
    assert task.status == "IN_PROGRESS"
    assert not TaskUpdate.objects.filter(task=task, status="COMPLETED").exists()
    assert not TaskPhoto.objects.filter(task_update__task=task).exists()
    assert not CompletionIdempotency.objects.filter(task=task).exists()
    assert not AuditLog.objects.filter(target_type="Task", target_id=str(task.pk)).exists()
    assert EvidenceUpload.objects.get(pk=upload_id).status == "PENDING"
    composition.task_container.cache_clear()


def test_completed_task_rejects_staging_with_zero_evidence_delta(monkeypatch) -> None:
    storage = ConcurrentStorage()
    monkeypatch.setattr(composition, "S3EvidenceStorage", lambda: storage)
    composition.task_container.cache_clear()
    create_config()
    _, actor = task_client("HELPDESK", "pg-evidence-terminal")
    task = create_task(actor, actor, assigned_date=date.today(), status="COMPLETED")

    with pytest.raises(IdentityAPIError) as terminal:
        stage(composition.task_container().evidence, actor.pk, task.pk)
    assert terminal.value.error_code == "TASK_ALREADY_COMPLETED"
    assert not EvidenceUpload.objects.filter(task=task).exists()
    assert not TaskPhoto.objects.filter(task_update__task=task).exists()
    assert not CompletionIdempotency.objects.filter(task=task).exists()
    composition.task_container.cache_clear()
