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
BUSINESS_CORE_NAMES = ("Attendance", "Task", "Location", "Report", "Notification")


@dataclass(frozen=True, slots=True)
class Finding:
    rule_id: str
    path: Path
    line: int


def check_file(path: Path) -> list[Finding]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    findings: list[Finding] = []
    is_domain = "domain" in path.parts or path.name == "domain_framework.py"
    is_adapter = "adapters" in path.parts
    is_controlled_fixture = "fixtures" in path.parts
    is_exempt = (
        ("tests" in path.parts and not is_controlled_fixture)
        or "migrations" in path.parts
        or "config" in path.parts
    )
    for node in ast.walk(tree):
        module = _imported_module(node)
        if module is not None and is_domain and module.startswith(FRAMEWORK_PREFIXES):
            findings.append(Finding("ARCH-DOMAIN-FRAMEWORK", path, _line(node)))
        if module is not None and not is_adapter and ".adapters" in module:
            findings.append(Finding("ARCH-INWARD", path, _line(node)))
        if module is not None and not is_exempt and _imports_internal_module(module):
            findings.append(Finding("ARCH-CROSS-MODULE", path, _line(node)))
        if _is_business_class_in_core(node, path):
            findings.append(Finding("ARCH-CORE-OWNERSHIP", path, _line(node)))
    return _deduplicate(findings)


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


def _imports_internal_module(module: str) -> bool:
    parts = module.split(".")
    return len(parts) > 1 and any(part in INTERNAL_MODULE_NAMES for part in parts[1:])


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
