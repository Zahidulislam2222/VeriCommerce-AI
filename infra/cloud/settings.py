"""One typed, validated boundary for optional cloud adapters and backup tools."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path


@dataclass(frozen=True)
class CloudSettings:
    schema_version: int
    max_archive_bytes: int
    max_expanded_bytes: int
    max_members: int
    max_compression_ratio: int
    max_text_chars: int
    max_documents: int
    max_query_chars: int
    max_results: int
    archive_members: list[str]
    fixture_label: str
    snapshot_file: str
    snapshot_sha256_file: str
    http_host: str
    http_port: int
    http_timeout_seconds: int
    benchmark_health_path: str
    backup_max_bytes: int
    backup_chunk_bytes: int
    backup_keep_count: int

    @classmethod
    def load(cls, path: Path | None = None) -> CloudSettings:
        content = path.read_text() if path else files("infra.cloud").joinpath("config.json").read_text()
        settings = cls(**json.loads(content))
        for key, value in vars(settings).items():
            if key not in {
                "archive_members",
                "fixture_label",
                "snapshot_file",
                "snapshot_sha256_file",
                "http_host",
                "benchmark_health_path",
            }:
                if type(value) is not int or value <= 0:
                    raise ValueError("Cloud resource budgets must be positive integers")
        if settings.archive_members != ["manifest.json", "draft.json"]:
            raise ValueError("Cloud ZIP protocol requires its exact two members")
        if not 1024 <= settings.http_port <= 65535:
            raise ValueError("Cloud adapter port must be unprivileged")
        if settings.http_host != "127.0.0.1":
            raise ValueError("Local adapter listener must remain loopback-only")
        health_path = settings.benchmark_health_path
        if (
            not isinstance(health_path, str)
            or not re.fullmatch(r"/[a-z0-9/_-]+", health_path)
            or health_path.startswith("/_ah/")
            or health_path.endswith("z")
        ):
            raise ValueError("Health path must avoid provider-reserved URL paths")
        if settings.backup_chunk_bytes > settings.backup_max_bytes:
            raise ValueError("Backup chunk exceeds configured archive bound")
        for name in (settings.snapshot_file, settings.snapshot_sha256_file):
            if Path(name).name != name or name in {"", ".", ".."}:
                raise ValueError("Cloud snapshot must be adjacent immutable package data")
        if not settings.fixture_label or len(settings.fixture_label) > settings.max_text_chars:
            raise ValueError("Synthetic label is required")
        return settings
