from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from tasks.domain.evidence import EvidenceLocationCandidate
from tasks.domain.tasks import LocationDisplay


@dataclass(frozen=True, slots=True)
class EvidenceLocationContext:
    task_gps_good_accuracy_m: Decimal
    task_gps_low_accuracy_m: Decimal
    candidates: tuple[EvidenceLocationCandidate, ...]


class LocationDirectory(Protocol):
    def get(self, location_id: int) -> LocationDisplay | None: ...
    def evidence_context(
        self, latitude: Decimal, longitude: Decimal
    ) -> EvidenceLocationContext: ...
