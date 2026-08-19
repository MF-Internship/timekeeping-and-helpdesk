from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from locations.domain.geofence import (
    EARTH_RADIUS_M,
    LocationValidationResult,
    classify_geofence,
    haversine_distance_m,
)
from locations.domain.locations import Coordinates

ROOT = Path(__file__).parents[4]
FIXTURE = ROOT / "contracts/fixtures/geofence-distance.json"


def load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def coordinates(point: dict[str, str]) -> Coordinates:
    return Coordinates(latitude=Decimal(point["latitude"]), longitude=Decimal(point["longitude"]))


FIXTURE_DOC = load_fixture()
CASES = [pytest.param(case, id=str(case["id"])) for case in FIXTURE_DOC["cases"]]


@pytest.mark.contract
def test_fixture_earth_radius_matches_the_canonical_constant() -> None:
    assert FIXTURE_DOC["earth_radius_m"] == EARTH_RADIUS_M


@pytest.mark.contract
def test_fixture_covers_every_required_scenario() -> None:
    assert len(FIXTURE_DOC["cases"]) >= 14
    assert len({case["id"] for case in FIXTURE_DOC["cases"]}) == len(FIXTURE_DOC["cases"])


@pytest.mark.contract
def test_classification_exposes_exactly_two_members() -> None:
    assert [member.value for member in LocationValidationResult] == [
        "INSIDE_GEOFENCE",
        "OUTSIDE_GEOFENCE",
    ]


@pytest.mark.contract
@pytest.mark.parametrize("case", CASES)
def test_distance_matches_the_fixture_within_tolerance(case: dict[str, Any]) -> None:
    distance = haversine_distance_m(coordinates(case["origin"]), coordinates(case["destination"]))
    assert abs(distance - case["expected_distance_m"]) <= FIXTURE_DOC["tolerance_m"]


@pytest.mark.contract
@pytest.mark.parametrize("case", CASES)
def test_distance_is_symmetric(case: dict[str, Any]) -> None:
    origin, destination = coordinates(case["origin"]), coordinates(case["destination"])
    assert haversine_distance_m(origin, destination) == haversine_distance_m(destination, origin)


@pytest.mark.contract
@pytest.mark.parametrize("case", CASES)
def test_classification_matches_the_fixture(case: dict[str, Any]) -> None:
    distance = haversine_distance_m(coordinates(case["origin"]), coordinates(case["destination"]))
    result = classify_geofence(distance, Decimal(case["radius_m"]))
    assert result.value == case["expected_status"]
