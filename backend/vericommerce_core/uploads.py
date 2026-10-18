"""Durable byte-bounded uploads parsed only in disposable constrained children."""

from __future__ import annotations

import base64
import hashlib
import json
import multiprocessing
import threading
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from .database import Connection, tenant_lock
from .document_parser import parse_document
from .models import CatalogInput
from .phase_models import IntelligencePolicy, UploadInput
from .repository import audit, ingest
from .settings import Settings


def policy(settings: Settings) -> dict[str, Any]:
    return IntelligencePolicy.model_validate_json(settings.intelligence_policy_path.read_text()).model_dump()


def _child(payload: dict[str, Any], pipe: Any) -> None:
    try:
        pipe.send_bytes(json.dumps({"ok": True, "result": parse_document(payload)}).encode())
    except Exception as exc:
        pipe.send_bytes(json.dumps({"ok": False, "error": type(exc).__name__}).encode())
    finally:
        pipe.close()


def isolated_parse(content: bytes, media: str, settings: Settings) -> dict[str, Any]:
    payload = {
        "content_base64": base64.b64encode(content).decode(),
        "media_type": media,
        "memory_bytes": settings.parser_memory_bytes,
        "cpu_seconds": settings.parser_timeout_seconds,
        "max_pages": settings.upload_max_pages,
        "max_pixels": settings.upload_max_pixels,
        "max_text_chars": settings.parser_max_text_chars,
        "max_products": settings.max_products,
        "max_sources": settings.max_sources,
        "csv_columns": policy(settings)["csv_columns"],
    }
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_child, args=(payload, sender), daemon=True)
    process.start()
    sender.close()

    def deadline() -> None:
        if process.is_alive():
            process.kill()

    timer = threading.Timer(settings.parser_timeout_seconds, deadline)
    timer.daemon = True
    timer.start()
    try:
        if not receiver.poll(settings.parser_timeout_seconds):
            raise ValueError("Document parser exceeded its time limit")
        try:
            result = decode_parser_result(receiver.recv_bytes(maxlength=settings.parser_max_result_bytes))
        except (EOFError, OSError):
            raise ValueError("Document parser exceeded resource limits") from None
        if not result["ok"]:
            raise ValueError("Document parser rejected input: " + result["error"])
        return dict(result["result"])
    finally:
        timer.cancel()
        receiver.close()
        if process.is_alive():
            process.terminate()
        process.join(timeout=settings.parser_timeout_seconds)
        if process.is_alive():
            process.kill()
            process.join()


def decode_parser_result(raw: bytes) -> dict[str, Any]:
    """The untrusted child boundary accepts JSON primitives and never unpickles."""
    try:
        result = json.loads(raw)
    except (ValueError, UnicodeDecodeError, RecursionError):
        raise ValueError("Invalid parser transport result") from None
    if not isinstance(result, dict) or type(result.get("ok")) is not bool:
        raise ValueError("Invalid parser envelope")
    if result["ok"]:
        parsed = result.get("result")
        if not isinstance(parsed, dict) or parsed.get("kind") not in {"catalog", "document", "image"}:
            raise ValueError("Invalid parser result type")
        if parsed["kind"] == "catalog":
            CatalogInput.model_validate(parsed.get("catalog"))
        elif parsed["kind"] == "document":
            if type(parsed.get("needs_ocr")) is not bool or not isinstance(parsed.get("pages"), list):
                raise ValueError("Invalid parsed document")
            if any(
                not isinstance(page, dict)
                or not isinstance(page.get("page"), str)
                or not isinstance(page.get("text"), str)
                for page in parsed["pages"]
            ):
                raise ValueError("Invalid parsed passage")
        elif not isinstance(parsed.get("image"), dict) or any(
            type(parsed["image"].get(key)) is not int or parsed["image"][key] <= 0
            for key in ("width", "height")
        ):
            raise ValueError("Invalid parsed image")
    elif not isinstance(result.get("error"), str) or len(result["error"]) > 100:
        raise ValueError("Invalid parser error envelope")
    return dict(result)


