"""Release-boundary, applied migration and configurable metadata regressions."""

from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "backend/vericommerce_core"


def boundary_violations(source: str) -> set[str]:
    findings: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "os" and node.attr in {"getenv", "environ"}:
                findings.add("environment_access")
        if isinstance(node, ast.ImportFrom) and node.module == "os":
            if any(alias.name in {"environ", "getenv"} for alias in node.names):
                findings.add("environment_access")
        if isinstance(node, ast.Call):
            for argument in node.keywords:
                if argument.arg in {"model_name", "repo_id", "revision", "connect_timeout"}:
                    if isinstance(argument.value, ast.Constant) and argument.value.value:
                        findings.add("literal_operational_setting")
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if re.search(r"https?://[A-Za-z0-9]", node.value):
                findings.add("literal_provider_url")
            if re.search(r"postgres(?:ql)?://[^\s:'\"]+:[^\s@'\"]+@", node.value):
                findings.add("literal_credential_dsn")
            if re.search(r"\bLIMIT\s+(?:[2-9]|\d{2,})\b", node.value, re.IGNORECASE):
                findings.add("literal_operational_page_limit")
    return findings


def test_backend_environment_and_operational_values_have_one_owner() -> None:
    for source in PACKAGE.glob("*.py"):
        if source.name != "settings.py":
            assert not boundary_violations(source.read_text()), source.name


def test_boundary_guard_rejects_reintroduced_settings_and_fake_credentials() -> None:
    examples = [
        "import os\nvalue=os.environ['VC_MODEL']",
        "from os import getenv\nvalue=getenv('VC_MODEL')",
        "provider(model_name='configured-test-model')",
        "connect(connect_timeout=5)",
        "endpoint='https://provider.example.test/v1'",
        "dsn='postgresql://test-user:test-key@localhost/test_db'",
        "query='SELECT id FROM audit_events LIMIT 50'",
    ]
    assert all(boundary_violations(source) for source in examples)
    assert not boundary_violations("provider(model_name=settings.embedding_model)")


def test_only_accepted_backend_and_applied_migration_ship() -> None:
    accepted = {
        "__init__",
        "database",
        "jobs",
        "main",
        "migrate",
        "models",
        "repository",
        "restore_probe",
        "retrieval",
        "security",
        "settings",
        "warmup",
        "worker",
        "account_repository",
        "account_routes",
        "shopify_protocol",
        "shopify_client",
        "shopify_repository",
        "shopify_routes",
        "phase_models",
        "phase_repository",
        "phase_routes",
        "uploads",
        "document_parser",
        "context",
        "intelligence",
        "benchmark",
    }
    assert {p.stem for p in PACKAGE.glob("*.py")} == accepted
    migrations = ROOT / "backend/migrations"
    assert {p.name for p in migrations.glob("*.sql")} == {
        "001_evidence_core.sql",
        "002_identity.sql",
        "003_content_intelligence.sql",
        "004_worker_fairness.sql",
        "005_initial_catalog_upload.sql",
        "006_product_retirement.sql",
    }
    # Applied-schema bytes are a release compatibility invariant, never rewritten.
    expected = "5c95f26d721215903d4b9e2ef2c41df3e3c785c3a7fe0216ef9cc7ff03483dac"
    assert hashlib.sha256((migrations / "001_evidence_core.sql").read_bytes()).hexdigest() == expected


def test_environment_examples_have_exact_typed_owners(settings: Any) -> None:
    example = (ROOT / "backend/.env.example").read_text()
    names = set(re.findall(r"^(VC_[A-Z0-9_]+)=", example, re.M))
    assert names == {"VC_" + name.upper() for name in type(settings).model_fields}
    assert not re.search(r"sk-[A-Za-z0-9_-]{20,}|-----BEGIN .*PRIVATE KEY-----", example)


def test_openapi_health_branding_and_version_change_through_configuration(
    settings: Any, tmp_path: Path
) -> None:
    from vericommerce_core.main import create_app

    policy = json.loads(settings.policy_path.read_text())
    policy.update(api_title="Configured workspace API", api_service_name="configured-workspace")
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(policy))
    configured = settings.model_copy(update={"policy_path": path, "api_version": "9.8.7"})
    with TestClient(create_app(configured), base_url="https://testserver") as client:
        description = client.get("/api/openapi.json").json()
        assert description["info"]["title"] == "Configured workspace API"
        assert description["info"]["version"] == "9.8.7"
        assert client.get("/api/healthz").json()["service"] == "configured-workspace"
        assert {
            "/api/auth/me",
            "/api/shopify",
            "/api/uploads",
            "/api/context",
            "/api/benchmark-dataset",
        }.issubset(description["paths"])


