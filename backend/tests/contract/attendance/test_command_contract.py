from scripts.generate_openapi import schema_document


def test_command_contract_owns_input_and_declares_disjoint_business_errors() -> None:
    document = schema_document()
    schemas = document["components"]["schemas"]
    request = schemas["AttendanceCommand"]
    assert set(request["required"]) == {"latitude", "longitude", "accuracy_m"}
    assert set(request["properties"]) == {
        "latitude",
        "longitude",
        "accuracy_m",
        "captured_at",
        "selected_location_id",
    }
    for path in ("/api/v1/attendance/check-in", "/api/v1/attendance/check-out"):
        responses = document["paths"][path]["post"]["responses"]
        assert set(responses) == {"201", "400", "401", "403", "409", "422"}
        conflict = _schema(document, responses["409"])
        unprocessable = _schema(document, responses["422"])
        assert len(conflict["oneOf"]) == len(_examples(responses["409"])) == 2
        assert len(unprocessable["oneOf"]) == 2
        assert len(_examples(responses["422"])) == 3
        assert _example_codes(responses["422"]) == {
            "WEAK_GPS",
            "OUTSIDE_RADIUS",
            "INVALID_LOCATION_CHOICE",
        }


def test_candidate_error_cardinality_and_coordinate_examples_are_safe() -> None:
    document = schema_document()
    schemas = document["components"]["schemas"]
    required = schemas["LocationChoiceRequiredError"]
    invalid = schemas["InvalidLocationChoiceError"]
    assert required["properties"]["location_candidates"]["minItems"] == 2
    assert invalid["properties"]["location_candidates"]["minItems"] == 1
    assert "example" not in schemas["AttendanceCommand"]["properties"]["latitude"]
    assert "example" not in schemas["AttendanceCommand"]["properties"]["longitude"]


def _schema(document: dict[str, object], response: dict[str, object]) -> dict[str, object]:
    raw = response["content"]["application/json"]["schema"]  # type: ignore[index]
    name = raw["$ref"].rsplit("/", 1)[-1]  # type: ignore[index,union-attr]
    return document["components"]["schemas"][name]  # type: ignore[index,return-value]


def _examples(response: dict[str, object]) -> dict[str, object]:
    return response["content"]["application/json"]["examples"]  # type: ignore[index,return-value]


def _example_codes(response: dict[str, object]) -> set[str]:
    return {item["value"]["error_code"] for item in _examples(response).values()}  # type: ignore[index,misc]
