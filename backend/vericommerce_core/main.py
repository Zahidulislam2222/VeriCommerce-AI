"""HTTP evidence workspaces: versioned facts, local retrieval, explicit approval."""

from __future__ import annotations

import json
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID, uuid4

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from psycopg.types.json import Jsonb
from starlette.concurrency import run_in_threadpool

from . import repository
from .database import check_runtime_role, tenant_lock, transaction
from .jobs import enqueue, job_output
from .models import CatalogInput, DraftInput, EmptyBody, SearchInput
from .retrieval import RetrievalEngine
from .security import RequestGuards, authenticated_tenant, rate_limit, token_hash
from .settings import Settings, get_settings

Tenant = Annotated[str, Depends(authenticated_tenant)]


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or get_settings()
    engine = RetrievalEngine(config)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await run_in_threadpool(engine.load)
        yield

    app = FastAPI(
        title=engine.policy["api_title"],
        version=config.api_version,
        lifespan=lifespan,
        openapi_url="/api/openapi.json",
        docs_url=None,
        redoc_url=None,
    )
    app.state.settings = config
    app.state.engine = engine
    app.add_middleware(RequestGuards, settings=config)

    @app.exception_handler(psycopg.Error)
    async def database_error(_: Request, __: psycopg.Error) -> JSONResponse:
        return JSONResponse({"detail": "Evidence database is temporarily unavailable"}, 503)

    @app.get("/api/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": engine.policy["api_service_name"]}

    @app.get("/api/readyz")
    def ready() -> dict[str, Any]:
        try:
            with transaction(config) as db:
                check_runtime_role(db)
                db.execute("SELECT 1 FROM demo_sessions LIMIT 1")
                protected = db.execute(
                    "SELECT count(*) AS n FROM pg_class WHERE relname IN "
                    "('products','source_revisions','sources','passages','drafts',"
                    "'jobs','audit_events','evaluations') AND relrowsecurity AND relforcerowsecurity"
                ).fetchone()
                if protected is None or protected["n"] != 8:
                    raise RuntimeError("Tenant RLS policy readiness failed")
        except Exception as exc:
            raise HTTPException(503, "Database readiness failed: " + type(exc).__name__) from None
        return {"status": "ready", "demo": True, "database": "postgresql_rls", "retrieval": engine.status()}

    def session_record(request: Request) -> dict[str, Any] | None:
        token = request.cookies.get(config.cookie_name, "")
        if not token or len(token) > 128:
            return None
        with transaction(config) as db:
            row = db.execute(
                "SELECT tenant_id,expires_at FROM demo_sessions WHERE token_hash=%s AND expires_at>now()",
                (token_hash(token),),
            ).fetchone()
        return dict(row) if row else None

    def session_output(row: dict[str, Any]) -> dict[str, Any]:
        return {**row, "demo": True, "store": engine.policy["store"]}

    @app.post("/api/session")
    def start_session(_: EmptyBody, request: Request, response: Response) -> dict[str, Any]:
        current = session_record(request)
        if current:
            return session_output(current)
        tenant_id = str(uuid4())
        token = secrets.token_urlsafe(32)
        expiry = datetime.now(UTC) + timedelta(seconds=config.session_ttl_seconds)
        catalog = CatalogInput.model_validate_json(config.seed_path.read_text())
        with transaction(config) as db:
            db.execute("SELECT pg_advisory_xact_lock(hashtext('vericommerce-session-quota'))")
            db.execute("DELETE FROM demo_sessions WHERE expires_at<=now()")
            count = db.execute("SELECT count(*) AS n FROM demo_sessions").fetchone()
            if count and count["n"] >= config.max_active_sessions:
                raise HTTPException(429, "All private workspace slots are currently in use; retry later")
            address = request.client.host if request.client else "unknown"
            rate_limit(db, token_hash(address), "session", config.session_creations_per_hour, hour=True)
            db.execute(
                "INSERT INTO demo_sessions(tenant_id,token_hash,expires_at) VALUES(%s,%s,%s)",
                (tenant_id, token_hash(token), expiry),
            )
            db.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant_id,))
            repository.ingest(db, tenant_id, catalog, config)
            repository.audit(db, tenant_id, "session.created", tenant_id, config)
        response.set_cookie(
            config.cookie_name,
            token,
            max_age=config.session_ttl_seconds,
            httponly=True,
            secure=config.cookie_secure,
            samesite="strict",
            path="/api",
        )
        response.headers["Cache-Control"] = "no-store"
        return session_output({"tenant_id": tenant_id, "expires_at": expiry})

    @app.get("/api/session")
    def get_session(request: Request, _: Tenant) -> dict[str, Any]:
        row = session_record(request)
        if row is None:
            raise HTTPException(401, "Workspace session expired")
        return session_output(row)

    @app.get("/api/overview")
    def overview(tenant_id: Tenant) -> dict[str, Any]:
        with transaction(config, tenant_id) as db:
            row = db.execute(
                "SELECT (SELECT count(*) FROM products) AS products,"
                "(SELECT count(*) FROM sources) AS sources,"
                "(SELECT count(*) FROM passages p JOIN sources s ON s.tenant_id=p.tenant_id "
                "AND s.current_revision_id=p.revision_id) AS passages,"
                "(SELECT count(*) FROM drafts) AS drafts,"
                "(SELECT count(*) FROM drafts WHERE status='approved') AS approved_drafts,"
                "(SELECT count(*) FROM jobs WHERE status IN ('queued','running')) AS queued_jobs"
            ).fetchone()
        return {**dict(row or {}), "demo": True, "retrieval": engine.status()}

    @app.get("/api/products")
    def get_products(tenant_id: Tenant) -> dict[str, Any]:
        with transaction(config, tenant_id) as db:
            return {"products": repository.products(db, tenant_id)}

    @app.get("/api/sources")
    def get_sources(tenant_id: Tenant) -> dict[str, Any]:
        with transaction(config, tenant_id) as db:
            return {"sources": repository.sources(db, tenant_id)}

    @app.post("/api/search")
    def search(body: SearchInput, tenant_id: Tenant) -> dict[str, Any]:
        with transaction(config, tenant_id) as db:
            return engine.search(db, tenant_id, body)

    @app.post("/api/answers")
    def answer(body: SearchInput, tenant_id: Tenant) -> dict[str, Any]:
        with transaction(config, tenant_id) as db:
            return engine.answer(db, tenant_id, body)

    @app.post("/api/ingestions", status_code=202)
    def ingestion(body: CatalogInput, tenant_id: Tenant) -> dict[str, Any]:
        with transaction(config, tenant_id) as db:
            return {"job": enqueue(db, tenant_id, "ingest", body.model_dump(mode="json"), config)}

    @app.post("/api/drafts", status_code=202)
    def draft(body: DraftInput, tenant_id: Tenant) -> dict[str, Any]:
        with transaction(config, tenant_id) as db:
            if (
                db.execute(
                    "SELECT 1 FROM products WHERE tenant_id=%s AND id=%s", (tenant_id, body.product_id)
                ).fetchone()
                is None
            ):
                raise HTTPException(404, "Product not found")
            return {"job": enqueue(db, tenant_id, "draft", body.model_dump(), config)}

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: UUID, tenant_id: Tenant) -> dict[str, Any]:
        with transaction(config, tenant_id) as db:
            row = db.execute(
                "SELECT * FROM jobs WHERE tenant_id=%s AND id=%s", (tenant_id, job_id)
            ).fetchone()
            if row is None:
                raise HTTPException(404, "Job not found")
            return {"job": job_output(dict(row))}

    @app.get("/api/drafts")
    def get_drafts(tenant_id: Tenant) -> dict[str, Any]:
        with transaction(config, tenant_id) as db:
            rows = db.execute(
                "SELECT d.*,p.fields->>'name' AS product_name FROM drafts d JOIN products p "
                "ON p.tenant_id=d.tenant_id AND p.id=d.product_id WHERE d.tenant_id=%s "
                "ORDER BY d.created_at DESC",
                (tenant_id,),
            ).fetchall()
            return {"drafts": [repository.draft_output(dict(row)) for row in rows]}

    @app.post("/api/drafts/{draft_id}/approve")
    def approve(draft_id: UUID, _: EmptyBody, tenant_id: Tenant) -> dict[str, Any]:
        with transaction(config, tenant_id) as db:
            tenant_lock(db, tenant_id)
            row = repository.draft_by_id(db, tenant_id, str(draft_id), lock=True)
            repository.ensure_current_draft(db, tenant_id, row)
            db.execute(
                "UPDATE drafts SET status='approved',approved_at=coalesce(approved_at,now()) "
                "WHERE tenant_id=%s AND id=%s",
                (tenant_id, draft_id),
            )
            repository.audit(db, tenant_id, "draft.approved", str(draft_id), config)
            return {"draft": repository.draft_output(repository.draft_by_id(db, tenant_id, str(draft_id)))}

    @app.get("/api/drafts/{draft_id}/export")
    def export(draft_id: UUID, tenant_id: Tenant) -> JSONResponse:
        with transaction(config, tenant_id) as db:
            tenant_lock(db, tenant_id)
            row = repository.draft_by_id(db, tenant_id, str(draft_id), lock=True)
            repository.ensure_current_draft(db, tenant_id, row)
            if row["status"] != "approved":
                raise HTTPException(409, "Explicit review approval is required before export")
            repository.audit(db, tenant_id, "draft.exported", str(draft_id), config)
            return JSONResponse(
                jsonable_encoder({"demo": True, "published": False, "draft": repository.draft_output(row)}),
                headers={
                    "Content-Disposition": f'attachment; filename="draft-{draft_id}.json"',
                    "Cache-Control": "no-store",
                },
            )

    @app.get("/api/audit")
    def audit(tenant_id: Tenant) -> dict[str, Any]:
        with transaction(config, tenant_id) as db:
            rows = db.execute(
                "SELECT id,action,entity_id,created_at FROM audit_events "
                "WHERE tenant_id=%s ORDER BY created_at DESC LIMIT 50",
                (tenant_id,),
            ).fetchall()
            return {"events": rows}

    @app.get("/api/graph")
    def graph(
        tenant_id: Tenant, product_id: Annotated[str | None, Query(max_length=80)] = None
    ) -> dict[str, Any]:
        with transaction(config, tenant_id) as db:
            passages = repository.current_passages(db, tenant_id, product_id)
            nodes: dict[str, dict[str, str]] = {}
            edges = []
            for p in passages:
                product_node = "product:" + p["product_id"]
                passage_node = "passage:" + str(p["passage_id"])
                source_node = "revision:" + str(p["revision_id"])
                nodes[product_node] = {"id": product_node, "type": "product", "label": p["product_name"]}
                nodes[passage_node] = {"id": passage_node, "type": "passage", "label": p["label"]}
                nodes[source_node] = {
                    "id": source_node,
                    "type": "source_revision",
                    "label": p["source_name"] + " · " + p["source_version"],
                }
                edges.extend(
                    [
                        {"source": product_node, "target": passage_node, "relation": "has_evidence"},
                        {"source": passage_node, "target": source_node, "relation": "documented_by"},
                    ]
                )
            drafts = db.execute(
                "SELECT id,product_id,status,citations FROM drafts WHERE tenant_id=%s "
                "AND (%s::text IS NULL OR product_id=%s)",
                (tenant_id, product_id, product_id),
            ).fetchall()
            for d in drafts:
                identity = "draft:" + str(d["id"])
                nodes[identity] = {
                    "id": identity,
                    "type": "draft",
                    "label": d["product_id"],
                    "status": d["status"],
                }
                for c in d["citations"]:
                    revision = "revision:" + c["revision_id"]
                    nodes.setdefault(
                        revision,
                        {
                            "id": revision,
                            "type": "source_revision",
                            "label": c["source_name"] + " · " + c["source_version"],
                        },
                    )
                    edges.append({"source": identity, "target": revision, "relation": "derived_from"})
            revisions = db.execute(
                "SELECT id,metadata,supersedes_revision_id FROM source_revisions WHERE tenant_id=%s",
                (tenant_id,),
            ).fetchall()
            history = {str(row["id"]): row for row in revisions}
            for _ in range(config.max_revisions_per_source):
                added = False
                for revision_id, revision in history.items():
                    successor = "revision:" + revision_id
                    previous = revision["supersedes_revision_id"]
                    if successor not in nodes or previous is None:
                        continue
                    predecessor = "revision:" + str(previous)
                    parent = history.get(str(previous))
                    if parent and predecessor not in nodes:
                        nodes[predecessor] = {
                            "id": predecessor,
                            "type": "source_revision",
                            "label": parent["metadata"]["name"] + " · " + parent["metadata"]["version"],
                        }
                        added = True
                    edge = {"source": successor, "target": predecessor, "relation": "supersedes"}
                    if edge not in edges:
                        edges.append(edge)
                if not added:
                    break
            return {
                "nodes": list(nodes.values()),
                "edges": edges,
                "impact": {
                    "stale_drafts": sum(d["status"] == "stale" for d in drafts),
                    "current_source_revisions": len({str(p["revision_id"]) for p in passages}),
                },
            }

    @app.post("/api/evaluations")
    def evaluate(_: EmptyBody, tenant_id: Tenant) -> dict[str, Any]:
        dataset = json.loads(config.evaluation_path.read_text())
        with transaction(config, tenant_id) as db:
            tenant_lock(db, tenant_id)
            count = db.execute(
                "SELECT count(*) AS n FROM evaluations WHERE tenant_id=%s", (tenant_id,)
            ).fetchone()
            if count and count["n"] >= config.max_evaluations:
                raise HTTPException(429, "Evaluation retention quota reached for this workspace")
            cases = []
            for case in dataset["cases"]:
                result = engine.answer(
                    db, tenant_id, SearchInput(query=case["query"], product_id=case["product_id"])
                )
                retrieved = list(dict.fromkeys(c["source_id"] for c in result["citations"]))
                expected_abstain = case["expected_abstain"]
                passed = result["abstained"] == expected_abstain and (
                    expected_abstain or case["expected_source_id"] in retrieved
                )
                cases.append(
                    {
                        **case,
                        "actual_abstain": result["abstained"],
                        "retrieved_source_ids": retrieved,
                        "passed": passed,
                    }
                )
            answerable = [case for case in cases if not case["expected_abstain"]]
            result = {
                "id": str(uuid4()),
                "created_at": datetime.now(UTC).isoformat(),
                "dataset_version": dataset["version"],
                "method": engine.status()["method"],
                "total": len(cases),
                "passed": sum(case["passed"] for case in cases),
                "retrieval_recall_at_k": sum(
                    c["expected_source_id"] in c["retrieved_source_ids"] for c in answerable
                )
                / len(answerable),
                "abstention_accuracy": sum(c["actual_abstain"] == c["expected_abstain"] for c in cases)
                / len(cases),
                "cases": cases,
                "retrieval": engine.status(),
            }
            db.execute(
                "INSERT INTO evaluations(tenant_id,id,result) VALUES(%s,%s,%s)",
                (tenant_id, result["id"], Jsonb(result)),
            )
            repository.audit(db, tenant_id, "evaluation.completed", result["id"], config)
            return result

    @app.get("/api/evaluations")
    def evaluations(tenant_id: Tenant) -> dict[str, Any]:
        with transaction(config, tenant_id) as db:
            rows = db.execute(
                "SELECT result FROM evaluations WHERE tenant_id=%s ORDER BY created_at DESC", (tenant_id,)
            ).fetchall()
            return {"evaluations": [row["result"] for row in rows]}

    return app


app = create_app()
