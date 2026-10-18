"""Authorized phase 2–5 HTTP contracts; each mutation uses tenant transactions."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from .account_repository import account_identity
from .benchmark import dataset, reviewed_dataset, run_benchmark, save_review
from .context import select_context
from .database import tenant_lock, transaction
from .intelligence import impact, inspect_claims, product_json_ld
from .jobs import enqueue, job_output
from .models import EmptyBody
from .phase_models import (
    BenchmarkReviewInput,
    ContextInput,
    ImageReviewInput,
    RelationInput,
    SnapshotInput,
    UploadInput,
)
from .phase_repository import delete_source, retry_job, versions
from .repository import audit, citation, current_passages, digest
from .security import authorized_transaction, require_capability
from .shopify_protocol import connector_owned_id
from .uploads import current_image, policy, save_upload

router = APIRouter(prefix="/api")
Read = Annotated[str, Depends(require_capability("read"))]
Edit = Annotated[str, Depends(require_capability("edit"))]
Approve = Annotated[str, Depends(require_capability("approve"))]


@router.get("/capabilities")
def capabilities(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    configuration = policy(settings)
    corpus = dataset(settings)
    return {
        "uploads": {
            "max_bytes": settings.upload_max_bytes,
            "media_types": configuration["media_types"],
            "csv_columns": configuration["csv_columns"],
        },
        "retrieval": {
            "methods": ["keyword", "dense", "hybrid", "rerank"],
            "context_max_chars": settings.context_max_chars,
        },
        "benchmark": {
            "version": corpus["version"],
            "hash": corpus["hash"],
            "review_status": corpus["review_status"],
        },
    }


@router.post("/uploads", status_code=202)
def upload(body: UploadInput, request: Request, tenant_id: Edit) -> dict[str, Any]:
    settings = request.app.state.settings
    if connector_owned_id(body.source_id):
        raise HTTPException(422, "Provider-owned source identifiers cannot be overwritten")
    with authorized_transaction(request, tenant_id, "edit") as db:
        result = save_upload(db, tenant_id, body, settings)
        if result["duplicate"]:
            existing = db.execute(
                "SELECT * FROM jobs WHERE tenant_id=%s AND kind='upload' "
                "AND payload->>'upload_id'=%s ORDER BY created_at DESC LIMIT 1",
                (tenant_id, result["upload_id"]),
            ).fetchone()
            result["job"] = job_output(dict(existing)) if existing else None
        else:
            result["job"] = enqueue(db, tenant_id, "upload", {"upload_id": result["upload_id"]}, settings)
        return result


@router.get("/uploads")
def uploads(request: Request, tenant_id: Read) -> dict[str, Any]:
    with transaction(request.app.state.settings, tenant_id) as db:
        return {
            "uploads": db.execute(
                "SELECT id,product_id,source_id,filename,media_type,content_hash,metadata,created_at "
                "FROM evidence_uploads WHERE tenant_id=%s AND deleted_at IS NULL ORDER BY created_at DESC",
                (tenant_id,),
            ).fetchall()
        }


@router.get("/uploads/{upload_id}/content")
def image_content(upload_id: UUID, request: Request, tenant_id: Read) -> Response:
    with transaction(request.app.state.settings, tenant_id) as db:
        row = db.execute(
            "SELECT content,media_type,metadata FROM evidence_uploads "
            "WHERE tenant_id=%s AND id=%s AND deleted_at IS NULL",
            (tenant_id, upload_id),
        ).fetchone()
        if row is None:
            raise HTTPException(404, "Upload not found")
        if row["media_type"] not in {"image/png", "image/jpeg", "image/webp"} or not row["metadata"].get(
            "processed"
        ):
            raise HTTPException(409, "Only successfully validated raster images can be viewed")
        return Response(
            bytes(row["content"]),
            media_type=row["media_type"],
            headers={
                "Cache-Control": "private, no-store",
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'; sandbox",
            },
        )


@router.get("/jobs")
def jobs(request: Request, tenant_id: Read) -> dict[str, Any]:
    with transaction(request.app.state.settings, tenant_id) as db:
        rows = db.execute(
            "SELECT * FROM jobs WHERE tenant_id=%s ORDER BY created_at DESC", (tenant_id,)
        ).fetchall()
        return {"jobs": [job_output(dict(row)) for row in rows]}


@router.post("/jobs/{job_id}/retry")
def retry(job_id: UUID, _: EmptyBody, request: Request, tenant_id: Edit) -> dict[str, Any]:
    with authorized_transaction(request, tenant_id, "edit") as db:
        return retry_job(db, tenant_id, str(job_id), request.app.state.settings)


@router.get("/sources/{source_id}/versions")
def source_versions(source_id: str, request: Request, tenant_id: Read) -> dict[str, Any]:
    with transaction(request.app.state.settings, tenant_id) as db:
        return versions(db, tenant_id, source_id)


@router.delete("/sources/{source_id}")
def remove_source(source_id: str, request: Request, tenant_id: Edit) -> dict[str, Any]:
    with authorized_transaction(request, tenant_id, "edit") as db:
        return delete_source(db, tenant_id, source_id, request.app.state.settings)


@router.get("/sources/{source_id}/impact")
def source_impact(source_id: str, request: Request, tenant_id: Read) -> dict[str, Any]:
    with transaction(request.app.state.settings, tenant_id) as db:
        return impact(db, tenant_id, source_id, request.app.state.settings)


@router.post("/context")
def context(body: ContextInput, request: Request, tenant_id: Read) -> dict[str, Any]:
    with transaction(request.app.state.settings, tenant_id) as db:
        return select_context(db, tenant_id, body, request.app.state.engine)


@router.post("/snapshot")
def snapshot(body: SnapshotInput, request: Request, tenant_id: Read) -> dict[str, Any]:
    with transaction(request.app.state.settings, tenant_id) as db:
        passages = [citation(p) for p in current_passages(db, tenant_id, body.product_id)]
        return {
            "snapshot": {
                "version": policy(request.app.state.settings)["version"],
                "hash": digest(passages),
                "passages": passages,
            }
        }


@router.get("/intelligence/{product_id}")
def intelligence(product_id: str, request: Request, tenant_id: Read) -> dict[str, Any]:
    settings = request.app.state.settings
    with transaction(settings, tenant_id) as db:
        if not db.execute(
            "SELECT 1 FROM products p WHERE tenant_id=%s AND id=%s AND NOT EXISTS "
            "(SELECT 1 FROM product_tombstones t WHERE t.tenant_id=p.tenant_id AND t.product_id=p.id)",
            (tenant_id, product_id),
        ).fetchone():
            raise HTTPException(404, "Product not found")
        passages = current_passages(db, tenant_id, product_id)
        relations = db.execute(
            "SELECT id,subject_id,predicate,object_id,revision_id,status,valid_from,valid_to "
            "FROM knowledge_relations WHERE tenant_id=%s AND (subject_id=%s OR object_id=%s) "
            "ORDER BY valid_from DESC",
            (tenant_id, product_id, product_id),
        ).fetchall()
        reviews = db.execute(
            "SELECT id,upload_id,product_id,purpose,observation,alt,function,approved,created_at "
            "FROM image_reviews WHERE tenant_id=%s AND product_id=%s ORDER BY created_at DESC",
            (tenant_id, product_id),
        ).fetchall()
        drafts = db.execute(
            "SELECT id,status,text,citations FROM drafts WHERE tenant_id=%s AND product_id=%s "
            "ORDER BY created_at DESC",
            (tenant_id, product_id),
        ).fetchall()
        return {
            "product_id": product_id,
            **inspect_claims(passages, settings),
            "relations": relations,
            "image_reviews": reviews,
            "json_ld": product_json_ld(db, tenant_id, product_id, settings),
            "drafts": drafts,
            "observation_notice": policy(settings)["image_observation_notice"],
        }


@router.post("/relations")
def relation(body: RelationInput, request: Request, tenant_id: Edit) -> dict[str, Any]:
    settings = request.app.state.settings
    with authorized_transaction(request, tenant_id, "edit") as db:
        tenant_lock(db, tenant_id)
        passages = [
            p
            for p in current_passages(db, tenant_id, body.subject_id)
            if str(p["revision_id"]) == str(body.revision_id)
        ]
        if not passages:
            raise HTTPException(409, "A candidate relation requires current evidence for its subject")
        target = db.execute(
            "SELECT 1 FROM products p WHERE tenant_id=%s AND id=%s AND NOT EXISTS "
            "(SELECT 1 FROM product_tombstones t WHERE t.tenant_id=p.tenant_id AND t.product_id=p.id)",
            (tenant_id, body.object_id),
        ).fetchone()
        source_target = body.object_id in {p["source_id"] for p in passages}
        if body.predicate in {"documented_by", "supported_by"} and not source_target:
            raise HTTPException(409, "Evidence relationships require the exact supporting source")
        if body.predicate in {"compatible_with", "has_variant"} and not target:
            raise HTTPException(404, "Product relationship target is not in this workspace")
        if not target and not source_target:
            raise HTTPException(404, "Relation target not found in this workspace")
        count = db.execute(
            "SELECT count(*) AS n FROM knowledge_relations WHERE tenant_id=%s", (tenant_id,)
        ).fetchone()
        if count and count["n"] >= settings.max_relations:
            raise HTTPException(429, "Relation quota reached")
        identity = str(uuid4())
        row = db.execute(
            "INSERT INTO knowledge_relations(tenant_id,id,subject_id,predicate,object_id,revision_id,status) "
            "VALUES(%s,%s,%s,%s,%s,%s,'candidate') RETURNING *",
            (tenant_id, identity, body.subject_id, body.predicate, body.object_id, body.revision_id),
        ).fetchone()
        audit(db, tenant_id, "relation.candidate", identity, settings)
        return {"relation": {k: v for k, v in dict(row or {}).items() if k != "tenant_id"}}


@router.post("/relations/{relation_id}/approve")
def approve_relation(relation_id: UUID, _: EmptyBody, request: Request, tenant_id: Approve) -> dict[str, Any]:
    settings = request.app.state.settings
    identity = account_identity(request, required=True)
    if identity is None:
        raise HTTPException(401, "An identified reviewer account is required")
    with authorized_transaction(request, tenant_id, "approve") as db:
        tenant_lock(db, tenant_id)
        row = db.execute(
            "SELECT * FROM knowledge_relations WHERE tenant_id=%s AND id=%s FOR UPDATE",
            (tenant_id, relation_id),
        ).fetchone()
        if row is None:
            raise HTTPException(404, "Relation not found")
        evidence = [
            p
            for p in current_passages(db, tenant_id, row["subject_id"])
            if str(p["revision_id"]) == str(row["revision_id"])
        ]
        if row["status"] == "stale" or not evidence:
            raise HTTPException(409, "Relation evidence is no longer current")
        if inspect_claims(evidence, settings)["blocked_claims"]:
            raise HTTPException(409, "Critical claims require separate verification")
        if row["predicate"] in {"compatible_with", "has_variant"}:
            target = db.execute(
                "SELECT fields FROM products WHERE tenant_id=%s AND id=%s", (tenant_id, row["object_id"])
            ).fetchone()
            references = {row["object_id"]}
            if target:
                references.update(str(target["fields"].get(key, "")) for key in ("name", "sku"))
            label = policy(settings)["relation_labels"][row["predicate"]]
            if not any(
                p["label"].casefold() == label.casefold()
                and any(
                    ref and ref.casefold() == p["value"].casefold() and ref.casefold() in p["text"].casefold()
                    for ref in references
                )
                for p in evidence
            ):
                raise HTTPException(409, "Relationship is not explicitly supported by its current source")
        updated = db.execute(
            "UPDATE knowledge_relations SET status='approved',approved_by=%s "
            "WHERE tenant_id=%s AND id=%s RETURNING *",
            (identity["id"], tenant_id, relation_id),
        ).fetchone()
        audit(db, tenant_id, "relation.approved", str(relation_id), settings)
        return {"relation": {k: v for k, v in dict(updated or {}).items() if k != "tenant_id"}}


@router.post("/image-reviews")
def image_review(body: ImageReviewInput, request: Request, tenant_id: Edit) -> dict[str, Any]:
    settings = request.app.state.settings
    with authorized_transaction(request, tenant_id, "edit") as db:
        tenant_lock(db, tenant_id)
        upload = current_image(db, tenant_id, str(body.upload_id))
        text = (body.observation + " " + body.alt).casefold()
        if any(term.casefold() in text for term in policy(settings)["unsafe_claim_terms"]):
            raise HTTPException(422, "Image observations cannot establish critical technical claims")
        count = db.execute(
            "SELECT count(*) AS n FROM image_reviews WHERE tenant_id=%s", (tenant_id,)
        ).fetchone()
        if count and count["n"] >= settings.max_relations:
            raise HTTPException(429, "Image review quota reached")
        row = db.execute(
            "INSERT INTO image_reviews(tenant_id,id,upload_id,product_id,purpose,observation,alt,function) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *",
            (
                tenant_id,
                uuid4(),
                body.upload_id,
                upload["product_id"],
                body.purpose,
                body.observation,
                body.alt,
                body.function,
            ),
        ).fetchone()
        return {"review": {k: v for k, v in dict(row or {}).items() if k != "tenant_id"}}


@router.post("/image-reviews/{review_id}/approve")
def approve_image(review_id: UUID, _: EmptyBody, request: Request, tenant_id: Approve) -> dict[str, Any]:
    settings = request.app.state.settings
    identity = account_identity(request, required=True)
    if identity is None:
        raise HTTPException(401, "An identified reviewer account is required")
    with authorized_transaction(request, tenant_id, "approve") as db:
        tenant_lock(db, tenant_id)
        row = db.execute(
            "SELECT r.* FROM image_reviews r JOIN evidence_uploads u ON u.tenant_id=r.tenant_id "
            "AND u.id=r.upload_id WHERE r.tenant_id=%s AND r.id=%s AND u.deleted_at IS NULL FOR UPDATE OF r",
            (tenant_id, review_id),
        ).fetchone()
        if row is None:
            raise HTTPException(409, "Review image no longer exists")
        current_image(db, tenant_id, str(row["upload_id"]))
        updated = db.execute(
            "UPDATE image_reviews SET approved=true,approved_by=%s,approved_at=now() "
            "WHERE tenant_id=%s AND id=%s RETURNING *",
            (identity["id"], tenant_id, review_id),
        ).fetchone()
        audit(db, tenant_id, "image.alt_approved", str(review_id), settings)
        return {"review": {k: v for k, v in dict(updated or {}).items() if k != "tenant_id"}}


@router.get("/benchmark-dataset")
def benchmark_dataset(request: Request, tenant_id: Read) -> dict[str, Any]:
    with transaction(request.app.state.settings, tenant_id) as db:
        return reviewed_dataset(db, tenant_id, request.app.state.settings)


@router.post("/benchmark-reviews")
def human_review(body: BenchmarkReviewInput, request: Request, tenant_id: Approve) -> dict[str, Any]:
    identity = account_identity(request, required=True)
    if identity is None:
        raise HTTPException(401, "An identified reviewer account is required")
    with authorized_transaction(request, tenant_id, "approve") as db:
        return save_review(db, tenant_id, str(identity["id"]), body, request.app.state.settings)


@router.get("/benchmarks")
def benchmarks(request: Request, tenant_id: Read) -> dict[str, Any]:
    with transaction(request.app.state.settings, tenant_id) as db:
        rows = db.execute(
            "SELECT result FROM benchmark_runs WHERE tenant_id=%s ORDER BY created_at DESC", (tenant_id,)
        ).fetchall()
        return {"benchmarks": [row["result"] for row in rows]}


@router.post("/benchmarks")
def benchmark(_: EmptyBody, request: Request, tenant_id: Edit) -> dict[str, Any]:
    with authorized_transaction(request, tenant_id, "edit") as db:
        return {"benchmark": run_benchmark(db, tenant_id, request.app.state.engine)}
