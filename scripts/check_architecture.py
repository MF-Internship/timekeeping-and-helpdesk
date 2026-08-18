from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from core.event_payload import sanitize_failure_reason  # noqa: E402

FRAMEWORK_PREFIXES = ("django", "rest_framework", "psycopg", "boto3")
INTERNAL_MODULE_NAMES = frozenset({"models", "domain", "adapters"})
BUSINESS_MODULE_NAMES = frozenset(
    {"identity", "audit", "operations", "locations", "attendance"}
)
BUSINESS_CORE_NAMES = ("Attendance", "Task", "Location", "Report", "Notification")


@dataclass(frozen=True, slots=True)
class Finding:
    rule_id: str
    path: Path
    line: int


@dataclass(frozen=True, slots=True)
class FileContext:
    path: Path
    is_domain: bool
    is_adapter: bool
    owner: str | None
    is_controlled_fixture: bool
    is_exempt: bool


def check_file(path: Path) -> list[Finding]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    context = _file_context(path)
    findings = [
        finding for node in ast.walk(tree) for finding in _node_findings(node, context)
    ]
    return _deduplicate(findings)


def _file_context(path: Path) -> FileContext:
    is_controlled_fixture = "fixtures" in path.parts
    is_exempt = (
        ("tests" in path.parts and not is_controlled_fixture)
        or "migrations" in path.parts
        or "config" in path.parts
    )
    return FileContext(
        path,
        "domain" in path.parts or path.name == "domain_framework.py",
        "adapters" in path.parts,
        _business_owner(path),
        is_controlled_fixture,
        is_exempt,
    )


def _node_findings(node: ast.AST, context: FileContext) -> list[Finding]:
    module = _imported_module(node)
    rules = []
    if (
        module is not None
        and context.is_domain
        and module.startswith(FRAMEWORK_PREFIXES)
    ):
        rules.append("ARCH-DOMAIN-FRAMEWORK")
    if module is not None and not context.is_adapter and not context.is_exempt:
        if ".adapters" in module:
            rules.append("ARCH-INWARD")
        if _imports_cross_module_internal(
            module, context.owner, context.is_controlled_fixture
        ):
            rules.append("ARCH-CROSS-MODULE")
    if _is_business_class_in_core(node, context.path):
        rules.append("ARCH-CORE-OWNERSHIP")
    return [Finding(rule, context.path, _line(node)) for rule in rules]


def check_path(path: Path) -> list[Finding]:
    files = [path] if path.is_file() else sorted(path.rglob("*.py"))
    return [finding for file_path in files for finding in check_file(file_path)]


def _imported_module(node: ast.AST) -> str | None:
    if isinstance(node, ast.ImportFrom):
        return node.module or ""
    if isinstance(node, ast.Import) and node.names:
        return node.names[0].name
    return None


def _line(node: ast.AST) -> int:
    return getattr(node, "lineno", 1)


def _business_owner(path: Path) -> str | None:
    return next((part for part in path.parts if part in BUSINESS_MODULE_NAMES), None)


def _imports_cross_module_internal(
    module: str, owner: str | None, is_controlled_fixture: bool
) -> bool:
    parts = module.split(".")
    if len(parts) < 2 or not any(part in INTERNAL_MODULE_NAMES for part in parts[1:]):
        return False
    imported_owner = parts[0]
    if owner is not None:
        return imported_owner in BUSINESS_MODULE_NAMES and imported_owner != owner
    return is_controlled_fixture


def _is_business_class_in_core(node: ast.AST, path: Path) -> bool:
    return (
        isinstance(node, ast.ClassDef)
        and ("core" in path.parts or path.name == "oversized_core.py")
        and node.name.startswith(BUSINESS_CORE_NAMES)
    )


def _deduplicate(findings: list[Finding]) -> list[Finding]:
    return list(dict.fromkeys(findings))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    arguments = parser.parse_args()
    findings = check_path(arguments.path)
    for finding in findings:
        path = sanitize_failure_reason(finding.path)
        print(f"{finding.rule_id}: {path}:{finding.line}", file=sys.stderr)
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
