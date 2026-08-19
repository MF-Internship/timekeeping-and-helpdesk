from collections.abc import Callable
from dataclasses import fields

import pytest

from attendance.application.reconciliation import ReconciliationDependencies


@pytest.mark.unit
def test_reconciliation_dependencies_are_consumer_owned_ports() -> None:
    assert {field.name for field in fields(ReconciliationDependencies)} == {
        "clock",
        "repository",
        "job_runs",
        "unit_of_work_factory",
    }
    assert Callable
