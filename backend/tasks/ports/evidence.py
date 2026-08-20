from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PresignedUpload:
    url: str
    headers: dict[str, str]
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class StoredEvidenceObject:
    mime: str
    size_bytes: int
    checksum_sha256: str


@dataclass(frozen=True, slots=True)
class EvidenceObject:
    object_key: str
    mime: str
    size_bytes: int
    checksum_sha256: str


class EvidenceStorage(Protocol):
    def presign_put(self, evidence: EvidenceObject) -> PresignedUpload: ...

    def inspect(self, object_key: str) -> StoredEvidenceObject: ...
    def presign_get(self, object_key: str) -> tuple[str, datetime]: ...
    def delete(self, object_key: str) -> None: ...
