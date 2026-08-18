from unittest.mock import Mock

import pytest

from identity.application.queries import PAGE_SIZE, UserFilters, UserQueryService
from identity.domain.authorization import Role
from tests.unit.identity.helpers import account


def test_query_service_forwards_combined_filters_and_pages_stably() -> None:
    repository = Mock()
    repository.list_users.return_value = [
        account(user_id=index) for index in range(1, PAGE_SIZE + 2)
    ]
    service = UserQueryService(repository)
    result = service.list(UserFilters("worker", Role.HELPDESK, True), 2)
    repository.list_users.assert_called_once_with("worker", Role.HELPDESK, True)
    assert result.count == PAGE_SIZE + 1
    assert [item.id for item in result.results] == [PAGE_SIZE + 1]


@pytest.mark.parametrize("records,page", [([], 2), ([account()], 0), ([account()], 2)])
def test_query_service_rejects_out_of_range_pages(records: list[object], page: int) -> None:
    repository = Mock()
    repository.list_users.return_value = records
    with pytest.raises(ValueError, match="page"):
        UserQueryService(repository).list(UserFilters(), page)
