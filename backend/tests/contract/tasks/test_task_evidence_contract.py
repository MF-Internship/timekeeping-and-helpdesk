from tests.contract.tasks.helpers import request_schema, schema, task_contract


def test_evidence_upload_contract_is_single_private_image_intent() -> None:
    document = task_contract()
    path = "/api/v1/tasks/{task_id}/evidence-uploads"
    operation = document["paths"][path]["post"]
    assert operation["operationId"] == "tasks_evidence_uploads_create"
    request = request_schema(document, path, "post")
    assert set(request["required"]) == {"mime", "size_bytes", "checksum_sha256"}
    assert request["properties"]["size_bytes"]["maximum"] == 5 * 1024 * 1024
    response_ref = operation["responses"]["201"]["content"]["application/json"]["schema"]["$ref"]
    assert response_ref.endswith("/EvidenceUploadIntent")


def test_complete_field_requires_idempotency_and_one_to_five_uploads() -> None:
    document = task_contract()
    path = "/api/v1/tasks/{task_id}/complete-field"
    operation = document["paths"][path]["post"]
    assert operation["operationId"] == "tasks_complete_field_create"
    headers = [item for item in operation["parameters"] if item.get("in") == "header"]
    assert headers == [
        {
            "in": "header",
            "name": "Idempotency-Key",
            "schema": {"type": "string"},
            "required": True,
        }
    ]
    request = request_schema(document, path, "post")
    uploads = request["properties"]["upload_ids"]
    assert uploads["minItems"] == 1
    assert uploads["maxItems"] == 5
    assert set(operation["responses"]) == {"200", "400", "401", "403", "404", "409", "422"}


def test_photo_access_is_a_separate_authorized_operation() -> None:
    document = task_contract()
    path = "/api/v1/tasks/{task_id}/photos/{photo_id}/access"
    operation = document["paths"][path]["post"]
    assert operation["operationId"] == "tasks_photos_access_create"
    assert set(operation["responses"]) == {"200", "401", "403", "404"}


def test_evidence_presentation_fields_are_nullable_server_projections() -> None:
    document = task_contract()
    update = schema(document, "TaskLifecycleUpdate")
    assert {"resolved_address", "maps_url"} <= set(update["required"])
    assert update["properties"]["resolved_address"]["nullable"] is True
    assert update["properties"]["maps_url"] == {
        "type": "string",
        "format": "uri",
        "nullable": True,
    }
