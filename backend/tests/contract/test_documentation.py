from __future__ import annotations

import json
import re
from pathlib import Path


def test_readme_local_links_resolve() -> None:
    source = Path("README.md").read_text(encoding="utf-8")
    links = re.findall(r"\[[^]]+\]\(([^)]+)\)", source)
    local_links = [link.split("#", 1)[0] for link in links if "://" not in link]
    assert local_links
    assert all(Path(link).exists() for link in local_links)


def test_dependency_provenance_covers_every_declared_dependency() -> None:
    architecture = Path("docs/ARCHITECTURE.md").read_text(encoding="utf-8").casefold()
    backend = Path("backend/pyproject.toml").read_text(encoding="utf-8")
    frontend = json.loads(Path("frontend/package.json").read_text(encoding="utf-8"))
    python_names = {
        match.casefold()
        for match in re.findall(r'^\s*"([A-Za-z0-9_-]+)(?:\[[^]]+\])?==', backend, re.MULTILINE)
    }
    node_names = set(frontend["dependencies"]) | set(frontend["devDependencies"])
    declared = python_names | {name.casefold() for name in node_names}
    missing = sorted(name for name in declared if f"`{name}`" not in architecture)
    assert missing == []
    forbidden = ("celery", "boto3", "redis==", "sentry-sdk", "axios")
    assert all(value not in backend.casefold() for value in forbidden)
