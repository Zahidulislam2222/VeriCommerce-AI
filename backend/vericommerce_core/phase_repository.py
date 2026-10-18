"""History, deletion and explicit recovery; tombstones exclude retained evidence."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from .database import Connection, tenant_lock
from .jobs import job_output
from .repository import audit
from .settings import Settings


def retire_product(db: Connection, tenant_id: str, product_id: str, settings: Settings) -> None:
    """Retain history while removing a provider product from every current view."""
    tenant_lock(db, tenant_id)
    exists = db.execute(
        "SELECT 1 FROM products WHERE tenant_id=%s AND id=%s", (tenant_id, product_id)
    ).fetchone()
    if not exists:
        return
    db.execute(
        "INSERT INTO product_tombstones(tenant_id,product_id) VALUES(%s,%s) "
        "ON CONFLICT(tenant_id,product_id) DO UPDATE SET deleted_at=now()",
        (tenant_id, product_id),
    )
    db.execute(
        "UPDATE drafts SET status='stale',approved_at=NULL WHERE tenant_id=%s AND product_id=%s",
        (tenant_id, product_id),
    )
    db.execute(
        "UPDATE knowledge_relations SET status='stale',valid_to=now() WHERE tenant_id=%s "
        "AND (subject_id=%s OR object_id=%s)",
        (tenant_id, product_id, product_id),
    )
    db.execute(
        "UPDATE image_reviews SET approved=false,approved_by=NULL,approved_at=NULL "
        "WHERE tenant_id=%s AND product_id=%s",
        (tenant_id, product_id),
    )
    audit(db, tenant_id, "product.retired", product_id, settings)


def delete_source(db: Connection, tenant_id: str, source_id: str, settings: Settings) -> dict[str, Any]:
    tenant_lock(db, tenant_id)
    exists = db.execute(
        "SELECT 1 FROM sources WHERE tenant_id=%s AND id=%s", (tenant_id, source_id)
    ).fetchone()
    uploads = db.execute(
        "SELECT 1 FROM evidence_uploads WHERE tenant_id=%s AND source_id=%s", (tenant_id, source_id)
    ).fetchone()
    if not exists and not uploads:
        raise HTTPException(404, "Source not found")
    db.execute(
        "INSERT INTO source_tombstones(tenant_id,source_id) VALUES(%s,%s) "
        "ON CONFLICT(tenant_id,source_id) DO UPDATE SET deleted_at=now()",
        (tenant_id, source_id),
    )
    db.execute(
        "UPDATE sources SET generation=generation+1 WHERE tenant_id=%s AND id=%s", (tenant_id, source_id)
    )
    stale = db.execute(
        "UPDATE drafts SET status='stale',approved_at=NULL WHERE tenant_id=%s AND status!='stale' "
        "AND citations @> %s RETURNING id",
        (tenant_id, Jsonb([{"source_id": source_id}])),
    ).fetchall()
    db.execute(
        "UPDATE knowledge_relations SET status='stale',valid_to=now() WHERE tenant_id=%s "
        "AND revision_id IN (SELECT id FROM source_revisions WHERE tenant_id=%s AND source_id=%s)",
        (tenant_id, tenant_id, source_id),
    )
    db.execute(
        "UPDATE image_reviews SET approved=false,approved_by=NULL,approved_at=NULL "
        "WHERE tenant_id=%s AND upload_id IN (SELECT id FROM evidence_uploads "
        "WHERE tenant_id=%s AND source_id=%s)",
        (tenant_id, tenant_id, source_id),
    )
    db.execute(
        "UPDATE evidence_uploads SET content=%s,deleted_at=now() WHERE tenant_id=%s AND source_id=%s",
        (b"", tenant_id, source_id),
    )
    audit(db, tenant_id, "source.deleted", source_id, settings)
    return {"source_id": source_id, "stale_drafts": len(stale), "deleted": True}


def versions(db: Connection, tenant_id: str, source_id: str) -> dict[str, Any]:
    rows = db.execute(
        "SELECT r.id AS revision_id,r.metadata,r.content_hash,r.created_at,"
        "(s.current_revision_id=r.id AND t.source_id IS NULL) AS current "
        "FROM source_revisions r LEFT JOIN sources s ON s.tenant_id=r.tenant_id AND s.id=r.source_id "
        "LEFT JOIN source_tombstones t ON t.tenant_id=r.tenant_id AND t.source_id=r.source_id "
        "WHERE r.tenant_id=%s AND r.source_id=%s ORDER BY r.created_at DESC,r.id",
        (tenant_id, source_id),
    ).fetchall()
    if not rows:
        raise HTTPException(404, "Source not found")
    result = []
    for row in rows:
        passages = db.execute(
            "SELECT id AS passage_id,product_id,label,value,text,page FROM passages "
            "WHERE tenant_id=%s AND revision_id=%s ORDER BY position,id",
            (tenant_id, row["revision_id"]),
        ).fetchall()
        result.append({**row, "passages": passages})
    return {"versions": result}


def retry_job(db: Connection, tenant_id: str, job_id: str, settings: Settings) -> dict[str, Any]:
    tenant_lock(db, tenant_id)
    row = db.execute(
        "SELECT * FROM jobs WHERE tenant_id=%s AND id=%s FOR UPDATE", (tenant_id, job_id)
    ).fetchone()
    if row is None:
        raise HTTPException(404, "Job not found")
    if row["status"] != "failed" or row["attempts"] >= settings.worker_max_attempts:
        raise HTTPException(409, "Only failed jobs within their original attempt budget may retry")
    if row["kind"] == "upload":
        upload = db.execute(
            "SELECT deleted_at FROM evidence_uploads WHERE tenant_id=%s AND id=%s",
            (tenant_id, row["payload"]["upload_id"]),
        ).fetchone()
        if upload is None or upload["deleted_at"]:
            raise HTTPException(409, "Deleted uploads cannot retry")
    updated = db.execute(
        "UPDATE jobs SET status='queued',error=NULL,available_at=now(),lease_until=NULL "
        "WHERE tenant_id=%s AND id=%s RETURNING *",
        (tenant_id, job_id),
    ).fetchone()
    audit(db, tenant_id, "job.manual_retry", job_id, settings)
    return {"job": job_output(dict(updated or {}))}
