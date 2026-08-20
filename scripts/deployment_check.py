from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from core.cache import (  # noqa: E402
    CACHE_BACKEND_CHOICES,
    cache_backend_path,
    is_process_local_backend,
)
from core.event_payload import sanitize_failure_reason  # noqa: E402

ENVIRONMENT_NAMES = ("development", "staging", "production")
IDENTITY_FIELDS = (
    "database_identity",
    "migration_identity",
    "bucket_identity",
    "cache_queue_namespace",
    "signing_key_identity",
    "credential_identity",
)
PRODUCTION_FIELDS = (
    *IDENTITY_FIELDS,
    "backup.plan",
    "backup.pitr_retention_days",
    "backup.mechanism",
    "backup.daily_schedule_utc",
    "backup.retention_days",
    "backup.restore_project_ref",
    "backup.alert_owner",
)
RECONCILIATION_JOB = {
    "name": "missing-check-out-reconciliation",
    "working_directory": "backend",
    "command": "python manage.py reconcile_missing_checkouts",
    "cron": "15 0 * * *",
    "timezone": "Asia/Ho_Chi_Minh",
    "calendar": "every_day",
    "singleton_per_environment": True,
}


def validate_cache_inventory(document: object) -> list[str]:
    findings: list[str] = []
    environments = _environments(document)
    for environment_name in ENVIRONMENT_NAMES:
        path = f"environments.{environment_name}.cache.backend"
        environment = _mapping(environments.get(environment_name))
        choice = _mapping(environment.get("cache")).get("backend")
        if choice not in CACHE_BACKEND_CHOICES or (
            environment_name != "development"
            and is_process_local_backend(cache_backend_path(str(choice)))
        ):
            findings.append(path)
    return findings


def validate_inventory(document: object) -> list[tuple[str, str]]:
    findings = [("DEPLOY-CACHE", path) for path in validate_cache_inventory(document)]
    environments = _environments(document)
    if set(environments) != set(ENVIRONMENT_NAMES):
        findings.append(("DEPLOY-ENVIRONMENTS", "environments"))
    findings.extend(_identity_findings(environments))
    return findings


def _identity_findings(environments: Mapping[Any, Any]) -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    seen: set[str] = set()
    for environment_name in ENVIRONMENT_NAMES:
        environment = _mapping(environments.get(environment_name))
        for field in IDENTITY_FIELDS:
            findings.extend(
                _identity_value_findings(environment_name, field, environment, seen)
            )
        findings.extend(_database_separation_findings(environment_name, environment))
    return findings


def _identity_value_findings(
    environment_name: str,
    field: str,
    environment: Mapping[Any, Any],
    seen: set[str],
) -> list[tuple[str, str]]:
    path = f"environments.{environment_name}.{field}"
    value = environment.get(field)
    if not isinstance(value, str) or not value or "://" in value:
        return [("DEPLOY-IDENTITY", path)]
    if value == "UNRESOLVED":
        return []
    if value in seen:
        return [("DEPLOY-IDENTITY", path)]
    seen.add(value)
    return []


def _database_separation_findings(
    environment_name: str, environment: Mapping[Any, Any]
) -> list[tuple[str, str]]:
    database_identity = environment.get("database_identity")
    migration_identity = environment.get("migration_identity")
    if database_identity != "UNRESOLVED" and database_identity == migration_identity:
        return [("DEPLOY-DATABASE-SEPARATION", f"environments.{environment_name}")]
    return []


def production_readiness(document: object) -> list[str]:
    production = _mapping(_environments(document).get("production"))
    return [
        f"environments.production.{path}"
        for path in PRODUCTION_FIELDS
        if _nested(production, path) in (None, "", "UNRESOLVED")
    ]


def recovery_readiness(document: object) -> list[str]:
    findings: list[str] = []
    document_map = _mapping(document)
    targets = _mapping(document_map.get("targets"))
    for section in ("drill", "capacity"):
        entry = _mapping(document_map.get(section))
        status = entry.get("status")
        if status != "passed":
            findings.append(f"{section}.status")
        if status == "failed" and entry.get("remediation_owner") in (
            None,
            "",
            "UNRESOLVED",
        ):
            findings.append(f"{section}.remediation_owner")
        if status == "passed" and _is_stale(entry.get("recorded_at")):
            findings.append(f"{section}.recorded_at")
    findings.extend(
        _target_findings(targets, _mapping(document_map.get("drill")), "drill")
    )
    findings.extend(
        _target_findings(targets, _mapping(document_map.get("capacity")), "capacity")
    )
    return findings


