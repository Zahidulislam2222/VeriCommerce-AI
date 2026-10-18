"""Actual HTTP/worker/resource-isolation checks for phase ingestion and deletion."""

from __future__ import annotations

import base64
import copy
import csv
import io
import json
from typing import Any

import pytest
from PIL import Image
from pypdf import PdfWriter


def upload(client: Any, content: bytes, media: str, source: str = "upload-one") -> Any:
    return client.post(
        "/api/uploads",
        json={
            "product_id": "forma-one",
            "source_id": source,
            "filename": "original.dat",
            "media_type": media,
            "version": "1",
            "content_base64": base64.b64encode(content).decode(),
        },
    )


def finish(client: Any, settings: Any, response: Any) -> dict[str, Any]:
    from vericommerce_core.jobs import process_one

    assert response.status_code == 202, response.text
    job_id = response.json()["job"]["id"]
    for _ in range(100):
        job = client.get("/api/jobs/" + job_id).json()["job"]
        if job["status"] in {"succeeded", "failed"}:
            return dict(job)
        process_one(settings)
    raise AssertionError("Worker did not finish bounded job")


def test_real_raster_upload_dedup_view_and_purpose_review(client: Any, settings: Any) -> None:
    image = io.BytesIO()
    Image.new("RGB", (16, 16), color="blue").save(image, format="PNG")
    received = upload(client, image.getvalue(), "image/png")
    job = finish(client, settings, received)
    assert job["status"] == "succeeded", job
    assert job["result"]["status"] == "human_observation_required"
    identity = received.json()["upload_id"]
    duplicate = upload(client, image.getvalue(), "image/png")
    assert duplicate.json()["duplicate"] and duplicate.json()["job"]["id"] == job["id"]
    viewed = client.get("/api/uploads/" + identity + "/content")
    assert viewed.content == image.getvalue() and viewed.headers["x-content-type-options"] == "nosniff"
    invalid = client.post(
        "/api/image-reviews",
        json={"upload_id": identity, "purpose": "decorative", "alt": "bad"},
    )
    assert invalid.status_code == 422
    review = client.post(
        "/api/image-reviews",
        json={"upload_id": identity, "purpose": "decorative", "alt": ""},
    )
    assert review.status_code == 200, review.text
    assert not review.json()["review"]["approved"]
    assert (
        client.post("/api/image-reviews/" + review.json()["review"]["id"] + "/approve", json={}).status_code
        == 401
    )
    assert client.delete("/api/sources/upload-one").json()["deleted"]
    assert client.get("/api/uploads/" + identity + "/content").status_code == 404
    assert upload(client, image.getvalue(), "image/png").status_code == 409


@pytest.mark.parametrize(
    "content,media",
    [
        (b"PK\x03\x04bad", "application/pdf"),
        (b"<html>bad</html>", "image/png"),
        (b"{}", "text/html"),
    ],
)
def test_format_spoofing_and_archives_fail_without_evidence(
    client: Any, settings: Any, content: bytes, media: str
) -> None:
    response = upload(client, content, media)
    if media == "text/html":
        assert response.status_code == 415
    else:
        job = finish(client, settings, response)
        assert job["status"] == "failed"
    assert not any(source["id"] == "upload-one" for source in client.get("/api/sources").json()["sources"])


def test_blank_and_active_pdfs_never_become_invented_text(client: Any, settings: Any) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    content = io.BytesIO()
    writer.write(content)
    job = finish(
        client,
        settings,
        upload(client, content.getvalue(), "application/pdf", "blank-pdf"),
    )
    assert job["status"] == "succeeded" and job["result"]["needs_ocr"]
    writer.add_js("app.alert('untrusted')")
    active = io.BytesIO()
    writer.write(active)
    rejected = finish(
        client,
        settings,
        upload(client, active.getvalue(), "application/pdf", "active-pdf"),
    )
    assert rejected["status"] == "failed"


def test_animated_raster_is_rejected_before_serving_bytes(client: Any, settings: Any) -> None:
    first = Image.new("RGB", (16, 16), color="red")
    second = Image.new("RGB", (16, 16), color="blue")
    content = io.BytesIO()
    first.save(content, format="PNG", save_all=True, append_images=[second], duration=100, loop=0)
    queued = upload(client, content.getvalue(), "image/png", "animated-raster")
    assert finish(client, settings, queued)["status"] == "failed"
    assert client.get("/api/uploads/" + queued.json()["upload_id"] + "/content").status_code == 409


def test_csv_catalog_parses_in_child_and_exact_replay_is_idempotent(client: Any, settings: Any) -> None:
    from vericommerce_core.uploads import policy

    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=policy(settings)["csv_columns"])
    writer.writeheader()
    writer.writerow(
        {
            "product_id": "new-audio",
            "name": "New Audio",
            "sku": "NEW-AUDIO",
            "category": "Audio",
            "source_id": "csv-source",
            "source_name": "Original fictional source",
            "version": "1",
            "date": "2026-10-18",
            "label": "battery",
            "value": "20 h",
            "passage": "New Audio battery: 20 h.",
            "page": "1",
        }
    )
    first = finish(
        client,
        settings,
        upload(client, stream.getvalue().encode(), "text/csv", "csv-upload"),
    )
    assert first["status"] == "succeeded", first
    assert first["result"]["sources_changed"] == 1
    versions = client.get("/api/sources/csv-source/versions").json()["versions"]
    assert len(versions) == 1 and versions[0]["current"]
    duplicate = upload(client, stream.getvalue().encode(), "text/csv", "csv-upload")
    assert duplicate.json()["duplicate"]
    assert len(client.get("/api/sources/csv-source/versions").json()["versions"]) == 1


def test_delete_invalidates_approved_draft_and_fences_queued_reimport(client: Any, settings: Any) -> None:
    from vericommerce_core.jobs import process_one

    catalog = json.loads(settings.seed_path.read_text())
    selected = copy.deepcopy(catalog)
    queued = client.post("/api/ingestions", json=selected)
    assert queued.status_code == 202
    source_id = selected["sources"][0]["id"]
    removed = client.delete("/api/sources/" + source_id)
    assert removed.status_code == 200
    for _ in range(100):
        result = client.get("/api/jobs/" + queued.json()["job"]["id"]).json()["job"]
        if result["status"] in {"failed", "succeeded"}:
            break
        process_one(settings)
    assert result["status"] == "failed"
    assert source_id not in {source["id"] for source in client.get("/api/sources").json()["sources"]}
    assert not any(
        v["current"] for v in client.get("/api/sources/" + source_id + "/versions").json()["versions"]
    )


def test_isolated_image_pixel_budget_and_provider_ownership(client: Any, settings: Any) -> None:
    from vericommerce_core.uploads import isolated_parse

    image = io.BytesIO()
    Image.new("RGB", (64, 64), color="red").save(image, format="PNG")
    with pytest.raises(ValueError):
        isolated_parse(
            image.getvalue(),
            "image/png",
            settings.model_copy(update={"upload_max_pixels": 1024}),
        )
    assert upload(client, image.getvalue(), "image/png", "shopify_catalog_123").status_code == 422
    catalog = json.loads(settings.seed_path.read_text())
    catalog["products"][0]["id"] = "shopify_123"
    job = finish(
        client,
        settings,
        upload(
            client,
            json.dumps(catalog).encode(),
            "application/json",
            "malicious-catalog",
        ),
    )
    assert job["status"] == "failed"
