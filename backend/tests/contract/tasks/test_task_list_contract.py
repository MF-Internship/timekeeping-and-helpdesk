from tests.contract.tasks.helpers import expanded_response_schema, task_contract


def test_grouped_list_contract_has_fixed_group_order_and_nullable_overdue() -> None:
    document = task_contract()
    operation = document["paths"]["/api/v1/tasks/"]["get"]
    assert operation["operationId"] == "tasks_list"
    grouped = expanded_response_schema(document, "/api/v1/tasks/", "get", "200")
    assert set(grouped["required"]) == {
        "business_date",
        "overdue",
        "today",
        "upcoming",
        "completed",
    }
    assert "overdue_days" in str(grouped)
