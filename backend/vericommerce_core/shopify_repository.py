"""Provider-owned evidence mapping, ordered tombstones and local connector controls."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from . import repository
from .database import Connection
from .models import CatalogInput
from .settings import Settings
from .shopify_protocol import PRODUCT_GID_PREFIX, VARIANT_GID_PREFIX


class PlainText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.hidden += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def product_number(value: Any) -> str:
    text = str(value)
    if text.startswith(PRODUCT_GID_PREFIX):
        text = text.removeprefix(PRODUCT_GID_PREFIX)
    if not re.fullmatch(r"[0-9]{1,30}", text):
        raise HTTPException(422, "Shopify product identity is invalid")
    return text


def timestamp(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(422, "Shopify event timestamp is invalid") from None
    if parsed.tzinfo is None:
        raise HTTPException(422, "Shopify event timestamp requires a timezone")
    return parsed.astimezone(UTC)


def variant_number(value: Any) -> str:
    text = str(value).removeprefix(VARIANT_GID_PREFIX)
    if not re.fullmatch(r"[0-9]{1,30}", text):
        raise HTTPException(422, "Shopify variant identity is invalid")
    return text


def variant_options(item: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, str]]:
    """Names come from provider options, never from variant titles or media."""
    selected = item.get("selectedOptions")
    if selected is None:
        options = payload.get("options", [])
        if not isinstance(options, list) or len(options) > 3:
            raise HTTPException(422, "Shopify product options are invalid")
        selected = []
        positions: set[int] = set()
        for option in options:
            if not isinstance(option, dict):
                raise HTTPException(422, "Shopify product option is invalid")
            position = option.get("position")
            if type(position) is not int or position not in {1, 2, 3} or position in positions:
                raise HTTPException(422, "Shopify option position is invalid")
            positions.add(position)
            value = item.get(f"option{position}")
            if value is not None:
                selected.append({"name": option.get("name"), "value": value})
    if not isinstance(selected, list) or len(selected) > 3:
        raise HTTPException(422, "Shopify selected options exceed supported bounds")
    names: set[str] = set()
    result = []
    for option in selected:
        if not isinstance(option, dict):
            raise HTTPException(422, "Shopify selected option is invalid")
        name, value = option.get("name"), option.get("value")
        if (
            not isinstance(name, str)
            or not name.strip()
            or len(name) > 100
            or not isinstance(value, str)
            or not value.strip()
            or len(value) > 100
            or name.strip().casefold() in names
        ):
            raise HTTPException(422, "Shopify selected option is invalid")
        names.add(name.strip().casefold())
        result.append({"name": name.strip(), "value": value.strip()})
    return result


def normalized(payload: dict[str, Any]) -> dict[str, Any]:
    title = payload.get("title")
    if not isinstance(title, str) or not title.strip() or len(title) > 200:
        raise HTTPException(422, "Shopify product title exceeds supported bounds")
    description = payload.get("description")
    if description is None:
        html = payload.get("body_html") or ""
        if not isinstance(html, str):
            raise HTTPException(422, "Shopify description is invalid")
        parser = PlainText()
        parser.feed(html)
        description = " ".join(parser.parts)
    if not isinstance(description, str) or len(description) > 4000:
        raise HTTPException(422, "Shopify product description exceeds supported bounds")
    variants = payload.get("variants") or []
    media = payload.get("media", payload.get("images", [])) or []
    if isinstance(variants, dict):
        if variants.get("pageInfo", {}).get("hasNextPage"):
            raise HTTPException(422, "Product variant page exceeds configured query bounds")
        variants = variants.get("nodes", [])
    if isinstance(media, dict):
        if media.get("pageInfo", {}).get("hasNextPage"):
            raise HTTPException(422, "Product media page exceeds configured query bounds")
        media = media.get("nodes", [])
    if not isinstance(variants, list) or not isinstance(media, list) or len(variants) + len(media) > 48:
        raise HTTPException(422, "Shopify variants/media exceed evidence bounds")
    # Keep identifiers, SKU/options and media observations; never infer image facts.
    mapped_variants = []
    identities: set[str] = set()
    for item in variants:
        if not isinstance(item, dict):
            raise HTTPException(422, "Shopify variant must be an object")
        identity = variant_number(item.get("id"))
        if identity in identities:
            raise HTTPException(422, "Shopify variant identity is duplicated")
        identities.add(identity)
        sku = item.get("sku") if item.get("sku") is not None else ""
        variant_title = item.get("title") if item.get("title") is not None else ""
        if (
            not isinstance(sku, str)
            or len(sku) > 100
            or not isinstance(variant_title, str)
            or len(variant_title) > 200
        ):
            raise HTTPException(422, "Shopify variant fields exceed supported bounds")
        selected = variant_options(item, payload)
        color = next((option["value"] for option in selected if option["name"].casefold() == "color"), "")
        if len(color) > 40:
            raise HTTPException(422, "Shopify color exceeds supported bounds")
        mapped_variants.append(
            {"id": identity, "sku": sku, "title": variant_title, "selectedOptions": selected, "color": color}
        )
    mapped_media = []
    for item in media:
        if not isinstance(item, dict):
            raise HTTPException(422, "Shopify media must be an object")
        mapped_media.append(
            {key: item.get(key) for key in ("id", "alt", "mediaContentType") if item.get(key) is not None}
        )
    return {
        "id": product_number(payload.get("id")),
        "title": title.strip(),
        "description": description,
        "product_type": str(payload.get("productType", payload.get("product_type", "")))[:100],
        "variants": mapped_variants,
        "media": mapped_media,
    }


def source_id(number: str) -> str:
    return "shopify_catalog_" + number


def apply_record(
    db: Connection,
    tenant: str,
    payload: dict[str, Any],
    event_at: datetime,
    deleted: bool,
    settings: Settings,
) -> bool:
    number = product_number(payload.get("id"))
    current = db.execute(
        "SELECT event_at,payload FROM shopify_records WHERE tenant_id=%s AND product_id=%s", (tenant, number)
    ).fetchone()
    if current and current["event_at"] >= event_at:
        return False
    product_id = "shopify_" + number
    if (
        not current
        and db.execute("SELECT 1 FROM products WHERE tenant_id=%s AND id=%s", (tenant, product_id)).fetchone()
        and not db.execute(
            "SELECT 1 FROM sources WHERE tenant_id=%s AND id=%s", (tenant, source_id(number))
        ).fetchone()
    ):
        raise HTTPException(409, "A merchant product occupies the connector-owned identity")
    prior_children = set((current or {}).get("payload", {}).get("variant_product_ids", []))
    # Existing pre-variant imports have no cached child list. Stored association is
    # authoritative for lifecycle cleanup and also catches interrupted upgrades.
    prior_children.update(
        row["id"]
        for row in db.execute(
            "SELECT id FROM products WHERE tenant_id=%s AND fields->>'parent_product_id'=%s",
            (tenant, product_id),
        ).fetchall()
    )
    mapped = {} if deleted else normalized(payload)
    children = {"shopify_variant_" + variant["id"] for variant in mapped.get("variants", [])}
    from .phase_repository import retire_product

    for identity in children:
        existing = db.execute(
            "SELECT fields FROM products WHERE tenant_id=%s AND id=%s", (tenant, identity)
        ).fetchone()
        if existing and existing["fields"].get("parent_product_id") != product_id:
            raise HTTPException(409, "Shopify variant identity belongs to another product")
    for identity in prior_children - children:
        retire_product(db, tenant, identity, settings)
    if deleted:
        from .phase_repository import delete_source

        if db.execute(
            "SELECT 1 FROM sources WHERE tenant_id=%s AND id=%s", (tenant, source_id(number))
        ).fetchone():
            delete_source(db, tenant, source_id(number), settings)
        retire_product(db, tenant, product_id, settings)
        mapped["variant_product_ids"] = sorted(prior_children)
    else:
        claims: list[dict[str, str]] = [
            {"label": "Catalog title", "value": mapped["title"], "passage": mapped["title"]}
        ]
        if mapped["description"].strip():
            claims.append(
                {"label": "Catalog description", "value": mapped["title"], "passage": mapped["description"]}
            )
        for label, key in (("Catalog variant", "variants"), ("Unverified media metadata", "media")):
            for item in mapped[key]:
                passage = json.dumps(item, sort_keys=True, ensure_ascii=False)
                if len(passage) > 4000:
                    raise HTTPException(422, "Shopify metadata exceeds passage bounds")
                claims.append(
                    {
                        "label": label,
                        "value": str(item.get("sku") or item.get("id") or label)[:500],
                        "passage": passage,
                    }
                )
        source = source_id(number)
        products = [
            {
                "id": product_id,
                "name": mapped["title"],
                "category": mapped["product_type"],
                "description": mapped["description"],
                "claims": [
                    {**claim, "sourceId": source, "page": str(index + 1)}
                    for index, claim in enumerate(claims)
                ],
            }
        ]
        for variant in mapped["variants"]:
            variant_claims = [
                claim for claim in claims if claim["label"] in {"Catalog title", "Catalog description"}
            ]
            for label, value in (("SKU", variant["sku"]), ("Color", variant["color"])):
                if value:
                    variant_claims.append({"label": label, "value": value, "passage": f"{label}: {value}"})
            for option in variant["selectedOptions"]:
                if option["name"].casefold() != "color":
                    variant_claims.append(
                        {
                            "label": "Catalog option " + option["name"],
                            "value": option["value"],
                            "passage": option["name"] + ": " + option["value"],
                        }
                    )
            products.append(
                {
                    "id": "shopify_variant_" + variant["id"],
                    "parent_product_id": product_id,
                    "name": mapped["title"],
                    "subtitle": variant["title"],
                    "category": mapped["product_type"],
                    "description": mapped["description"],
                    "sku": variant["sku"],
                    "color": variant["color"],
                    "claims": [
                        {**claim, "sourceId": source, "page": str(index + 1)}
                        for index, claim in enumerate(variant_claims)
                    ],
                }
            )
        mapped["variant_product_ids"] = sorted(children)
        catalog = CatalogInput.model_validate(
            {
                "products": products,
                "sources": [
                    {
                        "id": source,
                        "name": mapped["title"],
                        "type": "Shopify read-only catalog",
                        "version": event_at.isoformat(),
                        "date": event_at.date().isoformat(),
                    }
                ],
            }
        )
        try:
            repository.ingest(db, tenant, catalog, settings)
        except ValueError:
            raise HTTPException(422, "Shopify catalog exceeds workspace evidence quotas") from None
    db.execute(
        "INSERT INTO shopify_records(tenant_id,product_id,payload,event_at,deleted) "
        "VALUES(%s,%s,%s,%s,%s) ON CONFLICT(tenant_id,product_id) DO UPDATE "
        "SET payload=EXCLUDED.payload,event_at=EXCLUDED.event_at,deleted=EXCLUDED.deleted",
        (tenant, number, Jsonb(mapped), event_at, deleted),
    )
    repository.audit(
        db, tenant, "shopify.product_deleted" if deleted else "shopify.product_imported", product_id, settings
    )
    return True


def retire_imported(db: Connection, tenant: str, settings: Settings) -> None:
    from .phase_repository import delete_source, retire_product

    rows = db.execute("SELECT product_id FROM shopify_records WHERE tenant_id=%s", (tenant,)).fetchall()
    for row in rows:
        parent = "shopify_" + row["product_id"]
        for product in db.execute(
            "SELECT id FROM products WHERE tenant_id=%s AND (id=%s OR fields->>'parent_product_id'=%s)",
            (tenant, parent, parent),
        ).fetchall():
            retire_product(db, tenant, product["id"], settings)
        if db.execute(
            "SELECT 1 FROM sources WHERE tenant_id=%s AND id=%s", (tenant, source_id(row["product_id"]))
        ).fetchone():
            delete_source(db, tenant, source_id(row["product_id"]), settings)
    db.execute("DELETE FROM shopify_records WHERE tenant_id=%s", (tenant,))
    db.execute(
        "UPDATE shopify_connections SET encrypted_tokens=NULL,token_expires_at=NULL,"
        "status='disconnected',updated_at=now() WHERE tenant_id=%s",
        (tenant,),
    )
    db.execute("UPDATE shopify_bindings SET status='disconnected' WHERE tenant_id=%s", (tenant,))
    db.execute("DELETE FROM shopify_oauth_states WHERE tenant_id=%s", (tenant,))