def scheduled_jobs_readiness(
    jobs_document: object, inventory_document: object
) -> list[str]:
    findings: list[str] = []
    matching = _matching_entries(_mapping(jobs_document).get("jobs"), "name")
    if len(matching) != 1:
        findings.append("jobs.missing-check-out-reconciliation")
    elif any(
        matching[0].get(key) != value for key, value in RECONCILIATION_JOB.items()
    ):
        findings.append("jobs.missing-check-out-reconciliation.contract")
    environments = _environments(inventory_document)
    identities: set[str] = set()
    for environment_name in ("staging", "production"):
        findings.extend(_binding_findings(environments, environment_name, identities))
    return findings


def _matching_entries(value: object, field: str) -> list[Mapping[Any, Any]]:
    if not isinstance(value, list):
        return []
    return [
        item
        for item in value
        if isinstance(item, Mapping) and item.get(field) == RECONCILIATION_JOB["name"]
    ]


def _binding_findings(
    environments: Mapping[Any, Any], environment_name: str, identities: set[str]
) -> list[str]:
    bindings = _mapping(environments.get(environment_name)).get("scheduled_jobs")
    selected = _matching_entries(bindings, "job")
    path = f"environments.{environment_name}.scheduled_jobs"
    if len(selected) != 1 or selected[0].get("enabled") is not True:
        return [path]
    identity = selected[0].get("scheduler_identity")
    if not isinstance(identity, str) or not identity or identity == "UNRESOLVED":
        return [f"{path}.scheduler_identity"]
    if identity in identities:
        return [f"{path}.scheduler_identity"]
    identities.add(identity)
    return []


def _is_stale(value: object) -> bool:
    if not isinstance(value, str):
        return True
    try:
        recorded = datetime.fromisoformat(value)
    except ValueError:
        return True
    if recorded.tzinfo is None:
        return True
    return datetime.now(UTC) - recorded.astimezone(UTC) > timedelta(days=90)


def _target_findings(
    targets: Mapping[Any, Any],
    entry: Mapping[Any, Any],
    section: str,
) -> list[str]:
    if entry.get("status") != "passed":
        return []
    checks = (
        (("measured_rpo_hours", "rpo_hours"), "maximum"),
        (("measured_rto_hours", "rto_hours"), "maximum"),
        (("measured_p95_ms", "capacity_p95_ms"), "maximum"),
        (("distinct_identities", None), "minimum-50"),
        (("concurrency", None), "minimum-20"),
    )
    findings: list[str] = []
    for (field, target), rule in checks:
        limit = (
            targets.get(target)
            if target
            else (50 if field == "distinct_identities" else 20)
        )
        if field in entry and _target_value_is_invalid(
            entry.get(field), limit, rule == "maximum"
        ):
            findings.append(f"{section}.{field}")
    return findings


def _target_value_is_invalid(value: object, limit: object, maximum: bool) -> bool:
    if not isinstance(value, int | float) or not isinstance(limit, int | float):
        return True
    if maximum:
        return value > limit
    return value < limit


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def _print_findings(findings: list[tuple[str, str]]) -> int:
    for rule, path in findings:
        print(f"{rule}: {sanitize_failure_reason(path)}", file=sys.stderr)
    return int(bool(findings))


def _mapping(value: object) -> Mapping[Any, Any]:
    return value if isinstance(value, Mapping) else {}


def _environments(document: object) -> Mapping[Any, Any]:
    return _mapping(_mapping(document).get("environments"))


def _nested(document: Mapping[Any, Any], path: str) -> object:
    value: object = document
    for part in path.split("."):
        value = _mapping(value).get(part)
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("isolation", "production-ready"):
        child = subparsers.add_parser(command)
        child.add_argument(
            "--inventory", type=Path, default=ROOT / "deploy/environments.yaml"
        )
    recovery = subparsers.add_parser("recovery-ready")
    recovery.add_argument(
        "--evidence", type=Path, default=ROOT / "deploy/recovery-evidence.yaml"
    )
    smoke = subparsers.add_parser("smoke")
    scheduled = subparsers.add_parser("scheduled-jobs-ready")
    scheduled.add_argument(
        "--jobs", type=Path, default=ROOT / "deploy/scheduled-jobs.yaml"
    )
    scheduled.add_argument(
        "--inventory", type=Path, default=ROOT / "deploy/environments.yaml"
    )
    smoke.add_argument("--status", required=True)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    if arguments.command == "isolation":
        return _print_findings(validate_inventory(load_yaml(arguments.inventory)))
    if arguments.command == "production-ready":
        paths = production_readiness(load_yaml(arguments.inventory))
        return _print_findings([("DEPLOY-NOT-READY", path) for path in paths])
    if arguments.command == "recovery-ready":
        paths = recovery_readiness(load_yaml(arguments.evidence))
        return _print_findings([("RECOVERY-NOT-READY", path) for path in paths])
    if arguments.command == "scheduled-jobs-ready":
        paths = scheduled_jobs_readiness(
            load_yaml(arguments.jobs), load_yaml(arguments.inventory)
        )
        return _print_findings([("SCHEDULE-NOT-READY", path) for path in paths])
    print(sanitize_failure_reason(arguments.status))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
