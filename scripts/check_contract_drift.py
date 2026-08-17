from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from core.event_payload import sanitize_failure_reason  # noqa: E402
from scripts.generate_openapi import generate_openapi_bytes  # noqa: E402

CANONICAL_CLIENT = ROOT / "frontend/src/shared/api/schema.ts"


@dataclass(frozen=True, slots=True)
class Finding:
    rule: str
    path: str


def check_artifacts(openapi_path: Path, client_path: Path) -> list[Finding]:
    findings: list[Finding] = []
    if (
        not openapi_path.exists()
        or openapi_path.read_bytes() != generate_openapi_bytes()
    ):
        findings.append(Finding("DRIFT-OPENAPI", str(openapi_path)))
    canonical_client = (
        CANONICAL_CLIENT.read_bytes() if CANONICAL_CLIENT.exists() else b""
    )
    if not client_path.exists() or client_path.read_bytes() != canonical_client:
        findings.append(Finding("DRIFT-CLIENT", str(client_path)))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--openapi", type=Path, default=ROOT / "contracts/openapi.yaml")
    parser.add_argument("--client", type=Path, default=CANONICAL_CLIENT)
    arguments = parser.parse_args()
    findings = check_artifacts(arguments.openapi, arguments.client)
    for finding in findings:
        print(
            f"{finding.rule}: {sanitize_failure_reason(finding.path)}", file=sys.stderr
        )
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
