from __future__ import annotations

import ast
from pathlib import Path


def test_verify_restore_command_is_owned_by_operations() -> None:
    from django.apps import apps
    from django.core.management import get_commands

    apps.set_installed_apps(["operations"])
    try:
        get_commands.cache_clear()
        assert get_commands()["verify_restore"] == "operations"
    finally:
        apps.unset_installed_apps()
        get_commands.cache_clear()


def test_command_handle_is_a_thin_delegate_without_query_or_policy_logic() -> None:
    path = Path("backend/operations/management/commands/verify_restore.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    command = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Command"
    )
    handle = next(
        node for node in command.body if isinstance(node, ast.FunctionDef) and node.name == "handle"
    )
    source = ast.unparse(handle)
    assert "verify_restore" in source
    assert "SELECT" not in source
    assert "execute(" not in source
    assert (handle.end_lineno or handle.lineno) - handle.lineno + 1 <= 20


def test_relay_outbox_command_is_a_thin_operations_delegate() -> None:
    from django.core.management import get_commands

    assert get_commands()["relay_outbox"] == "operations"
    path = Path("backend/operations/management/commands/relay_outbox.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    command = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Command"
    )
    handle = next(
        node for node in command.body if isinstance(node, ast.FunctionDef) and node.name == "handle"
    )
    source = ast.unparse(handle)
    assert "operations_container().outbox_relay.run_once" in source
    assert "select_for_update" not in source
    assert "OutboxEvent" not in source
    assert "publish_state" not in source
    assert (handle.end_lineno or handle.lineno) - handle.lineno + 1 <= 20


def test_prune_retention_command_is_a_thin_operations_delegate() -> None:
    from django.core.management import get_commands

    assert get_commands()["prune_retention"] == "operations"
    path = Path("backend/operations/management/commands/prune_retention.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    command = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Command"
    )
    handle = next(
        node for node in command.body if isinstance(node, ast.FunctionDef) and node.name == "handle"
    )
    source = ast.unparse(handle)
    assert "prune_retention" in source
    assert "OutboxEvent" not in source
    assert "ProcessedEvent" not in source
    assert "delete(" not in source
    assert (handle.end_lineno or handle.lineno) - handle.lineno + 1 <= 20


def test_reconciliation_command_is_owned_by_attendance_and_has_no_repair_arguments() -> None:
    from django.core.management import get_commands, load_command_class

    assert get_commands()["reconcile_missing_checkouts"] == "attendance"
    command = load_command_class("attendance", "reconcile_missing_checkouts")
    parser = command.create_parser("manage.py", "reconcile_missing_checkouts")
    destinations = {action.dest for action in parser._actions}
    assert destinations.isdisjoint({"date", "work_date", "repair", "session_id", "user_id"})