def save_upload(db: Connection, tenant_id: str, body: UploadInput, settings: Settings) -> dict[str, Any]:
    tenant_lock(db, tenant_id)
    try:
        content = base64.b64decode(body.content_base64, validate=True)
    except ValueError:
        raise HTTPException(422, "Upload must contain valid base64 bytes") from None
    if not content or len(content) > settings.upload_max_bytes:
        raise HTTPException(413, "Upload exceeds configured byte limit")
    if body.media_type not in policy(settings)["media_types"]:
        raise HTTPException(415, "Unsupported upload format; archives and HTML are not accepted")
    is_catalog = body.media_type in {"application/json", "text/csv"}
    if not is_catalog and body.product_id is None:
        raise HTTPException(422, "PDF and image uploads require an existing product")
    if (
        body.product_id is not None
        and not db.execute(
            "SELECT 1 FROM products WHERE tenant_id=%s AND id=%s", (tenant_id, body.product_id)
        ).fetchone()
    ):
        raise HTTPException(404, "Product not found")
    if (
        body.product_id
        and db.execute(
            "SELECT 1 FROM product_tombstones WHERE tenant_id=%s AND product_id=%s",
            (tenant_id, body.product_id),
        ).fetchone()
    ):
        raise HTTPException(409, "Product is no longer active")
    if db.execute(
        "SELECT 1 FROM source_tombstones WHERE tenant_id=%s AND source_id=%s", (tenant_id, body.source_id)
    ).fetchone():
        raise HTTPException(409, "Deleted sources require a new source identifier for uploads")
    content_hash = hashlib.sha256(content).hexdigest()
    existing = db.execute(
        "SELECT id,deleted_at FROM evidence_uploads WHERE tenant_id=%s "
        "AND product_id IS NOT DISTINCT FROM %s::text AND source_id=%s "
        "AND content_hash=%s",
        (tenant_id, body.product_id, body.source_id, content_hash),
    ).fetchone()
    if existing:
        if existing["deleted_at"]:
            raise HTTPException(409, "This upload was deleted")
        return {"upload_id": str(existing["id"]), "duplicate": True}
    quota = db.execute(
        "SELECT count(*) AS n,coalesce(sum(octet_length(content)),0) AS bytes "
        "FROM evidence_uploads WHERE tenant_id=%s",
        (tenant_id,),
    ).fetchone()
    if quota and (
        quota["n"] >= settings.max_sources
        or quota["bytes"] + len(content) > settings.upload_max_storage_bytes
    ):
        raise HTTPException(429, "Private upload storage quota reached")
    source = db.execute(
        "SELECT generation FROM sources WHERE tenant_id=%s AND id=%s", (tenant_id, body.source_id)
    ).fetchone()
    identity = str(uuid4())
    source_generations = {
        r["id"]: r["generation"]
        for r in db.execute("SELECT id,generation FROM sources WHERE tenant_id=%s", (tenant_id,)).fetchall()
    }
    db.execute(
        "UPDATE image_reviews SET approved=false,approved_by=NULL,approved_at=NULL "
        "WHERE tenant_id=%s AND upload_id IN (SELECT id FROM evidence_uploads "
        "WHERE tenant_id=%s AND product_id=%s AND source_id=%s)",
        (tenant_id, tenant_id, body.product_id, body.source_id),
    )
    db.execute(
        "INSERT INTO evidence_uploads(tenant_id,id,product_id,source_id,filename,media_type,"
        "content_hash,content,metadata,source_generation) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            tenant_id,
            identity,
            body.product_id,
            body.source_id,
            body.filename,
            body.media_type,
            content_hash,
            content,
            Jsonb({"version": body.version, "source_generations": source_generations}),
            source["generation"] if source else 0,
        ),
    )
    audit(db, tenant_id, "upload.received", identity, settings)
    return {"upload_id": identity, "duplicate": False}


