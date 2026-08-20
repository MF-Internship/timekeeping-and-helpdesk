import pytest
from django.db import connection

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.postgres]


def test_reconciliation_partial_index_and_open_uniqueness_have_canonical_predicate() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT indexname, indexdef FROM pg_indexes "
            "WHERE schemaname = current_schema() AND tablename = 'attendance_attendancesession'"
        )
        indexes = dict(cursor.fetchall())
    reconciliation = indexes["attendance_reconcile_idx"]
    assert "(work_date, id)" in reconciliation
    assert "check_out_id IS NULL" in reconciliation
    assert "NOT closed_by_job" in reconciliation
    open_unique = indexes["uniq_open_session_per_user"]
    assert "check_out_id IS NULL" in open_unique
    assert "NOT closed_by_job" in open_unique
