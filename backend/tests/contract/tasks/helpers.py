from __future__ import annotations

from typing import Any

from scripts.generate_openapi import schema_document


def task_contract() -> dict[str, Any]:
    return schema_document()


def schema(document: dict[str, Any], name: str) -> dict[str, Any]:
    return document["components"]["schemas"][name]


def resolved_schema(document: dict[str, Any], value: dict[str, Any]) -> dict[str, Any]:
    reference = value.get("$ref")
    if reference is None:
        return value
    return schema(document, reference.rsplit("/", 1)[-1])


def request_schema(document: dict[str, Any], path: str, method: str) -> dict[str, Any]:
    raw = document["paths"][path][method]["requestBody"]["content"]["application/json"]["schema"]
    return resolved_schema(document, raw)


def response_schema(
    document: dict[str, Any], path: str, method: str, status: str
) -> dict[str, Any]:
    raw = document["paths"][path][method]["responses"][status]["content"]["application/json"][
        "schema"
    ]
    return resolved_schema(document, raw)


def expanded(document: dict[str, Any], value: Any) -> Any:
    if isinstance(value, list):
        return [expanded(document, item) for item in value]
    if not isinstance(value, dict):
        return value
    if "$ref" in value:
        referenced = schema(document, value["$ref"].rsplit("/", 1)[-1])
        merged = {**referenced, **{key: item for key, item in value.items() if key != "$ref"}}
        return expanded(document, merged)
    return {key: expanded(document, item) for key, item in value.items()}


def expanded_response_schema(
    document: dict[str, Any], path: str, method: str, status: str
) -> dict[str, Any]:
    return expanded(document, response_schema(document, path, method, status))
