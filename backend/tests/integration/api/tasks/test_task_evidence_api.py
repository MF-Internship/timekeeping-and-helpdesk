from datetime import date, timedelta

import pytest
from django.utils import timezone

from config import composition
from tasks.models import CompletionIdempotency, TaskPhoto, TaskUpdate
from tasks.ports.evidence import EvidenceObject, PresignedUpload, StoredEvidenceObject
from tests.integration.api.locations.helpers import create_config, create_location
from tests.integration.api.tasks.helpers import create_task, task_client

pytestmark = pytest.mark.django_db


class Storage:
    def presign_put(self, evidence: EvidenceObject) -> PresignedUpload:
        self.object_key = evidence.object_key
        return PresignedUpload(
            "https://storage.invalid/upload",
            {"Content-Type": evidence.mime},
            timezone.now() + timedelta(minutes=15),
        )

    def inspect(self, object_key: str) -> StoredEvidenceObject:
        assert object_key == self.object_key
        return StoredEvidenceObject("image/jpeg", 3, "a" * 64)

    def presign_get(self, object_key: str) -> tuple[str, object]:
        return "https://storage.invalid/read", timezone.now() + timedelta(minutes=15)


def test_field_evidence_api_commits_once_and_protects_photo_access(monkeypatch) -> None:
    storage = Storage()
    monkeypatch.setattr(composition, "S3EvidenceStorage", lambda: storage)
    composition.task_container.cache_clear()
    create_config()
    create_location("HCM")
    client, actor = task_client("HELPDESK", "task-evidence-owner")
    outsider, _ = task_client("HELPDESK", "task-evidence-outsider")
    task = create_task(actor, actor, assigned_date=date.today(), status="IN_PROGRESS")
    intent = client.post(
        f"/api/v1/tasks/{task.pk}/evidence-uploads",
        {"mime": "image/jpeg", "size_bytes": 3, "checksum_sha256": "a" * 64},
        format="json",
    )
    assert intent.status_code == 201, intent.json()
    body = {
        "upload_ids": [intent.json()["upload_id"]],
        "latitude": "10.123456789012345",
        "longitude": "106.123456789012345",
        "accuracy_m": "12",
        "captured_at": timezone.now().isoformat(),
        "completion_note": "Đã xử lý",
    }
    completed = client.post(
        f"/api/v1/tasks/{task.pk}/complete-field",
        body,
        format="json",
        HTTP_IDEMPOTENCY_KEY="submission-1",
    )
    assert completed.status_code == 200, completed.json()
    assert completed.json()["completion_method"] == "FIELD_EVIDENCE"
    assert TaskUpdate.objects.filter(task=task, status="COMPLETED").count() == 1
    assert TaskPhoto.objects.count() == CompletionIdempotency.objects.count() == 1
    replay = client.post(
        f"/api/v1/tasks/{task.pk}/complete-field",
        body,
        format="json",
        HTTP_IDEMPOTENCY_KEY="submission-1",
    )
    assert replay.status_code == 200
    photo = TaskPhoto.objects.get()
    denied = outsider.post(f"/api/v1/tasks/{task.pk}/photos/{photo.pk}/access")
    assert denied.status_code == 404
    access = client.post(f"/api/v1/tasks/{task.pk}/photos/{photo.pk}/access")
    assert access.status_code == 200 and access.json()["url"].endswith("/read")
    assert "no-store" in access.headers["Cache-Control"]
    composition.task_container.cache_clear()


def test_invalid_coordinate_precision_returns_redacted_400_not_500() -> None:
    client, actor = task_client("HELPDESK", "task-evidence-invalid-coordinate")
    task = create_task(actor, actor, assigned_date=date.today(), status="IN_PROGRESS")
    response = client.post(
        f"/api/v1/tasks/{task.pk}/complete-field",
        {
            "upload_ids": ["00000000-0000-4000-8000-000000000001"],
            "latitude": "10.1234567890123456",
            "longitude": "106",
            "accuracy_m": "12",
            "captured_at": timezone.now().isoformat(),
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY="invalid-coordinate",
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "VALIDATION_FAILED"
    assert response.json()["details"] == {
        "fields": ["Giá trị đầu vào được bảo vệ không hợp lệ."]
    }
    assert "latitude" not in str(response.json())
