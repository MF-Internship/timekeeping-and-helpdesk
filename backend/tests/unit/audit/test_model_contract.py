import pytest

from audit.models import AuditLog


@pytest.mark.unit
def test_audit_log_has_exact_eight_fields() -> None:
    assert [field.name for field in AuditLog._meta.fields] == [
        "id",
        "actor",
        "action",
        "target_type",
        "target_id",
        "before",
        "after",
        "recorded_at",
    ]
