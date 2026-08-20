import ast
from pathlib import Path

from audit.models import AuditLog, OutboxEvent


def _append_methods() -> list[ast.FunctionDef]:
    source = (Path(__file__).parents[3] / "audit/adapters/persistence/recording.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    methods: list[ast.FunctionDef] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("append_"):
            methods.append(node)
    return methods


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


def test_append_ports_do_not_own_transactions() -> None:
    methods = _append_methods()
    assert {method.name for method in methods} == {"append_audit_entry", "append_outbox_event"}
    for method in methods:
        source = ast.unparse(method)
        assert "transaction.atomic" not in source
        assert "on_commit" not in source
