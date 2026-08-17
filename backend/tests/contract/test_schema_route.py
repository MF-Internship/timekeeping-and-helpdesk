from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).parents[2]


def _probe(enabled: bool) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment.update(
        {
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "APP_ENV": "development",
            "DATABASE_URL": "postgresql://runtime:secret@localhost/foundation",
            "DJANGO_SECRET_KEY": "test-only",
            "DJANGO_DEBUG": "false",
            "API_DOCS_ENABLED": str(enabled).lower(),
            "DJANGO_CACHE_BACKEND": "locmem",
            "REDIS_URL": "rediss://user:secret@redis.invalid/0",
            "REDIS_KEY_PREFIX": "foundation-development",
            "R2_BUCKET": "foundation-development",
            "ORIGIN_CREDENTIAL_HEADER": "X-Origin-Credential",
            "ORIGIN_CREDENTIAL": "z" * 32,
        }
    )
    code = """
import django
django.setup()
from django.test import Client
from django.urls import resolve, Resolver404
try:
    match = resolve('/api/v1/schema/')
except Resolver404:
    print('ABSENT')
else:
    print(match.url_name, match.func.view_class.__name__)
response = Client().get(
    '/api/v1/schema/',
    HTTP_X_ORIGIN_CREDENTIAL='z' * 32,
    HTTP_ACCEPT='application/yaml',
)
print(response.status_code, response.headers.get('Content-Type', ''))
if response.status_code == 200:
    print(response.content.decode().splitlines()[0])
"""
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_schema_route_is_machine_only_when_enabled() -> None:
    result = _probe(True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "api-schema MachineSchemaView",
        "200 application/yaml; charset=utf-8",
        "openapi: 3.0.3",
    ]
    source = BACKEND.joinpath("config/urls.py").read_text(encoding="utf-8")
    assert "Swagger" not in source
    assert "Redoc" not in source
    assert "SpectacularSwaggerView" not in source


def test_schema_route_is_absent_when_disabled() -> None:
    result = _probe(False)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["ABSENT", "404 text/html; charset=utf-8"]
