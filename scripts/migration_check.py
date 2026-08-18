from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from core.event_payload import sanitize_failure_reason  # noqa: E402

_DESTRUCTIVE = {
    "RemoveField",
    "RemoveModel",
    "RenameField",
    "RenameModel",
    "AlterField",
}
_EXPANSION = {"AddField", "CreateModel"}
_ALLOWED_OWNERS = frozenset({"operations", "identity", "audit", "locations"})


@dataclass(frozen=True, slots=True)
class Finding:
    rule: str
    path: str
    line: int


def check_tree(root: Path) -> list[Finding]:
    files = sorted(
        path for path in root.rglob("*.py") if _is_migration_source(root, path)
    )
    findings: list[Finding] = []
    graphs: dict[str, dict[str, set[str]]] = {}
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        owner = path.parts[path.parts.index("migrations") - 1]
        if owner not in _ALLOWED_OWNERS:
            findings.append(Finding("MIGRATION-OWNER", str(path), 1))
        dependencies = _dependencies(tree, owner)
        graphs.setdefault(owner, {})[path.stem] = dependencies
        findings.extend(_check_operations(path, tree, owner))
    findings.extend(_leaf_findings(graphs, files))
    return findings


def _is_migration_source(root: Path, path: Path) -> bool:
    relative_parts = path.relative_to(root).parts
    excluded = {".venv", "tests", "__pycache__"}
    return (
        "migrations" in relative_parts
        and path.name != "__init__.py"
        and not excluded.intersection(relative_parts)
    )


def _dependencies(tree: ast.Module, owner: str) -> set[str]:
    dependencies: set[str] = set()
    for node in ast.walk(tree):
        for item in _dependency_items(node):
            dependency = _local_dependency(item, owner)
            if dependency:
                dependencies.add(dependency)
    return dependencies


def _dependency_items(node: ast.AST) -> list[ast.expr]:
    if not isinstance(node, ast.Assign):
        return []
    is_dependency = any(
        isinstance(target, ast.Name) and target.id == "dependencies"
        for target in node.targets
    )
    if not is_dependency or not isinstance(node.value, ast.List | ast.Tuple):
        return []
    return list(node.value.elts)


def _local_dependency(node: ast.AST, owner: str) -> str | None:
    if not isinstance(node, ast.Tuple) or len(node.elts) != 2:
        return None
    app = _literal(node.elts[0])
    name = _literal(node.elts[1])
    return name if app == owner and isinstance(name, str) else None


def _check_operations(path: Path, tree: ast.Module, owner: str) -> list[Finding]:
    findings: list[Finding] = []
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    operation_names = {_call_name(call) for call in calls}
    release_phase = _release_phase(tree)
    if operation_names & _DESTRUCTIVE and release_phase != "contract":
        findings.append(Finding("MIGRATION-RELEASE-PHASE", str(path), 1))
    if operation_names & _DESTRUCTIVE and operation_names & _EXPANSION:
        findings.append(Finding("MIGRATION-MIXED-PHASE", str(path), 1))
    for call in calls:
        if _call_name(call) == "AddField" and _required_without_database_default(call):
            findings.append(Finding("MIGRATION-DB-DEFAULT", str(path), call.lineno))
    source_names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    literals = {
        _literal(node) for node in ast.walk(tree) if isinstance(node, ast.Constant)
    }
    if "createcachetable" in literals and (
        owner != "operations" or "THROTTLE_CACHE_TABLE" not in source_names
    ):
        findings.append(Finding("MIGRATION-CACHE-IDENTITY", str(path), 1))
    return findings


def _required_without_database_default(call: ast.Call) -> bool:
    field = next(
        (keyword.value for keyword in call.keywords if keyword.arg == "field"), None
    )
    if not isinstance(field, ast.Call):
        return False
    keywords = {keyword.arg: keyword.value for keyword in field.keywords}
    nullable = _literal(keywords.get("null")) is True
    return not nullable and "db_default" not in keywords


def _release_phase(tree: ast.Module) -> str | None:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "RELEASE_PHASE"
            for target in node.targets
        ):
            value = _literal(node.value)
            return value if isinstance(value, str) else None
    return None


def _leaf_findings(
    graphs: dict[str, dict[str, set[str]]], files: list[Path]
) -> list[Finding]:
    findings: list[Finding] = []
    for owner, graph in graphs.items():
        depended_on = {
            dependency for dependencies in graph.values() for dependency in dependencies
        }
        leaves = set(graph) - depended_on
        if len(leaves) > 1:
            path = next(path for path in files if owner in path.parts)
            findings.append(Finding("MIGRATION-LEAF", str(path), 1))
    return findings


def _call_name(call: ast.Call) -> str:
    return call.func.attr if isinstance(call.func, ast.Attribute) else ""


def _literal(node: ast.AST | None) -> str | bool | None:
    return (
        node.value
        if isinstance(node, ast.Constant) and isinstance(node.value, str | bool)
        else None
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["check"])
    parser.add_argument("--root", type=Path, default=ROOT / "backend")
    findings = check_tree(parser.parse_args().root)
    for finding in findings:
        path = sanitize_failure_reason(finding.path)
        print(f"{finding.rule}: {path}:{finding.line}", file=sys.stderr)
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
