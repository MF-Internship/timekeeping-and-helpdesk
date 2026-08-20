from tests.contract.tasks.helpers import response_schema, task_contract


def test_detail_contract_has_history_and_minimal_identity_projection() -> None:
    document = task_contract()
    path = "/api/v1/tasks/{task_id}/"
    operation = document["paths"][path]["get"]
    assert operation["operationId"] == "tasks_retrieve"
    assert set(operation["responses"]) == {"200", "401", "403", "404"}
    assert operation["parameters"][0]["schema"]["type"] == "string"
    detail = response_schema(document, path, "get", "200")
    assert "updates" in str(detail)
    task_user = document["components"]["schemas"]["TaskUser"]
    assert set(task_user["properties"]) == {"id", "full_name"}
    assert {"username", "is_active"}.isdisjoint(task_user["properties"])
