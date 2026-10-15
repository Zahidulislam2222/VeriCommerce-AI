"""Real PostgreSQL fixtures; only explicitly configured dedicated *_test databases."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from pydantic import SecretStr

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))


@pytest.fixture(scope="session")
def settings() -> Any:
    from vericommerce_core.migrate import migrate
    from vericommerce_core.settings import Settings

    admin_url = os.environ.get("VC_TEST_ADMIN_DATABASE_URL")
    runtime_url = os.environ.get("VC_TEST_DATABASE_URL")
    if not admin_url or not runtime_url:
        pytest.skip("Real PostgreSQL tests require explicit VC_TEST_*_DATABASE_URL settings")
    details = conninfo_to_dict(admin_url)
    database = details.get("dbname", "")
    if not database.endswith("_test"):
        raise RuntimeError("Refusing tests on a database without the explicit _test suffix")
    with psycopg.connect(make_conninfo(admin_url, dbname="postgres"), autocommit=True) as db:
        if not db.execute("SELECT 1 FROM pg_database WHERE datname=%s", (database,)).fetchone():
            db.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
    with psycopg.connect(admin_url) as db:
        db.execute("DROP SCHEMA public CASCADE")
        db.execute("CREATE SCHEMA public")
    result = Settings(
        database_url=SecretStr(runtime_url),
        migration_database_url=SecretStr(admin_url),
        allowed_origins=["https://testserver"],
        requests_per_minute=1000,
        session_creations_per_hour=100,
        max_active_sessions=100,
        embedding_enabled=False,
    )
    migrate(result)
    os.environ["VC_DATABASE_URL"] = runtime_url
    return result


@pytest.fixture
def client(settings: Any) -> Iterator[Any]:
    from fastapi.testclient import TestClient
    from vericommerce_core.main import create_app

    with TestClient(
        create_app(settings), base_url="https://testserver", headers={"Origin": "https://testserver"}
    ) as session:
        response = session.post("/api/session", json={})
        assert response.status_code == 200, response.text
        yield session
