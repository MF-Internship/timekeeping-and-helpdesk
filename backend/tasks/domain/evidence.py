from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

MAX_EVIDENCE_PHOTO_BYTES = 5 * 1024 * 1024
ALLOWED_EVIDENCE_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class GpsQuality(StrEnum):
    GOOD = "GOOD"
    LOW_ACCURACY = "LOW_ACCURACY"
    UNRELIABLE = "UNRELIABLE"


class LocationResolutionMethod(StrEnum):
    AUTO_SINGLE = "AUTO_SINGLE"
    USER_SELECTED = "USER_SELECTED"
    GPS_ONLY = "GPS_ONLY"


class EvidenceUploadStatus(StrEnum):
    PENDING = "PENDING"
    UPLOADED = "UPLOADED"
    BOUND = "BOUND"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True, slots=True)
class EvidenceLocationCandidate:
    id: int
    code: str
    name: str
    distance_m: Decimal


@dataclass(frozen=True, slots=True)
class EvidenceLocationResolution:
    location_id: int | None
    distance_m: Decimal | None
    method: LocationResolutionMethod | None
    candidates: tuple[EvidenceLocationCandidate, ...]
    choice_required: bool = False
    invalid_choice: bool = False


def classify_gps_quality(
    accuracy_m: Decimal,
    good_accuracy_m: Decimal,
    low_accuracy_m: Decimal,
) -> GpsQuality:
    for field, value in (
        ("accuracy_m", accuracy_m),
        ("good_accuracy_m", good_accuracy_m),
        ("low_accuracy_m", low_accuracy_m),
    ):
        if not value.is_finite() or value < 0:
            raise ValueError(field)
    if good_accuracy_m > low_accuracy_m:
        raise ValueError("good_accuracy_m")
    if accuracy_m <= good_accuracy_m:
        return GpsQuality.GOOD
    if accuracy_m <= low_accuracy_m:
        return GpsQuality.LOW_ACCURACY
    return GpsQuality.UNRELIABLE


def validate_upload_metadata(mime: str, size_bytes: int, checksum_sha256: str) -> None:
    if mime not in ALLOWED_EVIDENCE_MIME_TYPES:
        raise ValueError("mime")
    if isinstance(size_bytes, bool) or not 1 <= size_bytes <= MAX_EVIDENCE_PHOTO_BYTES:
        raise ValueError("size_bytes")
    if SHA256_PATTERN.fullmatch(checksum_sha256) is None:
        raise ValueError("checksum_sha256")


def resolve_evidence_location(
    gps_quality: GpsQuality,
    candidates: tuple[EvidenceLocationCandidate, ...],
    selected_location_id: int | None,
) -> EvidenceLocationResolution:
    if gps_quality is not GpsQuality.GOOD:
        return EvidenceLocationResolution(None, None, LocationResolutionMethod.GPS_ONLY, ())
    ordered = tuple(sorted(candidates, key=lambda item: item.id))
    if not ordered:
        return EvidenceLocationResolution(None, None, LocationResolutionMethod.GPS_ONLY, ())
    if len(ordered) == 1:
        return _resolve_single_candidate(ordered, selected_location_id)
    return _resolve_multiple_candidates(ordered, selected_location_id)


def _resolve_single_candidate(
    ordered: tuple[EvidenceLocationCandidate, ...], selected_location_id: int | None
) -> EvidenceLocationResolution:
    candidate = ordered[0]
    if selected_location_id not in (None, candidate.id):
        return EvidenceLocationResolution(None, None, None, ordered, invalid_choice=True)
    return EvidenceLocationResolution(
        candidate.id, candidate.distance_m, LocationResolutionMethod.AUTO_SINGLE, ordered
    )


def _resolve_multiple_candidates(
    ordered: tuple[EvidenceLocationCandidate, ...], selected_location_id: int | None
) -> EvidenceLocationResolution:
    if selected_location_id is None:
        return EvidenceLocationResolution(None, None, None, ordered, choice_required=True)
    selected = next((item for item in ordered if item.id == selected_location_id), None)
    if selected is None:
        return EvidenceLocationResolution(None, None, None, ordered, invalid_choice=True)
    return EvidenceLocationResolution(
        selected.id,
        selected.distance_m,
        LocationResolutionMethod.USER_SELECTED,
        ordered,
    )
