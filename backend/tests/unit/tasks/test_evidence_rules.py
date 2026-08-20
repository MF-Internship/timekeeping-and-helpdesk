from decimal import Decimal

import pytest

from tasks.domain.evidence import (
    EvidenceLocationCandidate,
    GpsQuality,
    LocationResolutionMethod,
    classify_gps_quality,
    resolve_evidence_location,
    validate_upload_metadata,
)


def test_task_gps_quality_uses_two_independent_thresholds() -> None:
    assert classify_gps_quality(Decimal("25"), Decimal("25"), Decimal("100")) is GpsQuality.GOOD
    assert (
        classify_gps_quality(Decimal("25.01"), Decimal("25"), Decimal("100"))
        is GpsQuality.LOW_ACCURACY
    )
    assert (
        classify_gps_quality(Decimal("100.01"), Decimal("25"), Decimal("100"))
        is GpsQuality.UNRELIABLE
    )


@pytest.mark.parametrize("size_bytes", [0, 5_242_881])
def test_upload_metadata_rejects_invalid_size(size_bytes: int) -> None:
    with pytest.raises(ValueError, match="size_bytes"):
        validate_upload_metadata("image/jpeg", size_bytes, "a" * 64)


def test_upload_metadata_rejects_unapproved_mime_and_checksum() -> None:
    with pytest.raises(ValueError, match="mime"):
        validate_upload_metadata("image/heic", 10, "a" * 64)
    with pytest.raises(ValueError, match="checksum_sha256"):
        validate_upload_metadata("image/jpeg", 10, "not-a-checksum")


def test_location_resolution_requires_selection_for_multiple_candidates() -> None:
    candidates = (
        EvidenceLocationCandidate(2, "HCM000002", "Second", Decimal("3")),
        EvidenceLocationCandidate(1, "HCM000001", "First", Decimal("2")),
    )
    undecided = resolve_evidence_location(GpsQuality.GOOD, candidates, None)
    assert undecided.choice_required
    assert tuple(item.id for item in undecided.candidates) == (1, 2)

    selected = resolve_evidence_location(GpsQuality.GOOD, candidates, 2)
    assert selected.location_id == 2
    assert selected.method is LocationResolutionMethod.USER_SELECTED


def test_weak_gps_skips_candidates_and_uses_gps_only() -> None:
    result = resolve_evidence_location(
        GpsQuality.LOW_ACCURACY,
        (EvidenceLocationCandidate(1, "HCM000001", "First", Decimal("2")),),
        None,
    )
    assert result.location_id is None
    assert result.candidates == ()
    assert result.method is LocationResolutionMethod.GPS_ONLY
