"""The only environment/configuration boundary for the evidence core."""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .models import CLAIM_PASSAGE_MAX_CHARS


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
    audit_page_size: int = Field(default=50, ge=1, le=1000)
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

    registration_enabled: bool = True
    account_cookie_name: str = "vc_account"
    account_session_ttl_seconds: int = Field(default=43200, ge=60, le=604800)
    account_attempts_per_hour: int = Field(default=20, ge=1, le=1000)
    account_max_tenants: int = Field(default=10, ge=1, le=100)
    account_max_members: int = Field(default=50, ge=1, le=500)
    account_max_accounts: int = Field(default=1000, ge=1, le=10000)
    account_max_sessions: int = Field(default=10, ge=1, le=50)
    password_scrypt_n: int = Field(default=131072, ge=131072, le=262144)
    password_scrypt_r: int = Field(default=8, ge=8, le=8)
    password_scrypt_p: int = Field(default=1, ge=1, le=1)
    password_scrypt_maxmem: int = Field(default=268435456, ge=268435456, le=536870912)
    password_parallelism: int = Field(default=2, ge=1, le=2)
    password_queue_timeout_seconds: float = Field(default=2.0, ge=0.1, le=10)
    upload_max_bytes: int = Field(default=1048576, ge=1024, le=16777216)
    upload_max_storage_bytes: int = Field(default=16777216, ge=1024, le=268435456)
    upload_max_pixels: int = Field(default=12000000, ge=1024, le=64000000)
    upload_max_pages: int = Field(default=40, ge=1, le=100)
    parser_timeout_seconds: int = Field(default=10, ge=1, le=30)
    parser_memory_bytes: int = Field(default=536870912, ge=134217728, le=1073741824)
    parser_max_text_chars: int = Field(default=100000, ge=1024, le=1000000)
    parser_max_result_bytes: int = Field(default=4194304, ge=1024, le=16777216)
    document_chunk_chars: int = Field(
        default=CLAIM_PASSAGE_MAX_CHARS, ge=1, le=CLAIM_PASSAGE_MAX_CHARS
    )
    context_max_chars: int = Field(default=12000, ge=1000, le=50000)
    context_max_passages: int = Field(default=10, ge=1, le=100)
    max_relations: int = Field(default=1000, ge=1, le=10000)
    intelligence_policy_path: Path = Path(__file__).resolve().parents[1] / "data" / "intelligence.json"
    benchmark_path: Path = Path(__file__).resolve().parents[1] / "data" / "benchmark.json"
    benchmark_agent_review_path: Path = (
        Path(__file__).resolve().parents[1] / "data" / "benchmark-agent-review.json"
    )
    shopify_enabled: bool = False
    shopify_client_id: str | None = None
    shopify_client_secret: SecretStr | None = None
    shopify_encryption_key: SecretStr | None = None
    shopify_origin_template: str = "https://{shop}"
    shopify_redirect_uri: str | None = None
    shopify_return_url: str | None = None
    shopify_oauth_cookie_name: str = "vc_shopify_state"
    shopify_api_version: str = "2026-10"
    shopify_scopes: list[str] = Field(default_factory=lambda: ["read_products"])
    shopify_state_ttl_seconds: int = Field(default=600, ge=60, le=1800)
    shopify_callback_max_age_seconds: int = Field(default=600, ge=60, le=1800)
    shopify_clock_skew_seconds: int = Field(default=60, ge=0, le=300)
    shopify_timeout_seconds: float = Field(default=10, ge=1, le=30)
    shopify_operation_timeout_seconds: float = Field(default=30, ge=5, le=120)
    shopify_max_pages: int = Field(default=20, ge=1, le=100)
    shopify_page_size: int = Field(default=25, ge=1, le=100)
    shopify_max_retries: int = Field(default=3, ge=0, le=5)
    shopify_retry_seconds: float = Field(default=1, ge=0, le=10)
    shopify_max_retry_seconds: float = Field(default=5, ge=0, le=30)
    shopify_max_response_bytes: int = Field(default=2097152, ge=1024, le=8388608)
    shopify_webhook_max_bytes: int = Field(default=1048576, ge=1024, le=4194304)
    shopify_webhook_max_age_seconds: int = Field(default=172800, ge=60, le=604800)
    shopify_receipt_retention_days: int = Field(default=30, ge=1, le=90)
    shopify_max_receipts: int = Field(default=10000, ge=100, le=100000)
    shopify_max_syncs: int = Field(default=100, ge=1, le=1000)
    shopify_refresh_margin_seconds: int = Field(default=60, ge=0, le=300)
    shopify_query_path: Path = Path(__file__).resolve().parents[1] / "data" / "shopify_graphql.json"

    @model_validator(mode="after")
    def validate_configuration(self) -> Settings:
        if self.password_scrypt_n & (self.password_scrypt_n - 1):
            raise ValueError("Password scrypt N must be a power of two")
        if self.shopify_enabled:
            if not all(
                (
                    self.shopify_client_id,
                    self.shopify_client_secret,
                    self.shopify_encryption_key,
                    self.shopify_redirect_uri,
                    self.shopify_return_url,
                )
            ):
                raise ValueError("Enabled Shopify requires credentials, encryption and callback/return URLs")
            if self.shopify_scopes != ["read_products"]:
                raise ValueError("This connector permits only read_products")
            if self.shopify_origin_template != "https://{shop}":
                raise ValueError("Shopify transport must use the verified HTTPS shop domain")
            if not re.fullmatch(r"20[0-9]{2}-(01|04|07|10)", self.shopify_api_version):
                raise ValueError("Shopify API version must be a pinned stable quarter")
            for configured in (self.shopify_redirect_uri, self.shopify_return_url):
                parsed = urlsplit(configured or "")
                origin = f"{parsed.scheme}://{parsed.netloc}"
                if (
                    parsed.scheme != "https"
                    or not parsed.hostname
                    or parsed.username
                    or parsed.password
                    or origin not in self.allowed_origins
                ):
                    raise ValueError("Shopify callback/return URLs must use an allowed HTTPS origin")
            if urlsplit(self.shopify_redirect_uri or "").path != "/api/shopify/callback":
                raise ValueError("Shopify callback must use its exact application route")
            from cryptography.fernet import Fernet

            Fernet((self.shopify_encryption_key or SecretStr("")).get_secret_value().encode())
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
