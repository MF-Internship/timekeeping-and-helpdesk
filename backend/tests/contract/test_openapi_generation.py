from __future__ import annotations

from scripts.generate_openapi import generate_openapi_bytes


def test_openapi_is_deterministic_and_canonical() -> None:
    first = generate_openapi_bytes()
    second = generate_openapi_bytes()
    assert first == second
    assert b"\r\n" not in first
    text = first.decode()
    assert text.startswith("openapi: 3.0.3\n")
    assert "version: 1.0.0" in text
    assert "operationId:" in text
    assert "timestamp" not in text.casefold()
    assert str(__file__) not in text


def test_all_paths_operation_ids_and_properties_are_canonical() -> None:
    from scripts.generate_openapi import schema_document

    document = schema_document()
    paths = document["paths"]
    assert paths
    operation_ids: list[str] = []
    for path, item in paths.items():
        assert path.startswith("/api/v1/")
        for operation in item.values():
            operation_ids.append(operation["operationId"])
    assert len(operation_ids) == len(set(operation_ids))
    assert operation_ids == ["api_schema_retrieve"]
