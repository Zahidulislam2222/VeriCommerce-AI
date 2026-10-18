"""Bounded, redirect-free Shopify reads and encrypted offline credentials."""

from __future__ import annotations

import json
import re
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict

from .database import Connection
from .settings import Settings
from .shopify_protocol import GRAPHQL_PATH, OAUTH_EXCHANGE_PATH, SHOP_PATTERN


class Queries(BaseModel):
    model_config = ConfigDict(extra="forbid")
    identity: str
    products: str


class ShopifyClient:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        self.settings = settings
        self.transport = transport
        self.deadline = time.monotonic() + settings.shopify_operation_timeout_seconds
        self.queries = Queries.model_validate_json(settings.shopify_query_path.read_text())
        for query in (self.queries.identity, self.queries.products):
            if not query.lstrip().startswith("query ") or "mutation" in query.lower():
                raise ValueError("Connector query data must contain read-only queries")

    def remaining(self) -> float:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise HTTPException(504, "Shopify operation exceeded its total time budget")
        return remaining

    def request(
        self, shop: str, path: str, payload: dict[str, Any], token: str | None = None, versioned: bool = False
    ) -> dict[str, Any]:
        if not re.fullmatch(SHOP_PATTERN, shop):
            raise HTTPException(422, "Use the store's exact myshopify.com domain")
        headers = {"Accept": "application/json"}
        if token:
            headers["X-Shopify-Access-Token"] = token
        url = self.settings.shopify_origin_template.format(shop=shop) + path
        with httpx.Client(
            timeout=self.settings.shopify_timeout_seconds,
            follow_redirects=False,
            trust_env=False,
            transport=self.transport,
        ) as client:
            for attempt in range(self.settings.shopify_max_retries + 1):
                try:
                    with client.stream(
                        "POST",
                        url,
                        json=payload,
                        headers=headers,
                        timeout=min(self.settings.shopify_timeout_seconds, self.remaining()),
                    ) as response:
                        raw = bytearray()
                        for chunk in response.iter_bytes():
                            self.remaining()
                            raw.extend(chunk)
                            if len(raw) > self.settings.shopify_max_response_bytes:
                                raise HTTPException(502, "Shopify response exceeds configured limit")
                        status = response.status_code
                        retry_after = response.headers.get("Retry-After", "")
                        version = response.headers.get("X-Shopify-API-Version")
                except httpx.TimeoutException:
                    raise HTTPException(504, "Shopify request timed out; retry the bounded sync") from None
                except httpx.HTTPError:
                    raise HTTPException(502, "Shopify transport failed") from None
                if status in {401, 403} or (status == 400 and path == OAUTH_EXCHANGE_PATH):
                    raise HTTPException(409, "Shopify credentials require reconnect")
                if status != 429 and status != 200:
                    raise HTTPException(502, "Shopify returned an unsupported response")
                if versioned and status == 200 and version != self.settings.shopify_api_version:
                    raise HTTPException(502, "Shopify API version differs from configured revision")
                try:
                    result = json.loads(raw) if status == 200 else {}
                except (ValueError, UnicodeDecodeError, RecursionError):
                    raise HTTPException(502, "Shopify returned invalid JSON") from None
                if not isinstance(result, dict):
                    raise HTTPException(502, "Shopify response must be an object")
                errors = result.get("errors", [])
                throttled = status == 429 or (
                    isinstance(errors, list)
                    and any(
                        isinstance(e, dict)
                        and isinstance(e.get("extensions"), dict)
                        and e["extensions"].get("code") == "THROTTLED"
                        for e in errors
                    )
                )
                if not throttled:
                    if errors:
                        raise HTTPException(502, "Shopify query failed; no data was imported")
                    return result
                if attempt >= self.settings.shopify_max_retries:
                    raise HTTPException(503, "Shopify throttle retry budget exhausted")
                delay = self.settings.shopify_retry_seconds * (2**attempt)
                try:
                    delay = max(delay, float(retry_after)) if retry_after else delay
                except ValueError:
                    pass
                time.sleep(min(delay, self.settings.shopify_max_retry_seconds, self.remaining()))
        raise HTTPException(502, "Shopify request failed")

    def exchange(self, shop: str, code: str | None = None, refresh: str | None = None) -> dict[str, Any]:
        secret = self.settings.shopify_client_secret
        payload: dict[str, Any] = {
            "client_id": self.settings.shopify_client_id,
            "client_secret": secret.get_secret_value() if secret else "",
        }
        if refresh:
            payload.update({"grant_type": "refresh_token", "refresh_token": refresh})
        else:
            payload.update({"code": code, "expiring": 1})
        result = self.request(shop, OAUTH_EXCHANGE_PATH, payload)
        if (
            not isinstance(result.get("access_token"), str)
            or not result["access_token"]
            or len(result["access_token"]) > self.settings.shopify_max_response_bytes
        ):
            raise HTTPException(502, "Shopify did not return usable credentials")
        if set(str(result.get("scope", "")).split(",")) != set(self.settings.shopify_scopes):
            raise HTTPException(403, "Shopify granted unexpected scopes")
        if result.get("refresh_token") is not None and not isinstance(result["refresh_token"], str):
            raise HTTPException(502, "Shopify returned an invalid refresh credential")
        now = datetime.now(UTC)
        for key in ("expires_in", "refresh_token_expires_in"):
            if key in result and (type(result[key]) is not int or result[key] <= 0):
                raise HTTPException(502, "Shopify returned an invalid token expiry")
        try:
            expiry = (
                (now + timedelta(seconds=result["expires_in"])).isoformat()
                if result.get("expires_in")
                else None
            )
            refresh_expiry = (
                (now + timedelta(seconds=result["refresh_token_expires_in"])).isoformat()
                if result.get("refresh_token_expires_in")
                else None
            )
        except (OverflowError, ValueError):
            raise HTTPException(502, "Shopify token expiry exceeds the supported timestamp range") from None
        return {
            "access_token": result["access_token"],
            "refresh_token": result.get("refresh_token"),
            "expires_at": expiry,
            "refresh_expires_at": refresh_expiry,
        }

    def graphql(
        self, shop: str, token: str, name: str, variables: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        query = self.queries.identity if name == "identity" else self.queries.products
        result = self.request(
            shop,
            GRAPHQL_PATH.format(version=self.settings.shopify_api_version),
            {"query": query, "variables": variables or {}},
            token,
            versioned=True,
        )
        if not isinstance(result.get("data"), dict):
            raise HTTPException(502, "Shopify query returned no data")
        return dict(result["data"])


def cipher(settings: Settings) -> Fernet:
    key = settings.shopify_encryption_key
    if key is None:
        raise HTTPException(503, "Shopify encryption is not configured")
    return Fernet(key.get_secret_value().encode())


def encrypted(settings: Settings, tenant: str, shop: str, tokens: dict[str, Any]) -> str:
    return (
        cipher(settings)
        .encrypt(json.dumps({"tenant_id": tenant, "shop": shop, "tokens": tokens}).encode())
        .decode()
    )


def access_token(db: Connection, row: dict[str, Any], settings: Settings, client: ShopifyClient) -> str:
    """Caller holds the tenant lock and connection row lock during token rotation."""
    try:
        saved = json.loads(cipher(settings).decrypt(row["encrypted_tokens"].encode()))
        if saved["tenant_id"] != str(row["tenant_id"]) or saved["shop"] != row["shop"]:
            raise ValueError("Credential binding mismatch")
        tokens = saved["tokens"]
        expiry = datetime.fromisoformat(tokens["expires_at"]) if tokens.get("expires_at") else None
        if expiry and expiry <= datetime.now(UTC) + timedelta(
            seconds=settings.shopify_refresh_margin_seconds
        ):
            refresh = tokens.get("refresh_token")
            refresh_expiry = (
                datetime.fromisoformat(tokens["refresh_expires_at"])
                if tokens.get("refresh_expires_at")
                else None
            )
            if not refresh or (refresh_expiry and refresh_expiry <= datetime.now(UTC)):
                raise ValueError("Reconnect required")
            tokens = client.exchange(row["shop"], refresh=refresh)
            db.execute(
                "UPDATE shopify_connections SET encrypted_tokens=%s,token_expires_at=%s,"
                "updated_at=now() WHERE tenant_id=%s",
                (
                    encrypted(settings, str(row["tenant_id"]), row["shop"], tokens),
                    tokens["expires_at"],
                    row["tenant_id"],
                ),
            )
        return str(tokens["access_token"])
    except (InvalidToken, KeyError, ValueError, TypeError):
        raise HTTPException(409, "Shopify credentials require reconnect") from None
