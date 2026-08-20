from tests.contract.tasks.helpers import expanded_response_schema, request_schema, task_contract


def test_status_contract_excludes_completed_and_declares_noop_success() -> None:
    document = task_contract()
    path = "/api/v1/tasks/{task_id}/status"
    operation = document["paths"][path]["post"]
    assert operation["operationId"] == "tasks_status_create"
    request = request_schema(document, path, "post")
    status = request["properties"]["status"]
    if "$ref" in status:
        name = status["$ref"].rsplit("/", 1)[-1]
        status = document["components"]["schemas"][name]
    assert set(status["enum"]) == {"TODO", "IN_PROGRESS", "BLOCKED"}
    assert set(operation["responses"]) == {"200", "400", "401", "403", "404", "422"}


def test_override_is_only_lifecycle_operation_with_completed_conflict() -> None:
    document = task_contract()
    path = "/api/v1/tasks/{task_id}/complete-override"
    operation = document["paths"][path]["post"]
    assert operation["operationId"] == "tasks_complete_override_create"
    assert set(operation["responses"]) == {"200", "400", "401", "403", "404", "409"}
    assert set(request_schema(document, path, "post")["required"]) == {"completion_note"}
    conflict = expanded_response_schema(document, path, "post", "409")
    assert conflict["properties"]["error_code"]["enum"] == ["TASK_ALREADY_COMPLETED"]
    assert "409" not in document["paths"]["/api/v1/tasks/{task_id}/status"]["post"]["responses"]
