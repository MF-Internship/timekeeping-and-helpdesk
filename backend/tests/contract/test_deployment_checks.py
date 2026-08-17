from __future__ import annotations

import subprocess
import sys
from pathlib import Path

DEPLOYMENT = Path(__file__).parent / "fixtures/deployment"
RECOVERY = Path(__file__).parent / "fixtures/recovery"


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/deployment_check.py", *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def test_isolated_inventory_passes_and_duplicate_identity_fails() -> None:
    safe = _run("isolation", "--inventory", str(DEPLOYMENT / "isolated.yaml"))
    duplicate = _run("isolation", "--inventory", str(DEPLOYMENT / "duplicate.yaml"))
    assert safe.returncode == 0, safe.stderr
    assert duplicate.returncode != 0
    assert "DEPLOY-IDENTITY" in duplicate.stderr
    assert "environments.staging.database_identity" in duplicate.stderr


def test_committed_inventory_is_source_valid_but_not_production_ready() -> None:
    isolation = _run("isolation", "--inventory", "deploy/environments.yaml")
    readiness = _run("production-ready", "--inventory", "deploy/environments.yaml")
    assert isolation.returncode == 0, isolation.stderr
    assert readiness.returncode != 0
    assert "UNRESOLVED" not in readiness.stderr


def test_protected_inventory_diagnostic_is_sanitized() -> None:
    result = _run("isolation", "--inventory", str(DEPLOYMENT / "protected.yaml"))
    assert result.returncode != 0
    assert "user:password" not in result.stderr
    assert "example.invalid" not in result.stderr


def test_production_and_recovery_readiness_fail_closed() -> None:
    production = _run("production-ready", "--inventory", "deploy/environments.yaml")
    recovery = _run("recovery-ready", "--evidence", str(RECOVERY / "unresolved.yaml"))
    missing_owner = _run(
        "recovery-ready", "--evidence", str(RECOVERY / "failed_without_owner.yaml")
    )
    assert production.returncode != 0
    assert recovery.returncode != 0
    assert missing_owner.returncode != 0
    assert "drill.status" in recovery.stderr
    assert "drill.remediation_owner" in missing_owner.stderr


def test_recovery_readiness_rejects_stale_and_target_exceeding_evidence() -> None:
    stale = _run("recovery-ready", "--evidence", str(RECOVERY / "stale.yaml"))
    exceeded = _run("recovery-ready", "--evidence", str(RECOVERY / "target_exceeded.yaml"))
    assert stale.returncode != 0
    assert "drill.recorded_at" in stale.stderr
    assert "capacity.recorded_at" in stale.stderr
    assert exceeded.returncode != 0
    for path in (
        "drill.measured_rpo_hours",
        "drill.measured_rto_hours",
        "capacity.distinct_identities",
        "capacity.concurrency",
        "capacity.measured_p95_ms",
    ):
        assert path in exceeded.stderr


def test_smoke_prints_status_only_without_body() -> None:
    result = _run("smoke", "--status", "403")
    assert result.returncode == 0
    assert result.stdout.strip() == "403"
    assert result.stderr == ""
