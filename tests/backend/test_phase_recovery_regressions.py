"""Regressions for defects found by independent phase review before deployment."""

from __future__ import annotations

import base64
import csv
import io
import json
from typing import Any
from uuid import uuid4

import pytest
from fastapi import HTTPException
from PIL import Image
from test_phase_ingestion import finish, upload


@pytest.mark.parametrize("media", ["application/json", "text/csv"])
def test_catalog_upload_fences_actual_sources_after_deletion(client: Any, settings: Any, media: str) -> None:
    from vericommerce_core.uploads import policy

    catalog = json.loads(settings.seed_path.read_text())
    product = catalog["products"][0]
    claim = product["claims"][0]
    source = next(s for s in catalog["sources"] if s["id"] == claim["sourceId"])
    actual = {"products": [{**product, "claims": [claim]}], "sources": [source]}
    if media == "application/json":
        raw = json.dumps(actual).encode()
    else:
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=policy(settings)["csv_columns"])
        writer.writeheader()
        writer.writerow(
            {
                "product_id": product["id"],
                "name": product["name"],
                "sku": product["sku"],
                "category": product["category"],
                "source_id": source["id"],
                "source_name": source["name"],
                "version": source["version"],
                "date": source["date"],
                "label": claim["label"],
                "value": claim["value"],
                "passage": claim["passage"],
                "page": claim["page"],
            }
        )
        raw = stream.getvalue().encode()
    queued = upload(client, raw, media, "wrapper-unrelated-source")
    assert queued.status_code == 202
    assert client.delete("/api/sources/" + source["id"]).status_code == 200
    assert finish(client, settings, queued)["status"] == "failed"
    assert source["id"] not in {s["id"] for s in client.get("/api/sources").json()["sources"]}


def test_source_creation_invalidates_image_review_and_reapproval(client: Any, settings: Any) -> None:
    from vericommerce_core.database import transaction
    from vericommerce_core.models import CatalogInput
    from vericommerce_core.repository import ingest
    from vericommerce_core.uploads import current_image

    image = io.BytesIO()
    Image.new("RGB", (16, 16), color="green").save(image, format="PNG")
    received = upload(client, image.getvalue(), "image/png", "visual-only")
    assert finish(client, settings, received)["status"] == "succeeded"
    review = client.post(
        "/api/image-reviews",
        json={
            "upload_id": received.json()["upload_id"],
            "purpose": "informative",
            "alt": "Green schematic",
            "observation": "Green pixels",
        },
    )
    assert review.status_code == 200
    tenant_id = client.get("/api/session").json()["tenant_id"]
    catalog = json.loads(settings.seed_path.read_text())
    product = next(p for p in catalog["products"] if p["id"] == "forma-one")
    product["claims"] = [
        {
            "label": "color",
            "value": "green",
            "sourceId": "visual-only",
            "passage": "A separate catalog declares color green",
            "page": "1",
        }
    ]
    source = {
        "id": "visual-only",
        "name": "New authoritative source",
        "version": "1",
        "type": "catalog",
        "date": "2026-10-18",
    }
    with transaction(settings, tenant_id) as db:
        db.execute(
            "UPDATE image_reviews SET approved=true WHERE tenant_id=%s AND id=%s",
            (tenant_id, review.json()["review"]["id"]),
        )
        ingest(
            db, tenant_id, CatalogInput.model_validate({"products": [product], "sources": [source]}), settings
        )
        row = db.execute(
            "SELECT approved FROM image_reviews WHERE tenant_id=%s AND id=%s",
            (tenant_id, review.json()["review"]["id"]),
        ).fetchone()
        assert row and not row["approved"]
        with pytest.raises(HTTPException) as denied:
            current_image(db, tenant_id, received.json()["upload_id"])
        assert denied.value.status_code == 409


def test_empty_merchant_imports_first_catalog_without_existing_product(
    client: Any, settings: Any, monkeypatch: Any
) -> None:
    from vericommerce_core import uploads

    original = uploads.process_upload
    diagnostics = []

    def process(*args: Any) -> Any:
        try:
            return original(*args)
        except Exception as exc:
            diagnostics.append(type(exc).__name__ + ": " + str(exc))
            raise

    monkeypatch.setattr(uploads, "process_upload", process)
    registered = client.post(
        "/api/auth/register",
        json={
            "email": str(uuid4()) + "@example.test",
            "password": "test-key-long-password",
            "tenant_name": "Empty catalog",
        },
    )
    assert registered.status_code == 200
    assert client.get("/api/products").json()["products"] == []
    payload = {
        "source_id": "first-catalog",
        "filename": "catalog.json",
        "media_type": "application/json",
        "version": "1",
        "content_base64": base64.b64encode(settings.seed_path.read_bytes()).decode(),
    }
    queued = client.post("/api/uploads", json=payload)
    job = finish(client, settings, queued)
    assert job["status"] == "succeeded", {"job": job, "diagnostics": diagnostics}
    assert client.get("/api/products").json()["products"]
    assert client.post("/api/uploads", json=payload).json()["duplicate"]


def test_worker_rotates_past_idle_bounded_batch(settings: Any) -> None:
    from vericommerce_core.database import transaction
    from vericommerce_core.jobs import enqueue, process_one
    from vericommerce_core.models import CatalogInput
    from vericommerce_core.repository import ingest

    configured = settings.model_copy(update={"worker_tenant_batch": 2, "max_active_sessions": 2})
    identities = [str(uuid4()) for _ in range(3)]
    with transaction(settings) as db:
        db.execute("UPDATE demo_sessions SET last_worker_scan_at=now()")
        for index, identity in enumerate(identities):
            db.execute(
                "INSERT INTO demo_sessions(tenant_id,token_hash,mode,expires_at,created_at) "
                "VALUES(%s,%s,'merchant','infinity',now()+(%s * interval '1 second'))",
                (identity, str(uuid4()), index),
            )
    target = identities[-1]
    with transaction(settings, target) as db:
        ingest(db, target, CatalogInput.model_validate_json(settings.seed_path.read_text()), settings)
        job = enqueue(db, target, "draft", {"product_id": "forma-one"}, settings)
    for _ in range(4):
        process_one(configured)
        with transaction(settings, target) as db:
            row = db.execute(
                "SELECT status FROM jobs WHERE tenant_id=%s AND id=%s", (target, job["id"])
            ).fetchone()
        if row and row["status"] == "succeeded":
            break
    assert row and row["status"] == "succeeded"
