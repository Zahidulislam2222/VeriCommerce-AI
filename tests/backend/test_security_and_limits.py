"""Security regression checks and real durable quota behavior."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


def test_expired_cookie_loses_access_and_does_not_become_another_tenant(client: Any, settings: Any) -> None:
    from vericommerce_core.database import transaction

    identity = client.get("/api/session").json()["tenant_id"]
    with transaction(settings) as db:
        db.execute(
            "UPDATE demo_sessions SET expires_at=now()-interval '1 second' WHERE tenant_id=%s", (identity,)
        )
    assert client.get("/api/products").status_code == 401
    fresh = client.post("/api/session", json={})
    assert fresh.status_code == 200 and fresh.json()["tenant_id"] != identity


def test_database_rls_rejects_other_tenant_write(client: Any, settings: Any) -> None:
    from vericommerce_core.database import transaction

    identity = client.get("/api/session").json()["tenant_id"]
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with transaction(settings, identity) as db:
            db.execute("INSERT INTO products(tenant_id,id,fields) VALUES(%s,'cross-tenant','{}')", (uuid4(),))


def test_durable_rate_and_job_quotas_are_enforced(client: Any, settings: Any) -> None:
    from vericommerce_core.database import transaction
    from vericommerce_core.jobs import enqueue
    from vericommerce_core.security import rate_limit

    key = str(uuid4())
    with transaction(settings) as db:
        rate_limit(db, key, "test", 1)
    with pytest.raises(HTTPException) as exc:
        with transaction(settings) as db:
            rate_limit(db, key, "test", 1)
    assert exc.value.status_code == 429
    identity = client.get("/api/session").json()["tenant_id"]
    limited = settings.model_copy(update={"max_jobs": 1})
    with transaction(settings, identity) as db:
        enqueue(db, identity, "draft", {"product_id": "forma-one"}, limited)
    with pytest.raises(HTTPException) as exc:
        with transaction(settings, identity) as db:
            enqueue(db, identity, "draft", {"product_id": "forma-one"}, limited)
    assert exc.value.status_code == 429


def test_cookie_attributes_and_missing_origin_are_checked(settings: Any) -> None:
    from vericommerce_core.main import create_app

    with TestClient(create_app(settings), base_url="https://testserver") as client:
        assert client.post("/api/session", json={}).status_code == 403
        response = client.post("/api/session", json={}, headers={"Origin": "https://testserver"})
        cookie = response.headers["set-cookie"].lower()
        assert "httponly" in cookie and "secure" in cookie and "samesite=strict" in cookie
        assert "path=/api" in cookie


def test_invalid_catalog_and_missing_product_fail_without_partial_data(client: Any, settings: Any) -> None:
    catalog = json.loads(settings.seed_path.read_text())
    catalog["products"][0]["claims"][0]["sourceId"] = "unknown-source"
    assert client.post("/api/ingestions", json=catalog).status_code == 422
    assert client.post("/api/drafts", json={"product_id": "absent-product"}).status_code == 404
    assert client.get("/api/overview").json()["products"] == 3


def test_configuration_and_secret_regressions() -> None:
    root = Path(__file__).resolve().parents[2]
    forbidden = [
        r"sk-[A-Za-z0-9_-]{20,}",
        r"-----BEGIN .*PRIVATE KEY-----",
        r"postgres(?:ql)?://[^\s:'\"]+:[^\s@'\"]+@",
        r"https?://(?:api\.)?(?:openai\.com|openrouter\.ai|anthropic\.com)",
        r"(?:BAAI|Qwen|Qdrant)/[A-Za-z0-9_.-]+",
    ]
    for source in (root / "backend/vericommerce_core").glob("*.py"):
        content = source.read_text()
        for pattern in forbidden:
            assert re.search(pattern, content) is None, (
                f"Configuration/secret boundary violation in {source.name}"
            )


def test_every_environment_setting_has_a_safe_example(settings: Any) -> None:
    root = Path(__file__).resolve().parents[2]
    example = (root / "backend/.env.example").read_text()
    for field in type(settings).model_fields:
        assert "VC_" + field.upper() + "=" in example


def test_enabled_model_requires_immutable_revision(settings: Any) -> None:
    from pydantic import ValidationError
    from vericommerce_core.settings import Settings

    with pytest.raises(ValidationError):
        Settings(
            database_url=settings.database_url,
            embedding_enabled=True,
            embedding_model="configured-test-model",
            embedding_repository="local/test",
            embedding_revision="main",
            embedding_model_file="model.onnx",
        )
