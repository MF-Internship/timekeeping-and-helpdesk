from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from core.event_payload import sanitize_failure_reason  # noqa: E402

_SNAKE_CASE = re.compile(r"^[a-z_][a-z0-9_]*$")
_CONTROL_NODES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.With,
    ast.AsyncWith,
)


@dataclass(frozen=True, slots=True)
class Finding:
    rule: str
    path: str
    line: int


def is_generated_exclusion(path: Path) -> bool:
    normalized = path.as_posix().lstrip("./")
    return normalized.endswith("contracts/openapi.yaml") or normalized.endswith(
        "frontend/src/shared/api/schema.ts"
    )


def check_paths(paths: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in _python_files(paths):
        if is_generated_exclusion(path):
            continue
        findings.extend(_check_python(path))
    for path in _typescript_files(paths):
        if _is_thin_client(path):
            findings.extend(_check_thin_client(path))
    return findings


def _python_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(
                candidate
                for candidate in path.rglob("*.py")
                if not _excluded_directory_candidate(path, candidate)
            )
        elif path.suffix == ".py":
            files.append(path)
    return sorted(files)


def _excluded_directory_candidate(root: Path, candidate: Path) -> bool:
    excluded_parts = {".venv", "__pycache__", "migrations", "tests"}
    return bool(excluded_parts.intersection(candidate.relative_to(root).parts))


def _typescript_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(
                candidate
                for candidate in path.rglob("*.ts")
                if not is_generated_exclusion(candidate)
            )
        elif path.suffix in {".ts", ".tsx"} and not is_generated_exclusion(path):
            files.append(path)
    return sorted(files)


def _is_thin_client(path: Path) -> bool:
    return path.as_posix().endswith("frontend/src/shared/api/client.ts")


def _check_thin_client(path: Path) -> list[Finding]:
    source = path.read_text(encoding="utf-8")
    endpoint_logic = re.search(r"\.(?:GET|POST|PUT|PATCH|DELETE)\s*\(", source)
    business_path = re.search(r"['\"]\/api\/v1\/[^'\"]+", source)
    explicit_any = re.search(r"\bany\b", source)
    if not (endpoint_logic or business_path or explicit_any):
        return []
    match = endpoint_logic or business_path or explicit_any
    line = source.count("\n", 0, match.start()) + 1 if match else 1
    return [Finding("MAINT-THIN-CLIENT", str(path), line)]


def _check_python(path: Path) -> list[Finding]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: dict[str, Finding] = {}
    if path.stem != "__init__" and not _SNAKE_CASE.fullmatch(path.stem):
        found["MAINT-NAMING"] = Finding("MAINT-NAMING", str(path), 1)
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        checks = _function_checks(node)
        for rule in checks:
            found.setdefault(rule, Finding(rule, str(path), node.lineno))
    return list(found.values())


def _function_checks(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    rules: list[str] = []
    if not _SNAKE_CASE.fullmatch(node.name):
        rules.append("MAINT-NAMING")
    if (node.end_lineno or node.lineno) - node.lineno + 1 > 30:
        rules.append("MAINT-FUNCTION-LENGTH")
    arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    if len(arguments) > 4:
        rules.append("MAINT-PARAMETERS")
    if _max_depth(node.body) > 3:
        rules.append("MAINT-NESTING")
    if _complexity(node) > 8:
        rules.append("MAINT-COMPLEXITY")
    return rules


def _max_depth(nodes: list[ast.stmt], depth: int = 0) -> int:
    maximum = depth
    for node in nodes:
        next_depth = depth + 1 if isinstance(node, _CONTROL_NODES) else depth
        maximum = max(maximum, next_depth)
        child_statements = [
            child for child in ast.iter_child_nodes(node) if isinstance(child, ast.stmt)
        ]
        maximum = max(maximum, _max_depth(child_statements, next_depth))
    return maximum


def _complexity(node: ast.AST) -> int:
    branching = (
        ast.If,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.ExceptHandler,
        ast.IfExp,
        ast.Match,
    )
    return 1 + sum(isinstance(child, branching) for child in ast.walk(node))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    findings = check_paths(parser.parse_args().paths)
    for finding in findings:
        path = sanitize_failure_reason(finding.path)
        print(f"{finding.rule}: {path}:{finding.line}", file=sys.stderr)
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
