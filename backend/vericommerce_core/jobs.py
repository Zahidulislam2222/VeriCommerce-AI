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
    return {
        key: value
        for key, value in row.items()
        if key not in {"tenant_id", "payload", "lease_until", "source_generations"}
    }


def enqueue(
    db: Connection, tenant_id: str, kind: str, payload: dict[str, Any], settings: Settings
) -> dict[str, Any]:
    tenant_lock(db, tenant_id)
    count = db.execute("SELECT count(*) AS n FROM jobs WHERE tenant_id=%s", (tenant_id,)).fetchone()
    if count and count["n"] >= settings.max_jobs:
        raise HTTPException(429, "Workspace job retention quota reached; contact its owner")
    identity = str(uuid4())
    generations = {}
    if kind == "ingest":
        for source in payload["sources"]:
            current = db.execute(
                "SELECT generation FROM sources WHERE tenant_id=%s AND id=%s", (tenant_id, source["id"])
            ).fetchone()
            generations[source["id"]] = current["generation"] if current else 0
    row = db.execute(
        "INSERT INTO jobs(tenant_id,id,kind,status,payload,source_generations) "
        "VALUES(%s,%s,%s,'queued',%s,%s) RETURNING *",
        (tenant_id, identity, kind, Jsonb(payload), Jsonb(generations)),
    ).fetchone()
    audit(db, tenant_id, "job.queued", identity, settings)
    if row is None:
        raise RuntimeError("Job insertion failed")
    return job_output(dict(row))


def create_draft(
    db: Connection, tenant_id: str, product_id: str, settings: Settings, kind: str | None = None
) -> dict[str, str]:
    tenant_lock(db, tenant_id)
    count = db.execute("SELECT count(*) AS n FROM drafts WHERE tenant_id=%s", (tenant_id,)).fetchone()
    if count and count["n"] >= settings.max_drafts:
        raise ValueError("Draft quota exceeded")
    passages = current_passages(db, tenant_id, product_id)
    if not passages:
        raise ValueError("No current evidence for that product")
    from .intelligence import inspect_claims

    inspection = inspect_claims(passages, settings)
    if inspection["contradictions"] or inspection["blocked_claims"]:
        raise ValueError("Conflicting or critical unsupported claims require human reconciliation")
    policy = json.loads(settings.policy_path.read_text())
    from .uploads import policy as intelligence_policy

    formats = intelligence_policy(settings)["draft_formats"]
    selected_kind = kind or formats["default"]
    if selected_kind == "faq":
        text = passages[0]["product_name"] + "\n" + formats["faq_heading"] + "\n\n"
        text += "\n\n".join(
            formats["faq_question"].format(label=p["label"]) + "\n" + p["text"] for p in passages
        )
    else:
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
            "SELECT tenant_id FROM demo_sessions WHERE expires_at>now() "
            "ORDER BY last_worker_scan_at NULLS FIRST,created_at,tenant_id LIMIT %s",
            (settings.worker_tenant_batch,),
        ).fetchall()
    for tenant in tenants:
        tenant_id = str(tenant["tenant_id"])
        with transaction(settings, tenant_id) as db:
            # Stamp only tenants actually visited: a busy early tenant cannot starve
            # the unvisited tail of a bounded registry batch.
            db.execute(
                "UPDATE demo_sessions SET last_worker_scan_at=clock_timestamp() WHERE tenant_id=%s",
                (tenant_id,),
            )
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
                    tenant_lock(db, tenant_id)
                    for source_id, generation in job["source_generations"].items():
                        current = db.execute(
                            "SELECT generation FROM sources WHERE tenant_id=%s AND id=%s",
                            (tenant_id, source_id),
                        ).fetchone()
                        if (current["generation"] if current else 0) != generation:
                            raise ValueError("Source changed after job submission; reimport explicitly")
                    result: dict[str, Any] = ingest(
                        db, tenant_id, CatalogInput.model_validate(job["payload"]), settings
                    )
                elif job["kind"] == "upload":
                    from .uploads import process_upload

                    result = process_upload(db, tenant_id, job["payload"]["upload_id"], settings)
                else:
                    result = create_draft(
                        db, tenant_id, job["payload"]["product_id"], settings, job["payload"].get("kind")
                    )
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
