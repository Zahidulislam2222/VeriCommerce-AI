"""Behavioral coverage of actual HTTP/SQL evidence and approval boundaries."""

from __future__ import annotations

import copy
import json
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb


def complete(client: Any, settings: Any, identity: str) -> dict[str, Any]:
    from vericommerce_core.jobs import process_one

    for _ in range(100):
        job = client.get("/api/jobs/" + identity).json()["job"]
        if job["status"] in {"succeeded", "failed"}:
            return job
        process_one(settings)
    raise AssertionError("Bounded worker did not complete the job")


def new_draft(client: Any, settings: Any) -> str:
    response = client.post("/api/drafts", json={"product_id": "forma-one"})
    assert response.status_code == 202, response.text
    job = complete(client, settings, response.json()["job"]["id"])
    assert job["status"] == "succeeded", job
    return str(job["result"]["draft_id"])


def test_session_cookie_health_counts_and_openapi(client: Any) -> None:
    assert client.get("/api/healthz").json()["status"] == "ok"
    assert client.get("/api/readyz").json()["status"] == "ready"
    current = client.get("/api/session").json()
    assert current["demo"] is True
    assert client.post("/api/session", json={}).json()["tenant_id"] == current["tenant_id"]
    overview = client.get("/api/overview").json()
    assert (overview["products"], overview["sources"], overview["passages"]) == (3, 6, 7)
    assert overview["retrieval"]["status"] == "lexical_only"
    assert "/api/drafts/{draft_id}/approve" in client.get("/api/openapi.json").json()["paths"]
    assert client.get("/api/products").headers["cache-control"] == "no-store"


def test_real_retrieval_answers_and_unsupported_abstention(client: Any) -> None:
    result = client.post(
        "/api/answers", json={"query": "What is the battery life?", "product_id": "forma-one"}
    ).json()
    assert result["abstained"] is False
    assert "40 hours" in result["answer"] and "disabled" in result["answer"]
    assert result["method"] == "extractive_source_quotes"
    assert result["citations"][0]["source_id"] == "forma-manual"
    for question, product in [
        ("Does it cure eczema?", "verdant-serum"),
        ("What waterproof certification does it have?", "forma-one"),
    ]:
        answer = client.post("/api/answers", json={"query": question, "product_id": product}).json()
        assert answer["abstained"] is True and not answer["citations"]


def test_durable_draft_approval_export_and_source_invalidation(client: Any, settings: Any) -> None:
    identity = new_draft(client, settings)
    assert client.get(f"/api/drafts/{identity}/export").status_code == 409
    approved = client.post(f"/api/drafts/{identity}/approve", json={})
    assert approved.status_code == 200 and approved.json()["draft"]["status"] == "approved"
    export = client.get(f"/api/drafts/{identity}/export")
    assert export.status_code == 200 and export.json()["published"] is False
    assert "attachment" in export.headers["content-disposition"]
    catalog = json.loads(settings.seed_path.read_text())
    changed = copy.deepcopy(catalog)
    changed["sources"][0]["version"] = "2.2"
    changed["products"][0]["claims"][0]["passage"] = (
        "Battery life: up to 30 hours with noise cancellation disabled."
    )
    changed["products"][0]["claims"][0]["value"] = "Up to 30 hours"
    queued = client.post("/api/ingestions", json=changed)
    assert queued.status_code == 202
    job = complete(client, settings, queued.json()["job"]["id"])
    assert job["status"] == "succeeded" and job["result"]["stale_drafts"] == 1
    assert client.post(f"/api/drafts/{identity}/approve", json={}).status_code == 409
    assert client.get(f"/api/drafts/{identity}/export").status_code == 409
    drafts = client.get("/api/drafts").json()["drafts"]
    assert drafts[0]["status"] == "stale" and drafts[0]["approved_at"] is None
    current = client.post("/api/answers", json={"query": "battery life", "product_id": "forma-one"}).json()
    assert "30 hours" in current["answer"] and "40 hours" not in current["answer"]


def test_ingestion_replay_is_idempotent(client: Any, settings: Any) -> None:
    from vericommerce_core.database import transaction

    tenant_id = client.get("/api/session").json()["tenant_id"]
    catalog = json.loads(settings.seed_path.read_text())
    with transaction(settings, tenant_id) as db:
        before = db.execute("SELECT count(*) AS n FROM source_revisions").fetchone()["n"]
    for _ in range(2):
        response = client.post("/api/ingestions", json=catalog)
        job = complete(client, settings, response.json()["job"]["id"])
        assert job["status"] == "succeeded"
        assert job["result"]["sources_changed"] == 0 and job["result"]["sources_unchanged"] == 6
    with transaction(settings, tenant_id) as db:
        assert db.execute("SELECT count(*) AS n FROM source_revisions").fetchone()["n"] == before


def test_product_metadata_change_also_invalidates_approved_text(client: Any, settings: Any) -> None:
    identity = new_draft(client, settings)
    assert client.post(f"/api/drafts/{identity}/approve", json={}).status_code == 200
    catalog = json.loads(settings.seed_path.read_text())
    catalog["products"][0]["name"] = "Renamed fictional headphones"
    queued = client.post("/api/ingestions", json=catalog)
    job = complete(client, settings, queued.json()["job"]["id"])
    assert job["status"] == "succeeded" and job["result"]["stale_drafts"] == 1
    assert client.get(f"/api/drafts/{identity}/export").status_code == 409
    assert client.get("/api/drafts").json()["drafts"][0]["status"] == "stale"


