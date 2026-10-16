import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vortex_api.config import Settings
from vortex_api.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY = REPO_ROOT / "models" / "registry.yaml"


def make_settings(tmp_path: Path, **overrides) -> Settings:
    values = {
        "mock_backend": True,
        "database_url": f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}",
        "db_auto_create": True,
        "rate_limit_per_minute": 0,
        "registry_path": REGISTRY,
        **overrides,
    }
    return Settings(_env_file=None, **values)


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(make_settings(tmp_path))) as c:
        yield c


def parse_sse(text: str) -> list:
    """Return the decoded `data:` payloads of an SSE body; '[DONE]' is kept as a string."""
    events = []
    for line in text.splitlines():
        if line.startswith("data: "):
            data = line[6:]
            events.append(data if data == "[DONE]" else json.loads(data))
    return events
