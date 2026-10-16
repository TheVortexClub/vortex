from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from vortex_api.main import create_app

from .conftest import make_settings

API_DIR = Path(__file__).resolve().parents[1]


def test_rate_limit_per_ip(tmp_path):
    app = create_app(make_settings(tmp_path, rate_limit_per_minute=2))
    with TestClient(app) as c:
        assert c.get("/v1/models").status_code == 200
        assert c.get("/v1/models").status_code == 200
        r = c.get("/v1/models")
        assert r.status_code == 429
        assert int(r.headers["retry-after"]) >= 1
        assert r.json()["error"]["type"] == "rate_limit_error"
        assert c.get("/health").status_code == 200  # probes are exempt


def test_alembic_migrations_create_schema(tmp_path):
    db_path = tmp_path / "migrated.db"
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_DIR / "migrations"))
    cfg.attributes["database_url"] = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    command.upgrade(cfg, "head")

    engine = sa.create_engine(f"sqlite:///{db_path.as_posix()}")
    with engine.connect() as conn:
        tables = set(sa.inspect(conn).get_table_names())
    engine.dispose()
    assert {"usage_events", "alembic_version"} <= tables
