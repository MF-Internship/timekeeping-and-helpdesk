from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from scripts.deployment_check import scheduled_jobs_readiness, validate_inventory


def test_feature003_reference_data_release_order_is_mandatory() -> None:
    text = Path("docs/TRIEN_KHAI.md").read_text(encoding="utf-8")
    positions = [
        text.index(value)
        for value in (
            "migration before rollout",
            "initialize_location_config",
            "seed_locations",
            "verify_location_reference_ready",
            "enable route/UI Feature 003",
        )
    ]
    assert positions == sorted(positions)
    assert "Chỉ exit code `0`" in text


def test_feature004_attendance_enablement_reuses_read_only_readiness_gate() -> None:
    text = Path("docs/TRIEN_KHAI.md").read_text(encoding="utf-8")
    assert text.index("verify_location_reference_ready") < text.index(
        "enable route/UI Feature 004 Attendance"
    )
    assert "không sửa Config, Location hoặc Attendance" in text


def test_feature005_daily_scheduler_contract_and_bindings_are_ready() -> None:
    jobs = yaml.safe_load(Path("deploy/scheduled-jobs.yaml").read_text(encoding="utf-8"))
    inventory = yaml.safe_load(Path("deploy/environments.yaml").read_text(encoding="utf-8"))
    assert scheduled_jobs_readiness(jobs, inventory) == []
    text = Path("docs/TRIEN_KHAI.md").read_text(encoding="utf-8")
    for required in ("00:15", "Asia/Ho_Chi_Minh", "trước** 01:00", "unknown", "rollback"):
        assert required in text


@pytest.mark.parametrize("defect", ["missing", "duplicate", "disabled", "unresolved", "drifted"])
def test_scheduler_checker_reports_stable_safe_findings(defect: str) -> None:
    jobs = yaml.safe_load(Path("deploy/scheduled-jobs.yaml").read_text(encoding="utf-8"))
    inventory = yaml.safe_load(Path("deploy/environments.yaml").read_text(encoding="utf-8"))
    binding = inventory["environments"]["staging"]["scheduled_jobs"][0]
    if defect == "missing":
        inventory["environments"]["staging"]["scheduled_jobs"] = []
    elif defect == "duplicate":
        inventory["environments"]["production"]["scheduled_jobs"][0]["scheduler_identity"] = (
            binding["scheduler_identity"]
        )
    elif defect == "disabled":
        binding["enabled"] = False
    elif defect == "unresolved":
        binding["scheduler_identity"] = "UNRESOLVED"
    else:
        jobs["jobs"][0]["cron"] = "0 0 * * *"
    findings = scheduled_jobs_readiness(jobs, inventory)
    assert findings
    assert all("secret" not in finding.lower() for finding in findings)


def test_web_push_egress_and_secret_identities_are_explicit() -> None:
    inventory = yaml.safe_load(Path("deploy/environments.yaml").read_text(encoding="utf-8"))

    assert validate_inventory(inventory) == []
    for environment_name in ("staging", "production"):
        environment = inventory["environments"][environment_name]
        assert environment["web_push_allowed_origins"]
        assert environment["web_push_vapid_key_identity"] != "UNRESOLVED"
        assert environment["push_subscription_encryption_key_identity"] != "UNRESOLVED"


def test_web_push_egress_rejects_arbitrary_urls() -> None:
    inventory = yaml.safe_load(Path("deploy/environments.yaml").read_text(encoding="utf-8"))
    inventory["environments"]["staging"]["web_push_allowed_origins"] = [
        "https://push.example.invalid/path"
    ]

    findings = validate_inventory(inventory)

    assert ("DEPLOY-WEB-PUSH-EGRESS", "environments.staging.web_push_allowed_origins") in findings