def process_upload(db: Connection, tenant_id: str, upload_id: str, settings: Settings) -> dict[str, Any]:
    tenant_lock(db, tenant_id)
    row = db.execute(
        "SELECT * FROM evidence_uploads WHERE tenant_id=%s AND id=%s FOR UPDATE", (tenant_id, upload_id)
    ).fetchone()
    if row is None or row["deleted_at"]:
        raise ValueError("Upload no longer exists")
    if (
        row["product_id"]
        and db.execute(
            "SELECT 1 FROM product_tombstones WHERE tenant_id=%s AND product_id=%s",
            (tenant_id, row["product_id"]),
        ).fetchone()
    ):
        raise ValueError("Upload product is no longer active")
    if row["metadata"].get("processed"):
        return dict(row["metadata"]["result"])
    source = db.execute(
        "SELECT generation FROM sources WHERE tenant_id=%s AND id=%s", (tenant_id, row["source_id"])
    ).fetchone()
    if (source["generation"] if source else 0) != row["source_generation"]:
        raise ValueError("Source changed after upload; submit a fresh source/version")
    if db.execute(
        "SELECT 1 FROM source_tombstones WHERE tenant_id=%s AND source_id=%s", (tenant_id, row["source_id"])
    ).fetchone():
        raise ValueError("Source was deleted")
    parsed = isolated_parse(bytes(row["content"]), row["media_type"], settings)
    if parsed["kind"] == "catalog":
        from .shopify_protocol import connector_owned_id

        catalog_input = CatalogInput.model_validate(parsed["catalog"])
        if any(
            connector_owned_id(p.id) or connector_owned_id(p.parent_product_id or "")
            for p in catalog_input.products
        ) or any(connector_owned_id(s.id) for s in catalog_input.sources):
            raise ValueError("Provider-owned identifiers cannot be overwritten by uploads")
        for supplied in catalog_input.sources:
            current = db.execute(
                "SELECT generation FROM sources WHERE tenant_id=%s AND id=%s", (tenant_id, supplied.id)
            ).fetchone()
            expected = row["metadata"]["source_generations"].get(supplied.id, 0)
            if (current["generation"] if current else 0) != expected or db.execute(
                "SELECT 1 FROM source_tombstones WHERE tenant_id=%s AND source_id=%s",
                (tenant_id, supplied.id),
            ).fetchone():
                raise ValueError("A catalog source changed or was deleted after upload submission")
        result = {
            **ingest(db, tenant_id, catalog_input, settings),
            "upload_id": upload_id,
            "kind": "catalog",
        }
    elif parsed["kind"] == "image" or parsed.get("needs_ocr"):
        result = {"upload_id": upload_id, **parsed, "status": "human_observation_required"}
    else:
        product = db.execute(
            "SELECT fields FROM products WHERE tenant_id=%s AND id=%s", (tenant_id, row["product_id"])
        ).fetchone()
        if not product:
            raise ValueError("Upload product no longer exists")
        chunks = []
        for page in parsed["pages"]:
            for start in range(0, len(page["text"]), 4000):
                text = page["text"][start : start + 4000]
                chunks.append(
                    {
                        "label": "Document passage",
                        "value": text[:500],
                        "sourceId": row["source_id"],
                        "passage": text,
                        "page": page["page"],
                    }
                )
        catalog = CatalogInput.model_validate(
            {
                "products": [{"id": row["product_id"], **product["fields"], "claims": chunks}],
                "sources": [
                    {
                        "id": row["source_id"],
                        "name": row["filename"],
                        "version": row["metadata"]["version"],
                        "type": "uploaded_pdf",
                        "date": datetime.now(UTC).date().isoformat(),
                    }
                ],
            }
        )
        result = {
            **ingest(db, tenant_id, catalog, settings),
            "upload_id": upload_id,
            "kind": "document",
            "needs_ocr": False,
        }
    db.execute(
        "UPDATE evidence_uploads SET metadata=metadata || %s WHERE tenant_id=%s AND id=%s",
        (
            Jsonb(
                {
                    "processed": True,
                    "parsed": parsed
                    if parsed["kind"] == "image"
                    else {"kind": parsed["kind"], "needs_ocr": parsed.get("needs_ocr", False)},
                    "result": result,
                }
            ),
            tenant_id,
            upload_id,
        ),
    )
    return result


def current_image(db: Connection, tenant_id: str, upload_id: str) -> dict[str, Any]:
    row = db.execute(
        "SELECT u.* FROM evidence_uploads u LEFT JOIN sources s ON s.tenant_id=u.tenant_id "
        "AND s.id=u.source_id WHERE u.tenant_id=%s AND u.id=%s AND u.deleted_at IS NULL "
        "AND u.source_generation=coalesce(s.generation,0) "
        "AND NOT EXISTS (SELECT 1 FROM source_tombstones t WHERE t.tenant_id=u.tenant_id "
        "AND t.source_id=u.source_id) "
        "AND NOT EXISTS (SELECT 1 FROM product_tombstones t WHERE t.tenant_id=u.tenant_id "
        "AND t.product_id=u.product_id) "
        "AND NOT EXISTS (SELECT 1 FROM evidence_uploads n WHERE n.tenant_id=u.tenant_id "
        "AND n.product_id=u.product_id AND n.source_id=u.source_id AND n.deleted_at IS NULL "
        "AND (n.created_at,n.id)>(u.created_at,u.id))",
        (tenant_id, upload_id),
    ).fetchone()
    if (
        row is None
        or row["media_type"] not in {"image/png", "image/jpeg", "image/webp"}
        or not row["metadata"].get("processed")
    ):
        raise HTTPException(409, "Image was replaced, deleted, unvalidated or its source changed")
    return dict(row)
