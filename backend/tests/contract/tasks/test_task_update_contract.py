from tests.contract.tasks.helpers import request_schema, task_contract


def test_patch_contract_owns_only_mutable_content_and_desired_assignee_set() -> None:
    document = task_contract()
    path = "/api/v1/tasks/{task_id}/"
    operation = document["paths"][path]["patch"]
    assert operation["operationId"] == "tasks_partial_update"
    request = request_schema(document, path, "patch")
    assert set(request["properties"]) == {
        "title",
        "description",
        "location_id",
        "expected_location",
        "assignee_ids",
    }
    assert {
        "assigned_date",
        "status",
        "completed_by",
        "completed_at",
        "completion_method",
        "completion_note",
        "block_reason",
    }.isdisjoint(request["properties"])
    assert set(operation["responses"]) == {"200", "400", "401", "403", "404", "422"}


def test_delete_contract_is_bodyless_and_keeps_canonical_denials() -> None:
    operation = task_contract()["paths"]["/api/v1/tasks/{task_id}/"]["delete"]

    assert operation["operationId"] == "tasks_destroy"
    assert "requestBody" not in operation
    assert set(operation["responses"]) == {"204", "400", "401", "403", "404", "409"}
