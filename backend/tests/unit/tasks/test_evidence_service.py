from dataclasses import dataclass, replace
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from core.error_codes import IDEMPOTENCY_CONFLICT, LOCATION_CHOICE_REQUIRED
from core.errors import IdentityAPIError
from tasks.application.dependencies import TaskDependencies
from tasks.application.dto import CompleteTaskFieldCommand, CreateEvidenceUploadCommand
from tasks.application.evidence import TaskEvidenceService
from tasks.domain.evidence import EvidenceLocationCandidate, EvidenceUploadStatus
from tasks.domain.tasks import TaskStatus
from tasks.ports.evidence import EvidenceObject, PresignedUpload, StoredEvidenceObject
from tasks.ports.locations import EvidenceLocationContext
from tasks.ports.repositories import EvidenceUploadSnapshot, IdempotencySnapshot
from tests.unit.tasks.fakes import Assignees, Audit, Clock, Repository, UnitOfWork, snapshot


class Authorization:
    def authorize_field_completion(self, actor_id: int) -> None:
        return None

    def authorize_photo_read(self, actor_id: int) -> object:
        raise AssertionError("not used")


class Locations:
    def __init__(self, candidates: tuple[EvidenceLocationCandidate, ...] = ()) -> None:
        self.candidates = candidates

    def get(self, location_id: int) -> object:
        raise AssertionError("not used")

    def evidence_context(self, latitude: Decimal, longitude: Decimal) -> EvidenceLocationContext:
        return EvidenceLocationContext(Decimal("25"), Decimal("100"), self.candidates)


class Storage:
    def presign_put(self, evidence: EvidenceObject) -> PresignedUpload:
        return PresignedUpload("https://upload.invalid", {}, Clock().now() + timedelta(minutes=15))

    def inspect(self, object_key: str) -> StoredEvidenceObject:
        return StoredEvidenceObject("image/jpeg", 123, "a" * 64)

    def presign_get(self, object_key: str) -> tuple[str, object]:
        raise AssertionError("not used")


@dataclass
class Update:
    id: int


class EvidenceRepository(Repository):
    def __init__(self) -> None:
        super().__init__(snapshot(task_id=1, creator_id=10), assignees=(10,))
        self.uploads: dict[UUID, EvidenceUploadSnapshot] = {}
        self.idempotency: IdempotencySnapshot | None = None
        self.bound_count = 0

    def create_evidence_upload(self, record: object) -> EvidenceUploadSnapshot:
        upload = EvidenceUploadSnapshot(
            record.id,
            record.task_id,
            record.actor_id,
            record.object_key,
            record.mime,
            record.size_bytes,
            record.checksum_sha256,
            EvidenceUploadStatus.PENDING,
            record.expires_at,
            None,
        )
        self.uploads[upload.id] = upload
        return upload

    def get_evidence_uploads(
        self, upload_ids: tuple[UUID, ...], *, lock: bool = False
    ) -> tuple[EvidenceUploadSnapshot, ...]:
        return tuple(self.uploads[value] for value in upload_ids if value in self.uploads)

    def append_update(self, record: object) -> Update:
        self.updates.append(record)
        return Update(77)

    def bind_evidence_uploads(self, task_update_id: int, photos: tuple[object, ...]) -> None:
        self.bound_count += len(photos)

    def get_idempotency(self, actor_id: int, task_id: int, key: str) -> IdempotencySnapshot | None:
        return self.idempotency

    def create_idempotency(self, record: object) -> None:
        self.idempotency = IdempotencySnapshot(record.request_hash, record.task_update_id)

    def get_photo_object_key(self, task_id: int, photo_id: int) -> str | None:
        return None


def service(
    repository: EvidenceRepository,
    candidates: tuple[EvidenceLocationCandidate, ...] = (),
    audit: Audit | None = None,
) -> TaskEvidenceService:
    return TaskEvidenceService(
        TaskDependencies(
            authorization=Authorization(),
            assignees=Assignees(),
            locations=Locations(candidates),
            repository=repository,
            clock=Clock(),
            audit=audit or Audit(),
            unit_of_work_factory=UnitOfWork,
            storage=Storage(),
        )
    )


def upload(repository: EvidenceRepository) -> str:
    result = service(repository).create_upload(
        CreateEvidenceUploadCommand(10, 1, "image/jpeg", 123, "a" * 64)
    )
    return result.upload_id


def command(
    upload_id: str, *, key: str = "key-1", selected: int | None = None
) -> CompleteTaskFieldCommand:
    return CompleteTaskFieldCommand(
        10,
        1,
        key,
        (upload_id,),
        Decimal("10.0"),
        Decimal("106.0"),
        Decimal("20"),
        Clock().now(),
        selected_location_id=selected,
    )


def test_field_completion_binds_photo_and_completes_once() -> None:
    repository = EvidenceRepository()
    upload_id = upload(repository)
    result = service(repository).complete_field(command(upload_id))
    assert result.status is TaskStatus.COMPLETED
    assert repository.bound_count == 1
    assert len(repository.updates) == 1
    assert repository.idempotency is not None


def test_field_completion_appends_privacy_safe_audit() -> None:
    repository = EvidenceRepository()
    audit = Audit()
    upload_id = upload(repository)

    service(repository, audit=audit).complete_field(command(upload_id))

    assert len(audit.entries) == 1
    entry = audit.entries[0]
    assert entry.action.value == "task.completion.field_evidence"
    assert entry.before == {"status": "TODO"}
    assert entry.after == {
        "task_id": 1,
        "status": "COMPLETED",
        "completion_method": "FIELD_EVIDENCE",
        "completed_by_id": 10,
        "completed_at": Clock().now().isoformat(),
    }


def test_same_idempotency_replays_and_different_payload_conflicts() -> None:
    repository = EvidenceRepository()
    upload_id = upload(repository)
    evidence = service(repository)
    evidence.complete_field(command(upload_id))
    evidence.complete_field(command(upload_id))
    assert len(repository.updates) == 1
    with pytest.raises(IdentityAPIError) as caught:
        evidence.complete_field(replace(command(upload_id), completion_note="changed"))
    assert caught.value.error_code == IDEMPOTENCY_CONFLICT


def test_multiple_good_candidates_require_selection_without_consuming_key() -> None:
    repository = EvidenceRepository()
    upload_id = upload(repository)
    candidates = (
        EvidenceLocationCandidate(1, "A", "First", Decimal("1")),
        EvidenceLocationCandidate(2, "B", "Second", Decimal("2")),
    )
    with pytest.raises(IdentityAPIError) as caught:
        service(repository, candidates).complete_field(command(upload_id))
    assert caught.value.error_code == LOCATION_CHOICE_REQUIRED
    assert repository.idempotency is None
