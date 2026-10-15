"""Durable per-tenant queue; bounded retries and interruption-safe transactional work."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from .database import Connection, tenant_lock, transaction
from .models import CatalogInput
from .repository import audit, citation, current_passages, ingest, source_fingerprint
from .settings import Settings


def job_output(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key not in {"tenant_id", "payload", "lease_until"}}


def enqueue(
    db: Connection, tenant_id: str, kind: str, payload: dict[str, Any], settings: Settings
) -> dict[str, Any]:
    tenant_lock(db, tenant_id)
    count = db.execute("SELECT count(*) AS n FROM jobs WHERE tenant_id=%s", (tenant_id,)).fetchone()
    if count and count["n"] >= settings.max_jobs:
        raise HTTPException(429, "Workspace job quota reached; wait for session expiry")
    identity = str(uuid4())
    row = db.execute(
        "INSERT INTO jobs(tenant_id,id,kind,status,payload) VALUES(%s,%s,%s,'queued',%s) RETURNING *",
        (tenant_id, identity, kind, Jsonb(payload)),
    ).fetchone()
    audit(db, tenant_id, "job.queued", identity, settings)
    if row is None:
        raise RuntimeError("Job insertion failed")
    return job_output(dict(row))


def create_draft(db: Connection, tenant_id: str, product_id: str, settings: Settings) -> dict[str, str]:
    tenant_lock(db, tenant_id)
    count = db.execute("SELECT count(*) AS n FROM drafts WHERE tenant_id=%s", (tenant_id,)).fetchone()
    if count and count["n"] >= settings.max_drafts:
        raise ValueError("Draft quota exceeded")
    passages = current_passages(db, tenant_id, product_id)
    if not passages:
        raise ValueError("No current evidence for that product")
    policy = json.loads(settings.policy_path.read_text())
    text = passages[0]["product_name"] + "\n" + policy["draft_heading"] + "\n\n"
    text += "\n\n".join(p["text"] for p in passages)
    identity = str(uuid4())
    db.execute(
        "INSERT INTO drafts(tenant_id,id,product_id,text,citations,source_fingerprint,method,status) "
        "VALUES(%s,%s,%s,%s,%s,%s,%s,'draft')",
        (
            tenant_id,
            identity,
            product_id,
            text,
            Jsonb([citation(p) for p in passages]),
            source_fingerprint(passages),
            policy["draft_method"],
        ),
    )
    audit(db, tenant_id, "draft.created", identity, settings)
    return {"draft_id": identity}


def process_one(settings: Settings) -> bool:
    with transaction(settings) as db:
        tenants = db.execute(
            "SELECT tenant_id FROM demo_sessions WHERE expires_at>now() ORDER BY created_at LIMIT %s",
            (settings.worker_tenant_batch,),
        ).fetchall()
    for tenant in tenants:
        tenant_id = str(tenant["tenant_id"])
        with transaction(settings, tenant_id) as db:
            db.execute(
                "UPDATE jobs SET status='failed',error='Retry budget exhausted after interrupted work',"
                "lease_until=NULL WHERE tenant_id=%s AND status='running' "
                "AND lease_until<now() AND attempts>=%s",
                (tenant_id, settings.worker_max_attempts),
            )
            row = db.execute(
                "SELECT * FROM jobs WHERE tenant_id=%s AND attempts<%s AND available_at<=now() "
                "AND (status='queued' OR (status='running' AND lease_until<now())) "
                "ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1",
                (tenant_id, settings.worker_max_attempts),
            ).fetchone()
            if row is None:
                continue
            job = dict(row)
            db.execute(
                "UPDATE jobs SET status='running',attempts=attempts+1,"
                "lease_until=now()+(%s * interval '1 second') WHERE tenant_id=%s AND id=%s",
                (settings.worker_lease_seconds, tenant_id, job["id"]),
            )
        try:
            with transaction(settings, tenant_id) as db:
                # Claim attempts fence a paused worker after its expired lease was reclaimed.
                owned = db.execute(
                    "SELECT status,attempts FROM jobs WHERE tenant_id=%s AND id=%s FOR UPDATE",
                    (tenant_id, job["id"]),
                ).fetchone()
                expected_attempt = job["attempts"] + 1
                if owned is None or owned["status"] != "running" or owned["attempts"] != expected_attempt:
                    return True
                if job["kind"] == "ingest":
                    result: dict[str, Any] = ingest(
                        db, tenant_id, CatalogInput.model_validate(job["payload"]), settings
                    )
                else:
                    result = create_draft(db, tenant_id, job["payload"]["product_id"], settings)
                db.execute(
                    "UPDATE jobs SET status='succeeded',result=%s,error=NULL,lease_until=NULL "
                    "WHERE tenant_id=%s AND id=%s AND status='running' AND attempts=%s",
                    (Jsonb(result), tenant_id, job["id"], expected_attempt),
                )
                audit(db, tenant_id, "job.succeeded", str(job["id"]), settings)
        except Exception as exc:
            with transaction(settings, tenant_id) as db:
                terminal = (
                    isinstance(exc, (ValueError, HTTPException))
                    or job["attempts"] + 1 >= settings.worker_max_attempts
                )
                changed = db.execute(
                    "UPDATE jobs SET status=%s,error=%s,lease_until=NULL,"
                    "available_at=now()+(%s * interval '1 second') WHERE tenant_id=%s AND id=%s "
                    "AND status='running' AND attempts=%s RETURNING id",
                    (
                        "failed" if terminal else "queued",
                        "Job could not complete: " + type(exc).__name__,
                        settings.worker_retry_seconds,
                        tenant_id,
                        job["id"],
                        job["attempts"] + 1,
                    ),
                ).fetchone()
                if changed:
                    audit(db, tenant_id, "job.failed" if terminal else "job.retry", str(job["id"]), settings)
        return True
    return False
