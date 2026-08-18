from pathlib import Path

from audit.models import AuditLog, OutboxEvent


def test_recording_adapter_joins_ambient_transaction_and_filters_columns() -> None:
    source = (Path(__file__).parents[3] / "audit/adapters/persistence/recording.py").read_text(
        encoding="utf-8"
    )
    assert "transaction.atomic" not in source
    assert "on_commit" not in source
    assert "request_id, correlation_id = get_correlation()" in source
    assert {field.name for field in AuditLog._meta.fields} == {
        "id",
        "actor",
        "action",
        "target_type",
        "target_id",
        "before",
        "after",
        "recorded_at",
    }
    assert "aggregate_version=latest + 1" in source
    assert "pg_advisory_xact_lock" not in source
    assert "refresh" not in {field.name for field in OutboxEvent._meta.fields}
