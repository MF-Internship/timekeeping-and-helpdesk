from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/deployment_check.py", *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def test_committed_readiness_baseline_remains_non_green_without_evidence_mutation() -> None:
    inventory = Path("deploy/environments.yaml")
    evidence = Path("deploy/recovery-evidence.yaml")
    before = (inventory.read_bytes(), evidence.read_bytes())
    production = _run("production-ready")
    recovery = _run("recovery-ready")
    smoke = _run("smoke", "--status", "503")
    assert production.returncode != 0
    assert recovery.returncode != 0
    assert smoke.returncode == 0
    assert smoke.stdout.strip() == "503"
    assert (inventory.read_bytes(), evidence.read_bytes()) == before
    assert "passed" not in evidence.read_text(encoding="utf-8").casefold()
