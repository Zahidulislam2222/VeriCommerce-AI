"""Tenant-scoped evidence/versioning transactions; every SQL value is parameterized."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from .database import Connection, tenant_lock
from .models import CatalogInput
from .settings import Settings


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def audit(db: Connection, tenant_id: str, action: str, entity_id: str, settings: Settings) -> None:
    db.execute(
        "INSERT INTO audit_events(tenant_id,id,action,entity_id) VALUES(%s,%s,%s,%s)",
        (tenant_id, uuid4(), action, entity_id),
    )
    db.execute(
        "DELETE FROM audit_events WHERE tenant_id=%s AND id IN "
        "(SELECT id FROM audit_events WHERE tenant_id=%s ORDER BY created_at DESC OFFSET %s)",
        (tenant_id, tenant_id, settings.max_audit_events),
    )


def ingest(db: Connection, tenant_id: str, catalog: CatalogInput, settings: Settings) -> dict[str, int]:
    tenant_lock(db, tenant_id)
    present_fields = {
        r["id"]: r["fields"]
        for r in db.execute("SELECT id,fields FROM products WHERE tenant_id=%s", (tenant_id,))
    }
    present_products = set(present_fields)
    present_sources = {r["id"] for r in db.execute("SELECT id FROM sources WHERE tenant_id=%s", (tenant_id,))}
    if len(present_products | {p.id for p in catalog.products}) > settings.max_products:
        raise ValueError("Product quota exceeded")
    if len(present_sources | {s.id for s in catalog.sources}) > settings.max_sources:
        raise ValueError("Source quota exceeded")
    incoming_passages = sum(len(p.claims) for p in catalog.products)
    if incoming_passages > settings.max_passages:
        raise ValueError("Passage quota exceeded")
    counts = {
        "products_upserted": len(catalog.products),
        "sources_changed": 0,
        "sources_unchanged": 0,
        "stale_drafts": 0,
    }
    for product in catalog.products:
        fields = product.model_dump(exclude={"claims", "draft", "status", "id"})
        if fields.get("parent_product_id") is None:
            fields.pop("parent_product_id", None)
        db.execute(
            "DELETE FROM product_tombstones WHERE tenant_id=%s AND product_id=%s",
            (tenant_id, product.id),
        )
        if product.id in present_fields and present_fields[product.id] == fields:
            continue
        if product.id in present_fields:
            affected = db.execute(
                "UPDATE drafts SET status='stale',approved_at=NULL WHERE tenant_id=%s "
                "AND product_id=%s AND status!='stale' RETURNING id",
                (tenant_id, product.id),
            ).fetchall()
            counts["stale_drafts"] += len(affected)
        db.execute(
            "INSERT INTO products(tenant_id,id,fields) VALUES(%s,%s,%s) "
            "ON CONFLICT(tenant_id,id) DO UPDATE SET fields=EXCLUDED.fields,updated_at=now()",
            (tenant_id, product.id, Jsonb(fields)),
        )
    for source in catalog.sources:
        claims = sorted(
            [
                {"product_id": p.id, **c.model_dump()}
                for p in catalog.products
                for c in p.claims
                if c.sourceId == source.id
            ],
            key=lambda item: (item["product_id"], item["label"], item["page"], item["passage"]),
        )
        if not claims:
            raise ValueError("Each supplied source requires at least one supporting passage")
        metadata = source.model_dump(mode="json")
        content_hash = digest({"metadata": metadata, "claims": claims})
        current = db.execute(
            "SELECT s.current_revision_id,r.content_hash FROM sources s JOIN source_revisions r "
            "ON r.tenant_id=s.tenant_id AND r.id=s.current_revision_id WHERE s.tenant_id=%s AND s.id=%s",
            (tenant_id, source.id),
        ).fetchone()
        tombstone = db.execute(
            "SELECT 1 FROM source_tombstones WHERE tenant_id=%s AND source_id=%s",
            (tenant_id, source.id),
        ).fetchone()
        if current and current["content_hash"] == content_hash and not tombstone:
            counts["sources_unchanged"] += 1
            continue
        revision_count = db.execute(
            "SELECT count(*) AS n FROM source_revisions WHERE tenant_id=%s AND source_id=%s",
            (tenant_id, source.id),
        ).fetchone()
        if revision_count and revision_count["n"] >= settings.max_revisions_per_source:
            raise ValueError("Source revision quota exceeded")
        old_revision = str(current["current_revision_id"]) if current else None
        revision_id = str(uuid4())
        previous = db.execute(
            "SELECT id FROM source_revisions WHERE tenant_id=%s AND source_id=%s AND content_hash=%s",
            (tenant_id, source.id, content_hash),
        ).fetchone()
        if previous:
            revision_id = str(previous["id"])
        else:
            db.execute(
                "INSERT INTO source_revisions(tenant_id,id,source_id,metadata,content_hash,"
                "supersedes_revision_id) "
                "VALUES(%s,%s,%s,%s,%s,%s)",
                (tenant_id, revision_id, source.id, Jsonb(metadata), content_hash, old_revision),
            )
            for position, claim in enumerate(claims):
                db.execute(
                    "INSERT INTO passages(tenant_id,id,revision_id,product_id,label,value,text,"
                    "page,position) "
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        tenant_id,
                        uuid4(),
                        revision_id,
                        claim["product_id"],
                        claim["label"],
                        claim["value"],
                        claim["passage"],
                        claim["page"],
                        position,
                    ),
                )
        db.execute(
            "INSERT INTO sources(tenant_id,id,current_revision_id) VALUES(%s,%s,%s) "
            "ON CONFLICT(tenant_id,id) DO UPDATE SET current_revision_id=EXCLUDED.current_revision_id,"
            "generation=sources.generation+1",
            (tenant_id, source.id, revision_id),
        )
        db.execute(
            "DELETE FROM source_tombstones WHERE tenant_id=%s AND source_id=%s", (tenant_id, source.id)
        )
        if old_revision:
            invalidated = db.execute(
                "UPDATE drafts SET status='stale',approved_at=NULL WHERE tenant_id=%s AND status!='stale' "
                "AND citations @> %s RETURNING id",
                (tenant_id, Jsonb([{"revision_id": old_revision}])),
            ).fetchall()
            counts["stale_drafts"] += len(invalidated)
            db.execute(
                "UPDATE knowledge_relations SET status='stale',valid_to=now() "
                "WHERE tenant_id=%s AND revision_id=%s AND status!='stale'",
                (tenant_id, old_revision),
            )
        db.execute(
            "UPDATE image_reviews SET approved=false,approved_by=NULL,approved_at=NULL "
            "WHERE tenant_id=%s AND upload_id IN (SELECT id FROM evidence_uploads "
            "WHERE tenant_id=%s AND source_id=%s)",
            (tenant_id, tenant_id, source.id),
        )
        counts["sources_changed"] += 1
        audit(db, tenant_id, "source.revision_created", source.id, settings)
    live_count = db.execute(
        "SELECT count(*) AS n FROM passages p JOIN sources s ON p.tenant_id=s.tenant_id "
        "AND p.revision_id=s.current_revision_id WHERE p.tenant_id=%s AND NOT EXISTS "
        "(SELECT 1 FROM source_tombstones t WHERE t.tenant_id=s.tenant_id AND t.source_id=s.id)",
        (tenant_id,),
    ).fetchone()
    if live_count and live_count["n"] > settings.max_passages:
        raise ValueError("Current passage quota exceeded")
    return counts


def current_passages(db: Connection, tenant_id: str, product_id: str | None = None) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in db.execute(
            "SELECT p.id AS passage_id,p.product_id,pr.fields->>'name' AS product_name,"
            "p.label,p.value,p.text,p.page,p.embedding,p.embedding_revision,r.id AS revision_id,"
            "r.source_id,r.metadata->>'name' AS source_name,"
            "r.metadata->>'version' AS source_version FROM passages p "
            "JOIN sources s ON s.tenant_id=p.tenant_id AND s.current_revision_id=p.revision_id "
            "JOIN source_revisions r ON r.tenant_id=p.tenant_id AND r.id=p.revision_id "
            "JOIN products pr ON pr.tenant_id=p.tenant_id AND pr.id=p.product_id "
            "WHERE p.tenant_id=%s AND (%s::text IS NULL OR p.product_id=%s) "
            "AND NOT EXISTS (SELECT 1 FROM source_tombstones t WHERE t.tenant_id=s.tenant_id "
            "AND t.source_id=s.id) "
            "AND NOT EXISTS (SELECT 1 FROM product_tombstones t WHERE t.tenant_id=p.tenant_id "
            "AND t.product_id=p.product_id) "
            "ORDER BY p.product_id,p.position,p.id",
            (tenant_id, product_id, product_id),
        ).fetchall()
    ]


def citation(passage: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "passage_id",
        "product_id",
        "product_name",
        "source_id",
        "source_name",
        "source_version",
        "revision_id",
        "page",
        "text",
    )
    return {key: str(passage[key]) for key in keys}


def source_fingerprint(passages: list[dict[str, Any]]) -> str:
    return digest(sorted((str(p["passage_id"]), str(p["revision_id"])) for p in passages))


def products(db: Connection, tenant_id: str) -> list[dict[str, Any]]:
    rows = db.execute(
        "SELECT id,fields FROM products p WHERE tenant_id=%s AND NOT EXISTS "
        "(SELECT 1 FROM product_tombstones t WHERE t.tenant_id=p.tenant_id "
        "AND t.product_id=p.id) ORDER BY id",
        (tenant_id,),
    ).fetchall()
    evidence = current_passages(db, tenant_id)
    return [
        {
            "id": row["id"],
            **row["fields"],
            "claims": [
                {
                    "label": p["label"],
                    "value": p["value"],
                    "sourceId": p["source_id"],
                    "passage": p["text"],
                    "page": p["page"],
                    "passage_id": str(p["passage_id"]),
                    "source_version": p["source_version"],
                }
                for p in evidence
                if p["product_id"] == row["id"]
            ],
        }
        for row in rows
    ]


def eligible_products(
    db: Connection,
    tenant_id: str,
    query: str,
    product_id: str | None = None,
    sku: str | None = None,
    color: str | None = None,
    category: str | None = None,
) -> list[str]:
    """Apply current product and variant constraints before retrieval/model work."""
    rows = db.execute(
        "SELECT id,fields FROM products p WHERE tenant_id=%s AND NOT EXISTS "
        "(SELECT 1 FROM product_tombstones t WHERE t.tenant_id=p.tenant_id "
        "AND t.product_id=p.id)",
        (tenant_id,),
    ).fetchall()
    query_tokens = set(re.findall(r"[a-z0-9_-]+", query.casefold()))
    # Query SKU entities take precedence over an accompanying parent name.
    sku_entities = {
        row["id"]
        for row in rows
        if row["fields"].get("sku") and str(row["fields"]["sku"]).casefold() in query_tokens
    }
    matching = []
    for row in rows:
        identity, fields = row["id"], row["fields"]
        if (
            product_id
            and identity != product_id
            and not ((sku or color or sku_entities) and fields.get("parent_product_id") == product_id)
        ):
            continue
        if any(
            value is not None and str(fields.get(key, "")).casefold() != value.casefold()
            for key, value in (("sku", sku), ("color", color), ("category", category))
        ):
            continue
        matching.append(row)
    if sku_entities:
        return [row["id"] for row in matching if row["id"] in sku_entities]
    named = [
        row["id"]
        for row in matching
        if row["fields"].get("name") and str(row["fields"]["name"]).casefold() in query.casefold()
    ]
    return named or [row["id"] for row in matching]


def sources(db: Connection, tenant_id: str) -> list[dict[str, Any]]:
    rows = db.execute(
        "SELECT r.id AS revision_id,r.metadata,r.content_hash,(SELECT count(*) FROM passages p "
        "WHERE p.tenant_id=r.tenant_id AND p.revision_id=r.id) AS passage_count FROM sources s "
        "JOIN source_revisions r ON r.tenant_id=s.tenant_id AND r.id=s.current_revision_id "
        "WHERE s.tenant_id=%s AND NOT EXISTS (SELECT 1 FROM source_tombstones t "
        "WHERE t.tenant_id=s.tenant_id AND t.source_id=s.id) ORDER BY s.id",
        (tenant_id,),
    ).fetchall()
    return [
        {
            **r["metadata"],
            "revision_id": str(r["revision_id"]),
            "content_hash": r["content_hash"],
            "passage_count": r["passage_count"],
        }
        for r in rows
    ]


def draft_output(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key not in {"tenant_id", "source_fingerprint"}}


def draft_by_id(db: Connection, tenant_id: str, draft_id: str, lock: bool = False) -> dict[str, Any]:
    query = (
        "SELECT d.*,p.fields->>'name' AS product_name FROM drafts d JOIN products p "
        "ON p.tenant_id=d.tenant_id AND p.id=d.product_id WHERE d.tenant_id=%s AND d.id=%s"
    )
    if lock:
        query += " FOR UPDATE OF d"
    row = db.execute(query, (tenant_id, draft_id)).fetchone()
    if row is None:
        raise HTTPException(404, "Draft not found")
    return dict(row)


def ensure_current_draft(db: Connection, tenant_id: str, draft: dict[str, Any]) -> None:
    evidence = current_passages(db, tenant_id, draft["product_id"])
    if draft["status"] == "stale" or source_fingerprint(evidence) != draft["source_fingerprint"]:
        raise HTTPException(409, "Source evidence changed; generate and review a fresh draft")