def test_other_tenant_cannot_read_jobs_or_drafts_and_rls_filters_without_where(
    client: Any, settings: Any
) -> None:
    from vericommerce_core.database import transaction
    from vericommerce_core.main import create_app

    draft_id = new_draft(client, settings)
    job_id = client.post("/api/drafts", json={"product_id": "arc-light"}).json()["job"]["id"]
    with TestClient(
        create_app(settings), base_url="https://testserver", headers={"Origin": "https://testserver"}
    ) as other:
        tenant_id = other.post("/api/session", json={}).json()["tenant_id"]
        assert other.get(f"/api/jobs/{job_id}").status_code == 404
        assert other.post(f"/api/drafts/{draft_id}/approve", json={}).status_code == 404
        assert other.get("/api/drafts").json()["drafts"] == []
        with transaction(settings, tenant_id) as db:
            assert db.execute("SELECT count(*) AS n FROM products").fetchone()["n"] == 3
            assert db.execute("SELECT count(*) AS n FROM drafts").fetchone()["n"] == 0
    with transaction(settings) as db:
        assert db.execute("SELECT count(*) AS n FROM products").fetchone()["n"] == 0


def test_origin_body_input_auth_and_security_guards(client: Any, settings: Any) -> None:
    assert (
        client.post(
            "/api/drafts", json={"product_id": "forma-one"}, headers={"Origin": "https://attacker.invalid"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/drafts", json={"product_id": "forma-one"}, headers={"Sec-Fetch-Site": "cross-site"}
        ).status_code
        == 403
    )
    assert client.post("/api/drafts", content="{}", headers={"Content-Type": "text/plain"}).status_code == 415
    assert (
        client.post(
            "/api/ingestions",
            content=b"x" * (settings.max_body_bytes + 1),
            headers={"Content-Type": "application/json"},
        ).status_code
        == 413
    )
    assert client.post("/api/drafts", json={"product_id": "forma-one", "admin": True}).status_code == 422
    assert client.post("/api/search", json={"query": "x", "limit": 100}).status_code == 422
    client.cookies.clear()
    assert client.get("/api/products").status_code == 401


def test_restart_session_and_approved_content_persist(client: Any, settings: Any) -> None:
    from vericommerce_core.main import create_app

    identity = new_draft(client, settings)
    assert client.post(f"/api/drafts/{identity}/approve", json={}).status_code == 200
    cookie = client.cookies.get(settings.cookie_name)
    with TestClient(
        create_app(settings), base_url="https://testserver", headers={"Origin": "https://testserver"}
    ) as restarted:
        restarted.cookies.set(settings.cookie_name, cookie, path="/api")
        assert restarted.get(f"/api/drafts/{identity}/export").status_code == 200
        assert restarted.get("/api/overview").json()["approved_drafts"] == 1


def test_measured_evaluation_graph_and_content_free_audit(client: Any) -> None:
    result = client.post("/api/evaluations", json={})
    assert result.status_code == 200, result.text
    report = result.json()
    assert report["total"] == 10 and len(report["cases"]) == 10
    assert report["passed"] == sum(case["passed"] for case in report["cases"])
    assert client.get("/api/evaluations").json()["evaluations"][0]["id"] == report["id"]
    graph = client.get("/api/graph").json()
    assert len([n for n in graph["nodes"] if n["type"] == "product"]) == 3
    assert graph["impact"]["current_source_revisions"] == 6
    events = client.get("/api/audit").json()["events"]
    assert events and all(set(e) == {"id", "action", "entity_id", "created_at"} for e in events)


def test_interrupted_job_is_reclaimed_and_exhausted_job_is_terminal(client: Any, settings: Any) -> None:
    from vericommerce_core.database import transaction
    from vericommerce_core.jobs import process_one

    tenant_id = client.get("/api/session").json()["tenant_id"]
    identity = client.post("/api/drafts", json={"product_id": "forma-one"}).json()["job"]["id"]
    with transaction(settings, tenant_id) as db:
        db.execute(
            "UPDATE jobs SET status='running',attempts=1,lease_until=now()-interval '1 second' "
            "WHERE tenant_id=%s AND id=%s",
            (tenant_id, identity),
        )
    result = complete(client, settings, identity)
    assert result["status"] == "succeeded" and result["attempts"] == 2
    broken = str(uuid4())
    with transaction(settings, tenant_id) as db:
        db.execute(
            "INSERT INTO jobs(tenant_id,id,kind,status,payload,attempts,lease_until) "
            "VALUES(%s,%s,'draft','running',%s,%s,now()-interval '1 second')",
            (tenant_id, broken, Jsonb({"product_id": "forma-one"}), settings.worker_max_attempts),
        )
    for _ in range(settings.worker_tenant_batch):
        process_one(settings)
        if client.get(f"/api/jobs/{broken}").json()["job"]["status"] == "failed":
            break
    assert client.get(f"/api/jobs/{broken}").json()["job"]["status"] == "failed"
