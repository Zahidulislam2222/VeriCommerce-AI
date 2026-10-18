"""IAM-only Lambda payload validator; strict synthetic ZIPs are never extracted."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import re
import stat
import zipfile
import zlib
from typing import Any

from .settings import CloudSettings


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def load_json(content: bytes) -> Any:
    return json.loads(content, object_pairs_hook=unique_object)


def text(value: Any, settings: CloudSettings) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > settings.max_text_chars:
        raise ValueError("Text exceeds the synthetic protocol boundary")
    # This is a narrow synthetic-only protocol, not a general private-data detector.
    if re.search(r"(?i)https?://|[\w.+-]+@[\w.-]+|password|secret|token|api.key|private.key", value) or any(
        ord(char) < 32 and char not in "\n\t" for char in value
    ):
        raise ValueError("Private-looking content is prohibited in cloud fixtures")
    return value


def validate_archive(content: bytes, settings: CloudSettings) -> dict[str, Any]:
    if not content or len(content) > settings.max_archive_bytes:
        raise ValueError("Archive exceeds configured bound")
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        members = archive.infolist()
        if len(members) > settings.max_members or sorted(x.filename for x in members) != sorted(
            settings.archive_members
        ):
            raise ValueError("Archive must contain exactly the protocol members")
        expanded = 0
        for member in members:
            mode = member.external_attr >> 16
            if (
                member.flag_bits & 1
                or member.is_dir()
                or stat.S_ISLNK(mode)
                or member.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
                or member.file_size > settings.max_expanded_bytes
                or member.file_size > max(1, member.compress_size) * settings.max_compression_ratio
            ):
                raise ValueError("Unsafe archive member")
            expanded += member.file_size
        if expanded > settings.max_expanded_bytes:
            raise ValueError("Expanded archive exceeds configured bound")
        manifest = load_json(archive.read("manifest.json"))
        draft_bytes = archive.read("draft.json")
    if (
        not isinstance(manifest, dict)
        or set(manifest) != {"schema_version", "classification", "draft_sha256"}
        or type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != settings.schema_version
        or manifest["classification"] != settings.fixture_label
        or manifest["draft_sha256"] != sha256(draft_bytes)
    ):
        raise ValueError("Manifest schema, classification or content hash mismatch")
    draft = load_json(draft_bytes)
    if not isinstance(draft, dict) or set(draft) != {"product_id", "body", "evidence"}:
        raise ValueError("Unexpected draft schema")
    text(draft["product_id"], settings)
    body = text(draft["body"], settings)
    evidence = draft["evidence"]
    if not isinstance(evidence, list) or not 1 <= len(evidence) <= settings.max_documents:
        raise ValueError("Bounded evidence is required")
    identifiers = set()
    for item in evidence:
        if not isinstance(item, dict) or set(item) != {"source_id", "quote", "sha256"}:
            raise ValueError("Unexpected evidence schema")
        source = text(item["source_id"], settings)
        quote = text(item["quote"], settings)
        if source in identifiers or sha256(quote.encode()) != item["sha256"]:
            raise ValueError("Evidence duplicate or hash mismatch")
        identifiers.add(source)
    if body != "\n".join(item["quote"] for item in evidence):
        raise ValueError("Draft must be exactly its cited quotations in source order")
    return {
        "valid": True,
        "schema_version": settings.schema_version,
        "archive_sha256": sha256(content),
        "evidence_count": len(evidence),
        "classification": settings.fixture_label,
    }


def handler(event: Any, _context: Any) -> dict[str, Any]:
    settings = CloudSettings.load()
    try:
        if not isinstance(event, dict) or set(event) != {"archive_base64"}:
            raise ValueError("Unexpected invocation schema")
        encoded = event["archive_base64"]
        if not isinstance(encoded, str) or len(encoded) > ((settings.max_archive_bytes + 2) // 3) * 4:
            raise ValueError("Encoded archive exceeds configured bound")
        return validate_archive(base64.b64decode(encoded, validate=True), settings)
    except (
        ValueError,
        KeyError,
        TypeError,
        UnicodeError,
        RecursionError,
        zipfile.BadZipFile,
        OSError,
        zlib.error,
        NotImplementedError,
        RuntimeError,
    ):
        return {"valid": False, "error": "invalid_synthetic_archive"}
