"""Provider HTTP import to real PostgreSQL exact variant context/lifecycle regressions."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import numpy as np
import pytest
import test_identity_and_shopify as support
from vericommerce_core.database import transaction
from vericommerce_core.jobs import create_draft


@pytest.fixture(autouse=True)
def store(monkeypatch: Any) -> None:
    monkeypatch.setattr(support, "SHOP", f"test-{uuid4().hex}.myshopify.com")


def multiple() -> dict[str, Any]:
    record = support.product()
    first = record["variants"]["nodes"][0]
    first.update(sku="COPPER-SKU", title="Copper / Small")
    first["selectedOptions"].append({"name": "Size", "value": "Small"})
    second = deepcopy(first)
    second.update(id="gid://shopify/ProductVariant/322", sku="BLUE-SKU", title="Blue / Large")
    second["selectedOptions"] = [
        {"name": "Color", "value": "Blue"},
        {"name": "Size", "value": "Large"},
    ]
    record["variants"]["nodes"].append(second)
    record["media"]["nodes"].append(
        {
            "id": "gid://shopify/MediaImage/457",
            "alt": "Blue product",
            "mediaContentType": "IMAGE",
        }
    )
    return record


def initialize(client: Any, settings: Any, record: dict[str, Any]) -> str:
    tenant = support.register(client)["active_tenant_id"]
    support.install_provider(
        client,
        settings,
        [{"data": {"products": {"nodes": [record], "pageInfo": {"hasNextPage": False}}}}],
    )
    support.connect(client, settings)
    response = client.post("/api/shopify/sync", json={})
    assert response.status_code == 200, response.text
    return str(tenant)


def context(client: Any, **filters: Any) -> dict[str, Any]:
    response = client.post(
        "/api/context", json={"query": "fixture catalog SKU Color", "method": "keyword", **filters}
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    return {
        "selected_product_ids": payload["context"]["eligible_products"],
        "passages": payload["context"]["selected"],
    }


def test_sync_variants_exact_context_and_normal_draft(settings: Any) -> None:
    config = support.configured(settings)
    with support.browser(config) as client:
        tenant = initialize(client, config, multiple())
        products = {p["id"]: p for p in client.get("/api/products").json()["products"]}
        assert set(products) == {
            "shopify_123",
            "shopify_variant_321",
            "shopify_variant_322",
        }
        assert products["shopify_variant_321"]["sku"] == "COPPER-SKU"
        assert products["shopify_variant_321"]["color"] == "Copper"
        assert products["shopify_variant_322"]["color"] == "Blue"
        copper = context(client, product_id="shopify_123", sku="COPPER-SKU", color="Copper")
        assert copper["selected_product_ids"] == ["shopify_variant_321"], copper
        assert copper["passages"] and all(
            p["product_id"] == "shopify_variant_321" for p in copper["passages"]
        )
        assert "BLUE-SKU" not in str(copper) and "Large" not in str(copper)
        named = context(client, product_id="shopify_123", query="COPPER-SKU color")
        assert named["selected_product_ids"] == ["shopify_variant_321"], named
        assert named["passages"] and "BLUE-SKU" not in str(named)
        answer = client.post("/api/answers", json={"query": "COPPER-SKU color", "product_id": "shopify_123"})
        assert answer.status_code == 200, answer.text
        assert not answer.json()["abstained"] and all(
            citation["product_id"] == "shopify_variant_321" for citation in answer.json()["citations"]
        ), answer.text
        seen: list[str] = []

        class RecordingModel:
            def embed(self, texts: list[str], **_: Any) -> Any:
                seen.extend(texts)
                return iter(np.array([1.0, 0.0], dtype=np.float32) for _ in texts)

            def query_embed(self, query: str) -> Any:
                return iter([np.array([1.0, 0.0], dtype=np.float32)])

        client.app.state.engine.model = RecordingModel()
        dense = client.post(
            "/api/context", json={"query": "COPPER-SKU color", "product_id": "shopify_123", "method": "dense"}
        )
        assert dense.status_code == 200, dense.text
        assert dense.json()["context"]["eligible_products"] == ["shopify_variant_321"]
        assert seen and all("BLUE-SKU" not in text and "Large" not in text for text in seen), seen
        client.app.state.engine.model = None
        mismatch = context(client, product_id="shopify_123", sku="COPPER-SKU", color="Blue")
        assert not mismatch["selected_product_ids"] and not mismatch["passages"]
        parent = context(client, product_id="shopify_123")
        assert parent["selected_product_ids"] == ["shopify_123"]
        with transaction(config, tenant) as db:
            draft = create_draft(db, tenant, "shopify_123", config)
        saved = next(d for d in client.get("/api/drafts").json()["drafts"] if d["id"] == draft["draft_id"])
        assert saved["status"] != "blocked" and saved["citations"], saved
        intelligence = client.get("/api/intelligence/shopify_variant_321").json()
        assert "price" not in str(intelligence.get("json_ld", {}).get("document", {}))
        assert "availability" not in str(intelligence.get("json_ld", {}).get("document", {}))


def test_rest_options_retire_removed_variants_and_ignore_stale_updates(
    settings: Any,
) -> None:
    config = support.configured(settings)
    with support.browser(config) as client:
        tenant = initialize(client, config, multiple())
        event = datetime.now(UTC) + timedelta(seconds=1)
        record = {
            "id": 123,
            "title": "Test product",
            "body_html": "Updated fixture",
            "updated_at": event.isoformat(),
            "options": [
                {"name": "Size", "position": 1},
                {"name": "Color", "position": 2},
            ],
            "variants": [
                {
                    "id": 321,
                    "sku": "COPPER-SKU",
                    "title": "Blue title must not infer color",
                    "option1": "Small",
                    "option2": "Copper",
                }
            ],
            "images": [{"id": 457, "alt": "Blue image must not infer color"}],
        }
        response = support.webhook(client, "products/update", record)
        assert response.status_code == 200 and response.json()["applied"], response.text
        products = {p["id"]: p for p in client.get("/api/products").json()["products"]}
        assert set(products) == {"shopify_123", "shopify_variant_321"}
        assert products["shopify_variant_321"]["color"] == "Copper"
        assert not context(client, product_id="shopify_123", sku="BLUE-SKU")["passages"]
        older = support.webhook(
            client, "products/update", multiple(), at=event - timedelta(seconds=1)
        )
        assert older.status_code == 200 and not older.json()["applied"], older.text
        assert not context(client, product_id="shopify_variant_322")["passages"]
        deletion = support.webhook(client, "products/delete", {"id": 123}, at=event + timedelta(seconds=1))
        assert deletion.status_code == 200 and deletion.json()["applied"], deletion.text
        assert client.get("/api/products").json()["products"] == []
        with transaction(config, tenant) as db:
            assert (
                db.execute(
                    "SELECT count(*) AS n FROM product_tombstones WHERE tenant_id=%s",
                    (tenant,),
                ).fetchone()["n"]
                == 3
            )
        assert not context(client, product_id="shopify_123", sku="COPPER-SKU")["passages"]


def test_cross_parent_collision_and_malformed_options_fail_atomically(
    settings: Any,
) -> None:
    config = support.configured(settings)
    with support.browser(config) as client:
        initialize(client, config, multiple())
        stolen = multiple()
        stolen.update(
            id="gid://shopify/Product/124",
            title="Other product",
            updated_at=datetime.now(UTC).isoformat(),
        )
        response = support.webhook(client, "products/update", stolen)
        assert response.status_code == 409, response.text
        malformed = multiple()
        malformed["variants"]["nodes"][0]["selectedOptions"].append({"name": "COLOR", "value": "Blue"})
        response = support.webhook(client, "products/update", malformed)
        assert response.status_code == 422, response.text
        products = {p["id"]: p for p in client.get("/api/products").json()["products"]}
        assert "shopify_124" not in products and products["shopify_variant_321"]["color"] == "Copper"
        response = support.webhook(client, "app/uninstalled", {"id": 42})
        assert response.status_code == 200, response.text
        assert client.get("/api/products").json()["products"] == []
