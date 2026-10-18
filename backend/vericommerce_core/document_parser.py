"""Disposable resource-limited parser; documents never execute code or fetch URLs."""

from __future__ import annotations

import base64
import csv
import io
import json
import resource
import warnings
from typing import Any


def parse_document(payload: dict[str, Any]) -> dict[str, Any]:
    resource.setrlimit(resource.RLIMIT_AS, (payload["memory_bytes"], payload["memory_bytes"]))
    resource.setrlimit(resource.RLIMIT_CPU, (payload["cpu_seconds"], payload["cpu_seconds"]))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    content = base64.b64decode(payload["content_base64"], validate=True)
    media = payload["media_type"]
    if media == "application/json":
        return {"kind": "catalog", "catalog": json.loads(content.decode("utf-8-sig"))}
    if media == "text/csv":
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
        if reader.fieldnames != payload["csv_columns"]:
            raise ValueError("CSV columns do not match the documented schema")
        products: dict[str, Any] = {}
        sources: dict[str, Any] = {}
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("Malformed CSV row")
            if len(products) >= payload["max_products"] and row["product_id"] not in products:
                raise ValueError("CSV product quota exceeded")
            fields = {
                "id": row["product_id"],
                "name": row["name"],
                "sku": row["sku"],
                "category": row["category"],
            }
            product = products.setdefault(row["product_id"], {**fields, "claims": []})
            if any(product[key] != value for key, value in fields.items()):
                raise ValueError("CSV product metadata conflicts")
            source = {
                "id": row["source_id"],
                "name": row["source_name"],
                "version": row["version"],
                "type": "catalog_csv",
                "date": row["date"],
            }
            if row["source_id"] in sources and sources[row["source_id"]] != source:
                raise ValueError("CSV source metadata conflicts")
            sources[row["source_id"]] = source
            if len(sources) > payload["max_sources"] or len(product["claims"]) >= 50:
                raise ValueError("CSV source or claim quota exceeded")
            product["claims"].append(
                {
                    "label": row["label"],
                    "value": row["value"],
                    "sourceId": row["source_id"],
                    "passage": row["passage"],
                    "page": row["page"],
                }
            )
        return {
            "kind": "catalog",
            "catalog": {"products": list(products.values()), "sources": list(sources.values())},
        }
    if media == "application/pdf":
        from pypdf import PdfReader
        from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject

        if not content.startswith(b"%PDF-"):
            raise ValueError("PDF signature mismatch")
        reader_pdf = PdfReader(io.BytesIO(content), strict=True)
        if reader_pdf.is_encrypted or len(reader_pdf.pages) > payload["max_pages"]:
            raise ValueError("Encrypted PDF or page limit exceeded")
        # Inspect resolved PDF names too: raw substring checks miss escaped names.
        forbidden = {
            "/JavaScript",
            "/JS",
            "/Launch",
            "/EmbeddedFile",
            "/OpenAction",
            "/AA",
            "/RichMedia",
            "/SubmitForm",
            "/ImportData",
            "/XFA",
        }
        stack: list[Any] = [reader_pdf.trailer]
        visited: set[tuple[int, int] | int] = set()
        while stack:
            obj = stack.pop()
            identity = (obj.idnum, obj.generation) if isinstance(obj, IndirectObject) else id(obj)
            if identity in visited:
                continue
            visited.add(identity)
            if isinstance(obj, IndirectObject):
                stack.append(obj.get_object())
            elif isinstance(obj, DictionaryObject):
                if forbidden.intersection(str(key) for key in obj):
                    raise ValueError("Active PDF content is not permitted")
                if str(obj.get("/S", "")) in forbidden or str(obj.get("/Type", "")) in forbidden:
                    raise ValueError("Active PDF action is not permitted")
                stack.extend(obj.values())
            elif isinstance(obj, ArrayObject):
                stack.extend(obj)
        pages = []
        total = 0
        for index, page in enumerate(reader_pdf.pages):
            text = (page.extract_text() or "").strip()
            total += len(text)
            if total > payload["max_text_chars"]:
                raise ValueError("Extracted PDF text exceeds configured limit")
            if text:
                pages.append({"page": str(index + 1), "text": text})
        return {"kind": "document", "pages": pages, "needs_ocr": not bool(pages)}
    if media.startswith("image/"):
        from PIL import Image

        Image.MAX_IMAGE_PIXELS = payload["max_pixels"]
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                expected = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}
                if (
                    image.format != expected.get(media)
                    or image.width * image.height > payload["max_pixels"]
                    or getattr(image, "n_frames", 1) != 1
                ):
                    raise ValueError("Static image format or pixel/frame limit exceeded")
                dimensions = {"width": image.width, "height": image.height, "format": image.format}
                image.verify()
        return {"kind": "image", "image": dimensions, "needs_ocr": True}
    raise ValueError("Unsupported media type")
