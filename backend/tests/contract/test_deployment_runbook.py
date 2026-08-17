from pathlib import Path


def test_runbook_contains_every_required_operational_procedure() -> None:
    source = Path("docs/TRIEN_KHAI.md").read_text(encoding="utf-8").casefold()
    required = (
        "≥2 az",
        "public load balancer",
        "private application instances",
        "per-az egress",
        "exactly one scheduler",
        "all outbound egress",
        "database_url",
        "database_admin_url",
        "credential rotation",
        "migration before rollout",
        "isolated restore",
        "session revocation",
        "stale lease",
        "iac is deferred",
        "apac is not data residency",
        "throttle_cache",
        "recovery-evidence.yaml",
        "unresolved",
    )
    for phrase in required:
        assert phrase in source, phrase
