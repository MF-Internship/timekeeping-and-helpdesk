from tests.contract.tasks.helpers import (
    expanded_response_schema,
    request_schema,
    response_schema,
    task_contract,
)


def test_create_operation_owns_mode_shaped_input_and_canonical_responses() -> None:
    document = task_contract()
    operation = document["paths"]["/api/v1/tasks/"]["post"]
    assert operation["operationId"] == "tasks_create"
    assert set(operation["responses"]) == {"201", "400", "401", "403", "422"}
    request = request_schema(document, "/api/v1/tasks/", "post")
    assert set(request["properties"]) == {
        "title",
        "description",
        "assigned_date",
        "location_id",
        "expected_location",
        "assignee_ids",
    }
    assert {"created_by", "status", "completed_at", "overdue_days"}.isdisjoint(
        request["properties"]
    )
    assert request["additionalProperties"] is False
    created = response_schema(document, "/api/v1/tasks/", "post", "201")
    assert "assigned_date" in created.get("properties", {}) or "allOf" in created


def test_create_eligibility_error_reports_all_ids_in_canonical_envelope() -> None:
    document = task_contract()
    error = expanded_response_schema(document, "/api/v1/tasks/", "post", "422")
    serialized = str(error)
    assert "INACTIVE_ASSIGNEE" in serialized
    assert "assignee_ids" in serialized
    assert all(field in serialized for field in ("message", "details", "request_id", "error"))
