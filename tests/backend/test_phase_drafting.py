"""Real persisted FAQ and variant structured-data acceptance flows."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4


def test_faq_is_exact_cited_text_and_source_deletion_blocks_export(client: Any, settings: Any) -> None:
    from vericommerce_core.database import transaction
    from vericommerce_core.jobs import create_draft
    from vericommerce_core.repository import current_passages

    tenant = client.get("/api/session").json()["tenant_id"]
    with transaction(settings, tenant) as db:
        result = create_draft(db, tenant, "forma-one", settings, kind="faq")
        passages = current_passages(db, tenant, "forma-one")
    draft = next(d for d in client.get("/api/drafts").json()["drafts"] if d["id"] == result["draft_id"])
    assert "?" in draft["text"] and all(p["text"] in draft["text"] for p in passages)
    assert {c["passage_id"] for c in draft["citations"]} == {str(p["passage_id"]) for p in passages}
    assert client.post("/api/drafts/" + draft["id"] + "/approve", json={}).status_code == 200
    assert client.get("/api/drafts/" + draft["id"] + "/export").status_code == 200
    assert client.delete("/api/sources/" + passages[0]["source_id"]).status_code == 200
    assert client.get("/api/drafts/" + draft["id"] + "/export").status_code == 409


def test_only_approved_current_variant_relations_produce_consistent_product_group(
    client: Any, settings: Any
) -> None:
    from vericommerce_core.database import transaction
    from vericommerce_core.models import CatalogInput
    from vericommerce_core.repository import ingest

    registered = client.post(
        "/api/auth/register",
        json={
            "email": str(uuid4()) + "@example.test",
            "password": "test-key-long-password",
            "tenant_name": "Variant acceptance",
        },
    )
    assert registered.status_code == 200
    tenant = registered.json()["active_tenant_id"]
    corpus = json.loads(settings.benchmark_path.read_text())
    parent, child = corpus["catalog"]["products"][:2]
    sources = corpus["catalog"]["sources"][:2]
    parent["claims"].append(
        {
            "label": "has variant",
            "value": child["sku"],
            "sourceId": sources[0]["id"],
            "passage": parent["name"] + " has variant " + child["sku"] + ".",
            "page": "1",
        }
    )
    with transaction(settings, tenant) as db:
        ingest(
            db,
            tenant,
            CatalogInput.model_validate({"products": [parent, child], "sources": sources}),
            settings,
        )
    revision = next(s for s in client.get("/api/sources").json()["sources"] if s["id"] == sources[0]["id"])
    candidate = client.post(
        "/api/relations",
        json={
            "subject_id": parent["id"],
            "predicate": "has_variant",
            "object_id": child["id"],
            "revision_id": revision["revision_id"],
        },
    )
    assert candidate.status_code == 200, candidate.text
    before = client.get("/api/intelligence/" + parent["id"]).json()["json_ld"]
    assert before["available"] and before["document"]["@type"] == "Product"
    approved = client.post("/api/relations/" + candidate.json()["relation"]["id"] + "/approve", json={})
    assert approved.status_code == 200, approved.text
    group = client.get("/api/intelligence/" + parent["id"]).json()["json_ld"]
    assert group["available"] and group["document"]["@type"] == "ProductGroup"
    assert group["document"]["hasVariant"][0]["sku"] == child["sku"]
    assert group["document"]["hasVariant"][0]["offers"]["price"] == "50.00"
    assert "variants." + child["id"] + ".color" in group["provenance"]
    for claim in child["claims"]:
        if claim["label"] == "color":
            claim["value"] = "unsupported-color"
            claim["passage"] = "color unsupported-color"
    with transaction(settings, tenant) as db:
        ingest(
            db, tenant, CatalogInput.model_validate({"products": [child], "sources": [sources[1]]}), settings
        )
    after = client.get("/api/intelligence/" + parent["id"]).json()["json_ld"]
    assert not after["available"] and after["document"] is None
