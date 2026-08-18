import pytest

from tests.integration.api.identity.helpers import create_user, manager_client


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
def test_manager_directory_combines_filters_and_keeps_manager_targets_visible() -> None:
    api, manager = manager_client("query-manager")
    worker = create_user("query-worker", active=False)
    response = api.get("/api/v1/users/?q=query&role=HELPDESK&is_active=false")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["results"]] == [worker.pk]
    assert api.get(f"/api/v1/users/{manager.pk}/").status_code == 200


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
@pytest.mark.parametrize("query", ["role=ADMIN", "is_active=maybe", "page=0"])
def test_invalid_directory_filters_are_validation_failures(query: str) -> None:
    api, _manager = manager_client(f"filter-{query.split('=')[0]}")
    response = api.get(f"/api/v1/users/?{query}")
    assert response.status_code == 400
    assert response.json()["error_code"] == "VALIDATION_FAILED"
