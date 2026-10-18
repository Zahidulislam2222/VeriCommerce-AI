"""Deterministic conflict checks and source-backed structured data, without inference."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from .database import Connection
from .repository import citation, current_passages, digest
from .settings import Settings
from .uploads import policy


def normalized_value(value: str, configuration: dict[str, Any]) -> tuple[str, str]:
    text = value.casefold().strip()
    for alias, unit in configuration["unit_aliases"].items():
        text = re.sub(r"\b" + re.escape(alias) + r"\b", unit, text)
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*([a-z]+)", text)
    if match and match[2] in configuration["unit_factors"]:
        dimension, factor = configuration["unit_factors"][match[2]]
        return str(dimension), str((Decimal(match[1]) * Decimal(str(factor))).normalize())
    return "text", " ".join(text.split())


def inspect_claims(passages: list[dict[str, Any]], settings: Settings) -> dict[str, Any]:
    configuration = policy(settings)
    grouped: dict[str, list[dict[str, Any]]] = {}
    blocked = []
    for passage in passages:
        grouped.setdefault(passage["label"].casefold(), []).append(passage)
        text = " ".join(str(passage[key]) for key in ("label", "value", "text")).casefold()
        if any(term.casefold() in text for term in configuration["unsafe_claim_terms"]):
            blocked.append(
                {
                    "passage_id": str(passage["passage_id"]),
                    "reason": "Critical claim requires independent verification",
                }
            )
    contradictions = []
    for label, rows in grouped.items():
        if label in {name.casefold() for name in configuration["non_scalar_labels"]}:
            continue
        values = {normalized_value(row["value"], configuration) for row in rows}
        if len(values) > 1:
            contradictions.append(
                {
                    "label": label,
                    "passage_ids": [str(p["passage_id"]) for p in rows],
                    "values": [p["value"] for p in rows],
                    "reason": "Current sources disagree after unit normalization",
                }
            )
    return {"contradictions": contradictions, "blocked_claims": blocked}


def product_json_ld(
    db: Connection, tenant_id: str, product_id: str, settings: Settings, include_variants: bool = True
) -> dict[str, Any]:
    product = db.execute(
        "SELECT fields FROM products WHERE tenant_id=%s AND id=%s", (tenant_id, product_id)
    ).fetchone()
    passages = current_passages(db, tenant_id, product_id)
    inspection = inspect_claims(passages, settings)
    blocked = ["Conflicting current evidence"] if inspection["contradictions"] else []
    if inspection["blocked_claims"]:
        blocked.append("Critical claims require separate verification")
    by_label: dict[str, list[dict[str, Any]]] = {}
    for passage in passages:
        by_label.setdefault(passage["label"].casefold(), []).append(passage)
    configuration = policy(settings)
    required = ["name", *configuration["offer_labels"]]
    selected: dict[str, dict[str, Any]] = {}
    for label in required:
        rows = by_label.get(label, [])
        if not rows:
            blocked.append("Missing evidence for " + label)
        else:
            selected[label] = rows[0]
            if rows[0]["value"].casefold() not in rows[0]["text"].casefold():
                blocked.append("Value is absent from supporting passage: " + label)
    if product and selected:
        for label in ("name", "sku"):
            if label in selected and product["fields"].get(label) != selected[label]["value"]:
                blocked.append("Visible product metadata differs from evidence: " + label)
    if "price" in selected:
        try:
            price = Decimal(selected["price"]["value"])
            exponent = price.as_tuple().exponent
            if not price.is_finite() or price < 0 or (isinstance(exponent, int) and exponent < -2):
                blocked.append("Price must be a finite nonnegative two-decimal amount")
        except InvalidOperation:
            blocked.append("Invalid authoritative price")
    if "currency" in selected and not re.fullmatch(r"[A-Z]{3}", selected["currency"]["value"]):
        blocked.append("Currency must use an uppercase ISO currency code")
    if (
        "availability" in selected
        and selected["availability"]["value"] not in configuration["schema_availability"]
    ):
        blocked.append("Unsupported authoritative availability")
    if blocked or product is None:
        return {
            "available": False,
            "blocked": blocked or ["Product not found"],
            "document": None,
            "provenance": {},
        }
    document: dict[str, Any] = {
        "@context": configuration["schema_context"],
        "@type": "Product",
        "name": selected["name"]["value"],
        "sku": selected["sku"]["value"],
        "offers": {
            "@type": "Offer",
            "price": selected["price"]["value"],
            "priceCurrency": selected["currency"]["value"],
            "availability": configuration["schema_context"] + "/" + selected["availability"]["value"],
        },
    }
    provenance = {label: citation(p) for label, p in selected.items()}
    if include_variants:
        variants = db.execute(
            "SELECT k.object_id FROM knowledge_relations k JOIN sources s ON s.tenant_id=k.tenant_id "
            "AND s.current_revision_id=k.revision_id WHERE k.tenant_id=%s AND k.subject_id=%s "
            "AND k.predicate='has_variant' AND k.status='approved' AND k.valid_to IS NULL "
            "AND NOT EXISTS (SELECT 1 FROM source_tombstones t WHERE t.tenant_id=s.tenant_id "
            "AND t.source_id=s.id) ORDER BY k.object_id",
            (tenant_id, product_id),
        ).fetchall()
        children = []
        for variant in variants:
            child = product_json_ld(db, tenant_id, variant["object_id"], settings, include_variants=False)
            colors = [
                p
                for p in current_passages(db, tenant_id, variant["object_id"])
                if p["label"].casefold() == "color" and p["value"].casefold() in p["text"].casefold()
            ]
            visible = db.execute(
                "SELECT fields->>'color' AS color FROM products WHERE tenant_id=%s AND id=%s",
                (tenant_id, variant["object_id"]),
            ).fetchone()
            if (
                not child["available"]
                or len({p["value"] for p in colors}) != 1
                or not visible
                or not colors
                or (visible["color"] != colors[0]["value"])
            ):
                return {
                    "available": False,
                    "blocked": ["Variant lacks consistent current offer/color evidence"],
                    "document": None,
                    "provenance": {},
                }
            children.append({**child["document"], "color": colors[0]["value"]})
            provenance.update(
                {
                    "variants." + variant["object_id"] + "." + key: value
                    for key, value in child["provenance"].items()
                }
            )
            provenance["variants." + variant["object_id"] + ".color"] = citation(colors[0])
        if children:
            document = {
                "@context": configuration["schema_context"],
                "@type": "ProductGroup",
                "name": selected["name"]["value"],
                "productGroupID": selected["sku"]["value"],
                "variesBy": [configuration["schema_context"] + "/color"],
                "hasVariant": children,
            }
    return {
        "available": True,
        "blocked": [],
        "document": document,
        "provenance": provenance,
    }


def impact(db: Connection, tenant_id: str, source_id: str, settings: Settings) -> dict[str, Any]:
    revisions = db.execute(
        "SELECT id FROM source_revisions WHERE tenant_id=%s AND source_id=%s", (tenant_id, source_id)
    ).fetchall()
    revision_ids = {str(row["id"]) for row in revisions}
    relations = db.execute(
        "SELECT * FROM knowledge_relations WHERE tenant_id=%s ORDER BY valid_from,id LIMIT %s",
        (tenant_id, settings.max_relations),
    ).fetchall()
    affected_relations = {str(row["id"]) for row in relations if str(row["revision_id"]) in revision_ids}
    affected_products = {row["subject_id"] for row in relations if str(row["id"]) in affected_relations}
    for _ in range(len(relations)):
        added = {row["subject_id"] for row in relations if row["object_id"] in affected_products}
        if added.issubset(affected_products):
            break
        affected_products.update(added)
    drafts = db.execute(
        "SELECT id,product_id,status,citations FROM drafts WHERE tenant_id=%s", (tenant_id,)
    ).fetchall()
    affected = [
        {"id": str(row["id"]), "product_id": row["product_id"], "status": row["status"]}
        for row in drafts
        if row["product_id"] in affected_products
        or any(str(c["revision_id"]) in revision_ids for c in row["citations"])
    ]
    return {
        "source_id": source_id,
        "revision_ids": sorted(revision_ids),
        "relations": sorted(affected_relations),
        "products": sorted(affected_products),
        "drafts": affected,
        "snapshot_hash": digest([sorted(revision_ids), affected]),
    }
