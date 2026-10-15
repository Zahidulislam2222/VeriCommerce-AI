"""The only environment/configuration boundary for the evidence core."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VC_", extra="ignore", case_sensitive=False)

    settings_file: str | None = None
    database_url: SecretStr
    migration_database_url: SecretStr | None = None
    allowed_origins: list[str] = Field(default_factory=list)
    cookie_name: str = "vc_demo"
    cookie_secure: bool = True
    session_ttl_seconds: int = Field(default=43200, ge=60, le=604800)
    max_active_sessions: int = Field(default=100, ge=1, le=1000)
    max_body_bytes: int = Field(default=262144, ge=1024, le=1048576)
    requests_per_minute: int = Field(default=120, ge=10, le=1000)
    session_creations_per_hour: int = Field(default=20, ge=1, le=100)
    max_products: int = Field(default=50, ge=3, le=500)
    max_sources: int = Field(default=100, ge=6, le=1000)
    max_passages: int = Field(default=500, ge=7, le=5000)
    max_revisions_per_source: int = Field(default=20, ge=1, le=100)
    max_drafts: int = Field(default=100, ge=1, le=1000)
    max_jobs: int = Field(default=200, ge=1, le=1000)
    max_audit_events: int = Field(default=1000, ge=10, le=10000)
    max_evaluations: int = Field(default=20, ge=1, le=100)
    search_limit: int = Field(default=5, ge=1, le=20)
    max_search_limit: int = Field(default=10, ge=1, le=20)
    lexical_min_score: float = Field(default=0.01, ge=0, le=1)
    rrf_constant: int = Field(default=60, ge=1, le=100)
    dense_min_similarity: float = Field(default=0.35, ge=-1, le=1)
    db_connect_timeout_seconds: int = Field(default=5, ge=1, le=30)
    db_statement_timeout_ms: int = Field(default=10000, ge=100, le=60000)
    worker_poll_seconds: float = Field(default=1.0, ge=0.1, le=30)
    worker_lease_seconds: int = Field(default=120, ge=10, le=600)
    worker_max_attempts: int = Field(default=3, ge=1, le=5)
    worker_retry_seconds: int = Field(default=3, ge=1, le=60)
    worker_tenant_batch: int = Field(default=100, ge=1, le=1000)
    worker_heartbeat_path: Path = Path(".cache/worker.ready")
    worker_heartbeat_timeout_seconds: int = Field(default=30, ge=10, le=120)
    embedding_enabled: bool = False
    embedding_download_allowed: bool = False
    embedding_model: str | None = None
    embedding_repository: str | None = None
    embedding_revision: str | None = None
    embedding_model_file: str | None = None
    embedding_cache_dir: Path = Path(".cache/models")
    embedding_threads: int = Field(default=1, ge=1, le=4)
    embedding_batch_size: int = Field(default=16, ge=1, le=64)
    seed_path: Path = Path(__file__).resolve().parents[1] / "data" / "demo.json"
    policy_path: Path = Path(__file__).resolve().parents[1] / "data" / "policy.json"
    evaluation_path: Path = Path(__file__).resolve().parents[1] / "data" / "heldout.json"
    migrations_path: Path = Path(__file__).resolve().parents[1] / "migrations"
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8081, ge=1024, le=65535)
    api_version: str = Field(default="0.2.0", pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")

    @model_validator(mode="after")
    def validate_configuration(self) -> Settings:
        if self.embedding_enabled:
            fields = (
                self.embedding_model,
                self.embedding_repository,
                self.embedding_revision,
                self.embedding_model_file,
            )
            if not all(fields):
                raise ValueError("Enabled embeddings require configured model/repository/revision/file")
            if len(self.embedding_revision or "") != 40:
                raise ValueError("Embedding revision must be a full immutable commit hash")
        if self.search_limit > self.max_search_limit:
            raise ValueError("Default search limit exceeds configured maximum")
        if self.worker_tenant_batch < self.max_active_sessions:
            raise ValueError("Worker tenant batch must cover all allowed active sessions")
        return self


@lru_cache
def get_settings() -> Settings:
    options: dict[str, Any] = {"_env_file": os.environ.get("VC_SETTINGS_FILE") or None}
    return Settings(**options)
