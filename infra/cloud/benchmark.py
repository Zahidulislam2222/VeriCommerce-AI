"""Immutable synthetic lexical benchmark ASGI adapter behind Cloud Run IAM."""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any

from .settings import CloudSettings
from .validator import load_json, sha256, text


class Benchmark:
    def __init__(self, settings: CloudSettings, directory: Path):
        self.settings = settings
        content = (directory / settings.snapshot_file).read_bytes()
        expected = (directory / settings.snapshot_sha256_file).read_text().strip()
        if len(content) > settings.max_expanded_bytes or sha256(content) != expected:
            raise ValueError("Immutable synthetic snapshot hash mismatch")
        snapshot = load_json(content)
        if (
            not isinstance(snapshot, dict)
            or set(snapshot) != {"classification", "documents"}
            or snapshot["classification"] != settings.fixture_label
            or not isinstance(snapshot["documents"], list)
            or not 1 <= len(snapshot["documents"]) <= settings.max_documents
        ):
            raise ValueError("Unexpected synthetic snapshot schema")
        identities = set()
        for item in snapshot["documents"]:
            if not isinstance(item, dict) or set(item) != {"id", "text"}:
                raise ValueError("Unexpected synthetic document schema")
            text(item["id"], settings)
            text(item["text"], settings)
            if item["id"] in identities:
                raise ValueError("Duplicate synthetic document")
            identities.add(item["id"])
        self.documents = snapshot["documents"]
        self.snapshot_sha256 = expected

    def query(self, request: Any) -> dict[str, Any]:
        if not isinstance(request, dict) or set(request) != {"query", "limit"}:
            raise ValueError("Expected query and limit only")
        query = text(request["query"], self.settings)
        limit = request["limit"]
        if (
            len(query) > self.settings.max_query_chars
            or type(limit) is not int
            or not 1 <= limit <= self.settings.max_results
        ):
            raise ValueError("Query or result limit exceeds configured bound")
        tokens = set(re.findall(r"\w+", query.casefold()))
        scored = []
        for item in self.documents:
            overlap = len(tokens & set(re.findall(r"\w+", item["text"].casefold())))
            if overlap:
                scored.append({"id": item["id"], "score": overlap, "text": item["text"]})
        scored.sort(key=lambda item: (-item["score"], item["id"]))
        return {
            "method": "keyword-overlap",
            "snapshot_sha256": self.snapshot_sha256,
            "classification": self.settings.fixture_label,
            "results": scored[:limit],
            "abstained": not scored,
        }


async def app(scope: dict[str, Any], receive: Any, send: Any) -> None:
    if scope["type"] != "http":
        return
    settings = CloudSettings.load()
    status = 400
    result: dict[str, Any] = {"error": "invalid_synthetic_request"}
    try:
        engine = Benchmark(settings, Path(__file__).parent)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        await send(
            {
                "type": "http.response.start",
                "status": 503,
                "headers": [(b"content-type", b"application/json"), (b"cache-control", b"no-store")],
            }
        )
        await send({"type": "http.response.body", "body": b'{"error":"snapshot_unavailable"}'})
        return
    try:
        headers = dict(scope.get("headers", []))
        if scope["method"] == "GET" and scope["path"] == settings.benchmark_health_path:
            result = {"ready": True, "snapshot_sha256": engine.snapshot_sha256}
            status = 200
        elif scope["method"] == "POST" and scope["path"] == "/benchmark":
            length = int(headers.get(b"content-length", b"-1"))
            if (
                headers.get(b"content-type", b"").split(b";")[0] != b"application/json"
                or not 0 < length <= settings.max_archive_bytes
            ):
                raise ValueError("Bounded JSON body required")
            body = bytearray()
            async with asyncio.timeout(settings.http_timeout_seconds):
                while True:
                    event = await receive()
                    if event["type"] != "http.request":
                        raise ValueError("Request disconnected")
                    body.extend(event.get("body", b""))
                    if len(body) > length:
                        raise ValueError("Body exceeds declared length")
                    if not event.get("more_body"):
                        break
            if len(body) != length:
                raise ValueError("Body length mismatch")
            result = engine.query(load_json(bytes(body)))
            status = 200
        else:
            status = 404
            result = {"error": "route_not_found"}
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError, TimeoutError):
        pass
    except OSError:
        status = 503
        result = {"error": "snapshot_unavailable"}
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"cache-control", b"no-store"),
                (b"x-content-type-options", b"nosniff"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": json.dumps(result).encode()})
