"""Real API tests for constrained context, graph provenance and frozen evaluations."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


def tenant(client: Any) -> str:
    return str(client.get("/api/session").json()["tenant_id"])


def test_context_constraints_budget_and_unavailable_methods(client: Any) -> None:
    products = client.get("/api/products").json()["products"]
    product = products[0]
    selected = client.post(
        "/api/context",
        json={
            "query": "battery life",
            "product_id": product["id"],
            "method": "keyword",
            "budget_chars": 100,
        },
    )
    assert selected.status_code == 200, selected.text
    response = selected.json()
    assert response["available"] and response["context"]["used_chars"] <= 100
    assert all(c["product_id"] == product["id"] for c in response["results"])
    denied = client.post(
        "/api/context",
        json={
            "query": "battery",
            "product_id": product["id"],
            "sku": "impossible-sku",
            "method": "keyword",
        },
    ).json()
    assert not denied["results"] and not denied["context"]["eligible_products"]
    unavailable = client.post("/api/context", json={"query": "battery", "method": "dense"}).json()
    assert unavailable["available"] is False and unavailable["method"] == "dense"


def test_source_delete_changes_snapshot_and_excludes_evidence(client: Any) -> None:
    original = client.post("/api/snapshot", json={}).json()["snapshot"]
    source_id = client.get("/api/sources").json()["sources"][0]["id"]
    response = client.delete("/api/sources/" + source_id, headers={"Content-Type": "application/json"})
    assert response.status_code == 200, response.text
    after = client.post("/api/snapshot", json={}).json()["snapshot"]
    assert after["hash"] != original["hash"]
    assert all(c["source_id"] != source_id for c in after["passages"])
    assert source_id not in {
        r["source_id"]
        for r in client.post(
            "/api/context",
            json={"query": "battery sound material", "method": "keyword"},
        ).json()["results"]
    }


def test_unit_normalized_conflicts_and_critical_claim_rejection(client: Any, settings: Any) -> None:
    from vericommerce_core.database import transaction
    from vericommerce_core.jobs import create_draft
    from vericommerce_core.models import CatalogInput
    from vericommerce_core.repository import ingest

    identity = tenant(client)
    catalog = json.loads(settings.seed_path.read_text())
    product = catalog["products"][0]
    source = catalog["sources"][0]
    body = {
        "products": [
            {
                **product,
                "claims": [
                    {
                        "label": "length",
                        "value": "10 cm",
                        "sourceId": source["id"],
                        "passage": "Length 10 cm",
                        "page": "1",
                    },
                    {
                        "label": "length",
                        "value": "100 mm",
                        "sourceId": source["id"],
                        "passage": "Length 100 mm",
                        "page": "2",
                    },
                ],
            }
        ],
        "sources": [source],
    }
    with transaction(settings, identity) as db:
        ingest(db, identity, CatalogInput.model_validate(body), settings)
    assert not client.get("/api/intelligence/" + product["id"]).json()["contradictions"]
    changed = copy.deepcopy(body)
    changed["products"][0]["claims"][1]["value"] = "101 mm"
    changed["products"][0]["claims"][1]["passage"] = "Length 101 mm"
    with transaction(settings, identity) as db:
        ingest(db, identity, CatalogInput.model_validate(changed), settings)
    assert client.get("/api/intelligence/" + product["id"]).json()["contradictions"]
    import pytest

    with transaction(settings, identity) as db, pytest.raises(ValueError):
        create_draft(db, identity, product["id"], settings)
    changed["products"][0]["claims"] = [
        {
            "label": "safety",
            "value": "guaranteed safe",
            "sourceId": source["id"],
            "passage": "guaranteed safe",
            "page": "1",
        }
    ]
    with transaction(settings, identity) as db:
        ingest(db, identity, CatalogInput.model_validate(changed), settings)
    result = client.get("/api/intelligence/" + product["id"]).json()
    assert result["blocked_claims"] and not result["json_ld"]["available"]


def test_structured_data_all_fields_have_current_provenance(client: Any, settings: Any) -> None:
    from vericommerce_core.benchmark import dataset
    from vericommerce_core.database import transaction
    from vericommerce_core.models import CatalogInput
    from vericommerce_core.repository import ingest

    corpus = dataset(settings)
    catalog = {
        "products": [corpus["catalog"]["products"][0]],
        "sources": [corpus["catalog"]["sources"][0]],
    }
    with transaction(settings, tenant(client)) as db:
        ingest(db, tenant(client), CatalogInput.model_validate(catalog), settings)
    result = client.get("/api/intelligence/atlas-1").json()["json_ld"]
    assert result["available"], result
    assert result["document"]["offers"]["price"] == "49.00"
    assert result["document"]["offers"]["priceCurrency"] == "USD"
    assert result["document"]["offers"]["availability"].endswith("/InStock")
    assert set(result["provenance"]) == {
        "name",
        "sku",
        "price",
        "currency",
        "availability",
    }
    catalog["products"][0]["sku"] = "visible-mismatch"
    with transaction(settings, tenant(client)) as db:
        ingest(db, tenant(client), CatalogInput.model_validate(catalog), settings)
    assert not client.get("/api/intelligence/atlas-1").json()["json_ld"]["available"]


def test_relations_are_current_candidates_and_impact_finds_dependents(client: Any, settings: Any) -> None:
    from vericommerce_core.database import transaction
    from vericommerce_core.jobs import create_draft

    source = client.get("/api/sources").json()["sources"][0]
    version = client.get("/api/sources/" + source["id"] + "/versions").json()["versions"][0]
    product = version["passages"][0]["product_id"]
    candidate = client.post(
        "/api/relations",
        json={
            "subject_id": product,
            "predicate": "documented_by",
            "object_id": source["id"],
            "revision_id": version["revision_id"],
        },
    )
    assert candidate.status_code == 200, candidate.text
    assert candidate.json()["relation"]["status"] == "candidate"
    with transaction(settings, tenant(client)) as db:
        draft = create_draft(db, tenant(client), product, settings)
    impact = client.get("/api/sources/" + source["id"] + "/impact").json()
    assert draft["draft_id"] in {d["id"] for d in impact["drafts"]}
    client.delete("/api/sources/" + source["id"], headers={"Content-Type": "application/json"})
    assert client.get("/api/intelligence/" + product).json()["relations"][0]["status"] == "stale"


def test_new_phase_endpoints_preserve_two_tenant_isolation(client: Any, settings: Any) -> None:
    from vericommerce_core.main import create_app

    source = client.get("/api/sources").json()["sources"][0]
    revision_id = source["revision_id"]
    with TestClient(
        create_app(settings),
        base_url="https://testserver",
        headers={"Origin": "https://testserver"},
    ) as other:
        assert other.post("/api/session", json={}).status_code == 200
        versions = other.get("/api/sources/" + source["id"] + "/versions").json()["versions"]
        assert revision_id not in {v["revision_id"] for v in versions}
        product_id = client.get("/api/products").json()["products"][0]["id"]
        result = other.post(
            "/api/relations",
            json={
                "subject_id": product_id,
                "predicate": "documented_by",
                "object_id": source["id"],
                "revision_id": revision_id,
            },
        )
        assert result.status_code == 409
        assert (
            client.post("/api/snapshot", json={}).json()["snapshot"]["hash"]
            != other.post("/api/snapshot", json={}).json()["snapshot"]["hash"]
        )


def test_frozen_corpus_size_split_hash_and_human_gate(client: Any, settings: Any) -> None:
    from vericommerce_core.benchmark import dataset
    from vericommerce_core.repository import digest

    corpus = dataset(settings)
    assert len(corpus["products"]) == 30 and len(corpus["images"]) == 120 and len(corpus["questions"]) == 200
    assert len([q for q in corpus["questions"] if q["split"] == "test"]) >= 50
    family_splits: dict[str, set[str]] = {}
    for product in corpus["products"]:
        family_splits.setdefault(product["family"], set()).add(product["split"])
    assert all(len(splits) == 1 for splits in family_splits.values())
    import hashlib

    root = Path(__file__).resolve().parents[2]
    for asset in corpus["images"]:
        assert (
            hashlib.sha256((root / "public" / asset["path"].lstrip("/")).read_bytes()).hexdigest()
            == asset["sha256"]
        )
    frozen = dict(corpus)
    expected = frozen.pop("hash")
    assert digest(frozen) == expected
    reviewed = client.get("/api/benchmark-dataset").json()
    assert reviewed["human_review_status"] == "pending"
    assert reviewed["review_status"] in {"pending", "agent_reviewed"}
    rejected = client.post(
        "/api/benchmark-reviews",
        json={
            "dataset_hash": expected,
            "question_ids": [corpus["questions"][0]["id"]],
            "image_ids": [],
            "decision": "approved",
            "notes": "",
        },
    )
    assert rejected.status_code == 401


def test_benchmark_measures_actual_keyword_and_marks_dense_unavailable(
    client: Any,
) -> None:
    response = client.post("/api/benchmarks", json={})
    assert response.status_code == 200, response.text
    result = response.json()["benchmark"]
    assert result["human_review_status"] == "pending" and result["split"] == "test"
    assert result["review_status"] in {"pending", "agent_reviewed"}
    keyword = next(r for r in result["results"] if r["method"] == "keyword")
    assert keyword["available"] and keyword["recall_at_10"] >= 0.85
    assert 0 <= keyword["ndcg_at_10"] <= 1 and keyword["latency_ms_p95"] >= 0
    assert all(
        not r["available"] and r["recall_at_10"] is None
        for r in result["results"]
        if r["method"] != "keyword"
    )
    assert client.get("/api/benchmarks").json()["benchmarks"][0]["id"] == result["id"]
