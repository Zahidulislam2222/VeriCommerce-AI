"""Reproduce the original fictional, family-split corpus and code-native diagrams."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def generate(spec: dict[str, Any], images: Path) -> dict[str, Any]:
    products = []
    sources = []
    questions = []
    assets = []
    images.mkdir(parents=True, exist_ok=True)
    for family_index, family in enumerate(spec["families"]):
        for index in range(spec["products_per_family"]):
            identity = family["name"].lower() + "-" + str(index + 1)
            name = family["name"] + " " + str(index + 1)
            source_id = identity + "-catalog"
            sku = identity.upper()
            facts = {
                "name": name,
                "sku": sku,
                "battery": str(12 + family_index + index) + " h",
                "weight": str(200 + 10 * family_index + index) + " g",
                "length": str(15 + index) + " cm",
                "price": str(49 + family_index * 5 + index) + ".00",
                "currency": "USD",
                "availability": "InStock",
                "color": spec["colors"][index],
            }
            claims = [
                {
                    "label": label,
                    "value": value,
                    "sourceId": source_id,
                    "passage": name + " " + label + ": " + value + ".",
                    "page": "1",
                }
                for label, value in facts.items()
            ]
            products.append(
                {
                    "id": identity,
                    "name": name,
                    "sku": sku,
                    "color": facts["color"],
                    "category": spec["category"],
                    "claims": claims,
                }
            )
            sources.append(
                {
                    "id": source_id,
                    "name": name + " original fictional catalog",
                    "version": spec["version"],
                    "type": "synthetic_catalog",
                    "date": spec["date"],
                }
            )
            for qindex, template in enumerate(spec["question_templates"]):
                questions.append(
                    {
                        "id": identity + "-q" + str(qindex + 1),
                        "product_id": identity,
                        "split": family["split"],
                        "query": template["query"].format(name=name),
                        "expected_source_id": source_id,
                        "expected_label": template["label"],
                        "expected_abstain": False,
                        "reviewed": False,
                    }
                )
            if index < 2:
                for qindex, template in enumerate(spec["abstention_templates"]):
                    if len([q for q in questions if q["expected_abstain"]]) >= 20:
                        continue
                    questions.append(
                        {
                            "id": identity + "-unsupported" + str(qindex + 1),
                            "product_id": identity,
                            "split": family["split"],
                            "query": template.format(name=name),
                            "expected_source_id": None,
                            "expected_label": None,
                            "expected_abstain": True,
                            "reviewed": False,
                        }
                    )
            for image_index, purpose in enumerate(spec["image_purposes"]):
                image_id = identity + "-image" + str(image_index + 1)
                width, height = spec["image_dimensions"]
                # SVG is source-native geometry, with no external URLs, scripts or inferred facts.
                svg = (
                    '<svg xmlns="http://www.w3.org/2000/svg" width="'
                    + str(width)
                    + '" height="'
                    + str(height)
                    + '" viewBox="0 0 '
                    + str(width)
                    + " "
                    + str(height)
                    + '">'
                    + '<rect width="100%" height="100%" fill="#f2eee6"/>'
                    + '<text x="12" y="20" fill="#30343b" font-size="12">'
                    + name
                    + "</text>"
                    + '<path d="M60 110V85a60 60 0 0 1 120 0v25" fill="none" stroke="'
                    + spec["swatches"][index]
                    + '" stroke-width="16"/>'
                    + '<rect x="45" y="85" width="30" height="55" rx="10" fill="#30343b"/>'
                    + '<rect x="165" y="85" width="30" height="55" rx="10" fill="#30343b"/>'
                    + '<circle cx="120" cy="160" r="'
                    + str(3 + image_index)
                    + '" fill="'
                    + spec["swatches"][index]
                    + '"/></svg>'
                )
                raw = svg.encode()
                (images / (image_id + ".svg")).write_bytes(raw)
                alt = (
                    ""
                    if purpose == "decorative"
                    else (
                        spec["image_function_template"].format(name=name)
                        if purpose == "functional"
                        else "Fictional " + name + " headphone schematic in " + facts["color"]
                    )
                )
                assets.append(
                    {
                        "id": image_id,
                        "product_id": identity,
                        "path": "/benchmark/images/" + image_id + ".svg",
                        "purpose": purpose,
                        "usage_context": spec["image_contexts"][purpose].format(name=name),
                        "function": spec["image_function_template"].format(name=name)
                        if purpose == "functional"
                        else "",
                        "destination": spec["image_destination_prefix"] + identity
                        if purpose == "functional"
                        else "",
                        "expected_alt": alt,
                        "reviewed": False,
                        "sha256": hashlib.sha256(raw).hexdigest(),
                    }
                )
    dataset = {
        "version": spec["version"],
        "license": spec["license"],
        "review_status": "pending",
        "review_notice": spec["review_notice"],
        "catalog": {"products": products, "sources": sources},
        "products": [
            {
                "id": p["id"],
                "name": p["name"],
                "family": p["name"].split()[0],
                "split": next(f["split"] for f in spec["families"] if p["name"].startswith(f["name"] + " ")),
            }
            for p in products
        ],
        "questions": questions,
        "images": assets,
    }
    dataset["hash"] = hashlib.sha256(
        json.dumps(dataset, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return dataset


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--images", required=True, type=Path)
    args = parser.parse_args()
    result = generate(json.loads(args.spec.read_text()), args.images)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "products": len(result["products"]),
                "images": len(result["images"]),
                "questions": len(result["questions"]),
                "dataset_hash": result["hash"],
            }
        )
    )
