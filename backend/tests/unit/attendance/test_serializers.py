from datetime import UTC, datetime, timedelta

import pytest
from rest_framework.exceptions import ValidationError

from attendance.adapters.api.serializers import AttendanceCommandSerializer
from core.errors import IdentityAPIError

NOW = datetime(2026, 8, 18, 4, 0, tzinfo=UTC)
BASE = {"latitude": "10", "longitude": "106", "accuracy_m": "5"}


def validate(**overrides: object) -> dict[str, object]:
    serializer = AttendanceCommandSerializer(
        data={**BASE, **overrides}, context={"receipt_time": NOW}
    )
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def test_accepts_optional_capture_at_at_exact_freshness_boundary() -> None:
    values = validate(captured_at=(NOW - timedelta(seconds=60)).isoformat())
    assert values["captured_at"] == NOW - timedelta(seconds=60)


def test_rejects_stale_capture_before_business_boundary() -> None:
    with pytest.raises(ValidationError):
        validate(captured_at=(NOW - timedelta(seconds=60, microseconds=1)).isoformat())


@pytest.mark.parametrize(
    ("field", "value"),
    [("latitude", "91"), ("longitude", "-181"), ("accuracy_m", "-0.001")],
)
def test_rejects_coordinate_and_accuracy_ranges(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        validate(**{field: value})


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_rejects_non_finite_coordinates_and_accuracy(value: str) -> None:
    for field in ("latitude", "longitude", "accuracy_m"):
        with pytest.raises(ValidationError):
            validate(**{field: value})


def test_captured_at_is_optional() -> None:
    assert "captured_at" not in validate()


@pytest.mark.parametrize("field", ["user_id", "kind", "recorded_at", "work_date"])
def test_rejects_server_owned_or_unknown_fields(field: str) -> None:
    with pytest.raises(IdentityAPIError) as caught:
        validate(**{field: "injected"})
    assert caught.value.error_code == "SERVER_OWNED_FIELD"