def test_typed_environment_overrides_version_without_source_changes(monkeypatch: Any) -> None:
    from vericommerce_core.settings import Settings

    monkeypatch.setenv("VC_API_VERSION", "3.2.1")
    configured = Settings(
        database_url="postgresql://test-user:test-key@localhost/test_db", embedding_enabled=False
    )
    assert configured.api_version == "3.2.1"


def test_invalid_maintained_policy_fails_before_serving_requests(settings: Any, tmp_path: Path) -> None:
    from pydantic import ValidationError
    from vericommerce_core.retrieval import RetrievalEngine

    policy = json.loads(settings.policy_path.read_text())
    policy["api_service_name"] = "not a service identifier"
    path = tmp_path / "invalid-policy.json"
    path.write_text(json.dumps(policy))
    with pytest.raises(ValidationError):
        RetrievalEngine(settings.model_copy(update={"policy_path": path}))


def test_audit_response_obeys_typed_page_limit_on_real_database(settings: Any) -> None:
    from vericommerce_core.database import transaction
    from vericommerce_core.main import create_app
    from vericommerce_core.repository import audit

    configured = settings.model_copy(update={"audit_page_size": 3})
    with TestClient(
        create_app(configured), base_url="https://testserver", headers={"Origin": "https://testserver"}
    ) as client:
        session = client.post("/api/session", json={})
        assert session.status_code == 200, session.text
        tenant_id = session.json()["tenant_id"]
        with transaction(configured, tenant_id) as db:
            for index in range(6):
                audit(db, tenant_id, "configured.limit", str(index), configured)
        response = client.get("/api/audit")
        assert response.status_code == 200, response.text
        assert len(response.json()["events"]) == 3


def test_document_chunk_limit_controls_persisted_passages(settings: Any, monkeypatch: Any) -> None:
    import base64

    from vericommerce_core import uploads
    from vericommerce_core.database import transaction
    from vericommerce_core.jobs import process_one
    from vericommerce_core.main import create_app

    # Isolate chunking from parser behavior: real HTTP admission, job and DB effects;
    # separate parser tests exercise actual PDF extraction/isolation.
    text = "Evidence document content." * 50
    monkeypatch.setattr(
        uploads, "isolated_parse", lambda *_: {"kind": "document", "pages": [{"page": "1", "text": text}]}
    )
    configured = settings.model_copy(update={"document_chunk_chars": 256})
    with TestClient(
        create_app(configured), base_url="https://testserver", headers={"Origin": "https://testserver"}
    ) as client:
        session = client.post("/api/session", json={})
        assert session.status_code == 200, session.text
        tenant_id = session.json()["tenant_id"]
        received = client.post(
            "/api/uploads",
            json={
                "product_id": "forma-one", "source_id": "configured-chunk-source",
                "filename": "configured.pdf", "media_type": "application/pdf", "version": "1",
                "content_base64": base64.b64encode(b"%PDF-1.7\nfixture").decode(),
            },
        )
        assert received.status_code == 202, received.text
        job_id = received.json()["job"]["id"]
        for _ in range(10):
            process_one(configured)
            job = client.get("/api/jobs/" + job_id).json()["job"]
            if job["status"] in {"succeeded", "failed"}:
                break
        assert job["status"] == "succeeded", job
        with transaction(configured, tenant_id) as db:
            passages = db.execute(
                "SELECT p.text,p.value FROM passages p JOIN source_revisions r "
                "ON p.tenant_id=r.tenant_id AND p.revision_id=r.id "
                "WHERE p.tenant_id=%s AND r.source_id=%s ORDER BY p.position",
                (tenant_id, "configured-chunk-source"),
            ).fetchall()
        assert len(passages) == (len(text) + 255) // 256
        # Evidence ingestion canonically sorts claims and trims schema whitespace;
        # this patch preserves that existing contract, rather than inventing a
        # document-order guarantee from the persisted position field.
        expected = sorted(text[start : start + 256].strip() for start in range(0, len(text), 256))
        assert [row["text"] for row in passages] == expected
        assert all(len(row["text"]) <= 256 and len(row["value"]) <= 500 for row in passages)


def test_operational_page_and_chunk_settings_reject_schema_excess(settings: Any) -> None:
    from pydantic import ValidationError

    cls = type(settings)
    defaults = cls.model_fields
    assert defaults["audit_page_size"].default == 50
    assert defaults["document_chunk_chars"].default == 4000
    values = settings.model_dump()
    for invalid in ({"audit_page_size": 0}, {"document_chunk_chars": 0}, {"document_chunk_chars": 4001}):
        with pytest.raises(ValidationError):
            cls(**{**values, **invalid})
