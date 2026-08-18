from __future__ import annotations

from datetime import date

import pytest
from django.db import IntegrityError, connection, transaction

from locations.models import Holiday


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_holiday_unique_nonblank_and_index() -> None:
    Holiday.objects.create(date=date(2027, 1, 1), name="New year")
    for name, value_date in (("Duplicate", date(2027, 1, 1)), ("   ", date(2027, 1, 2))):
        with pytest.raises(IntegrityError), transaction.atomic():
            Holiday.objects.create(date=value_date, name=name)
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, Holiday._meta.db_table)
    assert constraints["holiday_date_id_idx"]["index"] is True
    assert not [value for value in constraints.values() if value.get("foreign_key")]
