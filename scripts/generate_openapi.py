from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.check_openapi import check_openapi_text  # noqa: E402

ARTIFACT = ROOT / "contracts/openapi.yaml"


def _generation_environment() -> dict[str, str]:
    environment = dict(os.environ)
    environment.update(
        {
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "APP_ENV": "development",
            "DATABASE_URL": "postgresql://schema:unused@127.0.0.1/schema",
            "DJANGO_SECRET_KEY": "schema-generation-only",
            "DJANGO_DEBUG": "false",
            "API_DOCS_ENABLED": "true",
            "DJANGO_CACHE_BACKEND": "locmem",
            "REDIS_URL": "rediss://schema:unused@redis.invalid/0",
            "REDIS_KEY_PREFIX": "schema-development",
            "R2_BUCKET": "schema-development",
            "ORIGIN_CREDENTIAL_HEADER": "X-Origin-Credential",
            "ORIGIN_CREDENTIAL": "schema-only-origin-credential-0000",
        }
    )
    return environment


def _raw_document() -> dict[str, Any]:
    code = """
import json
import django
django.setup()
from drf_spectacular.generators import SchemaGenerator
print(json.dumps(SchemaGenerator().get_schema(request=None, public=True), sort_keys=True))
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT / "backend",
        env=_generation_environment(),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode or result.stderr.strip():
        raise RuntimeError("OPENAPI-GENERATION: backend schema generation failed")
    loaded = json.loads(result.stdout)
    if not isinstance(loaded, dict):
        raise RuntimeError("OPENAPI-GENERATION: invalid schema document")
    return loaded


def schema_document() -> dict[str, Any]:
    return _raw_document()


def generate_openapi_bytes() -> bytes:
    document = schema_document()
    ordered = {
        key: document[key]
        for key in ("openapi", "info", "paths", "components")
        if key in document
    }
    ordered.update(
        {key: value for key, value in document.items() if key not in ordered}
    )
    rendered = yaml.safe_dump(
        ordered,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    check_openapi_text(rendered, "contracts/openapi.yaml")
    return rendered.replace("\r\n", "\n").encode()


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    candidate = generate_openapi_bytes()
    if arguments.write:
        ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        ARTIFACT.write_bytes(candidate)
        return 0
    if not ARTIFACT.exists() or ARTIFACT.read_bytes() != candidate:
        print("OPENAPI-DRIFT: contracts/openapi.yaml", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
