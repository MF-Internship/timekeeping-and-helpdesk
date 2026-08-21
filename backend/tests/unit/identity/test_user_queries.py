from unittest.mock import Mock

import pytest

from identity.application.queries import PAGE_SIZE, UserFilters, UserQueryService
from identity.domain.authorization import Role
from tests.unit.identity.helpers import account


def test_query_service_forwards_combined_filters_and_offsets_stably() -> None:
    repository = Mock()
    repository.paginate_users.return_value = (PAGE_SIZE + 1, [account(user_id=PAGE_SIZE + 1)])
    service = UserQueryService(repository)
    result = service.list(UserFilters("worker", Role.HELPDESK, True), PAGE_SIZE, PAGE_SIZE)
    repository.paginate_users.assert_called_once_with(
        "worker", Role.HELPDESK, True, (PAGE_SIZE, PAGE_SIZE)
    )
    assert result.count == PAGE_SIZE + 1
    assert [item.id for item in result.results] == [PAGE_SIZE + 1]


@pytest.mark.parametrize("count,offset,limit", [(0, -1, PAGE_SIZE), (1, 1, PAGE_SIZE), (1, 0, 0)])
def test_query_service_rejects_invalid_offsets(count: int, offset: int, limit: int) -> None:
    repository = Mock()
    repository.paginate_users.return_value = (count, [])
    with pytest.raises(ValueError, match="pagination"):
        UserQueryService(repository).list(UserFilters(), offset, limit)
