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
