from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from tasks.application.dependencies import TaskDependencies
from tasks.domain.evidence import EvidenceUploadStatus
from tasks.ports.evidence import EvidenceStorage


@dataclass(frozen=True, slots=True)
class EvidenceCleanupOutcome:
    scanned_count: int
    deleted_count: int
    failed_count: int


class EvidenceUploadCleanupService:
    """Remove expired, unbound staging objects without risking bound evidence."""

    def __init__(self, dependencies: TaskDependencies) -> None:
        if dependencies.storage is None:
            raise ValueError("Evidence storage is required")
        self._dependencies = dependencies
        self._storage: EvidenceStorage = dependencies.storage

    def run(self, *, limit: int = 500) -> EvidenceCleanupOutcome:
        if limit < 1:
            raise ValueError("limit must be positive")
        repository = self._dependencies.repository
        upload_ids = repository.list_cleanup_upload_ids(self._dependencies.clock.now(), limit)
        deleted = 0
        failed = 0
        for upload_id in upload_ids:
            object_key = self._claim(upload_id)
            if object_key is None:
                continue
            try:
                self._storage.delete(object_key)
            except Exception:  # storage failures are isolated and retried on the next run
                failed += 1
                continue
            if self._delete_claim(upload_id):
                deleted += 1
        return EvidenceCleanupOutcome(len(upload_ids), deleted, failed)

    def _claim(self, upload_id: UUID) -> str | None:
        repository = self._dependencies.repository
        with self._dependencies.unit_of_work_factory():
            uploads = repository.get_evidence_uploads((upload_id,), lock=True)
            if len(uploads) != 1:
                return None
            upload = uploads[0]
            if (
                upload.bound_update_id is not None
                or upload.status is EvidenceUploadStatus.BOUND
                or upload.expires_at > self._dependencies.clock.now()
            ):
                return None
            repository.mark_evidence_upload_expired(upload_id)
            return upload.object_key

    def _delete_claim(self, upload_id: UUID) -> bool:
        repository = self._dependencies.repository
        with self._dependencies.unit_of_work_factory():
            uploads = repository.get_evidence_uploads((upload_id,), lock=True)
            if len(uploads) != 1:
                return False
            upload = uploads[0]
            if (
                upload.status is not EvidenceUploadStatus.EXPIRED
                or upload.bound_update_id is not None
            ):
                return False
            repository.delete_expired_evidence_upload(upload_id)
            return True
