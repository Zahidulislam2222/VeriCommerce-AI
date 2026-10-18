"""Owner-authorized standalone OAuth and replay-safe read-only catalog imports."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode
from uuid import UUID, uuid4

import psycopg
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from . import account_repository as accounts
from . import repository
from .database import tenant_lock, transaction
from .models import EmptyBody
from .settings import Settings
from .shopify_client import ShopifyClient, access_token, encrypted
from .shopify_protocol import AUTHORIZE_PATH, SHOP_PATTERN, SUPPORTED_TOPICS
from .shopify_repository import apply_record, retire_imported, timestamp


class ConnectInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    shop: str = Field(pattern=SHOP_PATTERN, max_length=80)


def install(app: FastAPI, settings: Settings) -> None:
    def enabled() -> None:
        if not settings.shopify_enabled:
            raise HTTPException(503, "Shopify is not configured; app/store credentials are required")

    def client() -> ShopifyClient:
        return ShopifyClient(settings, getattr(app.state, "shopify_transport", None))

    @app.get("/api/shopify")
    def status(request: Request) -> dict[str, Any]:
        identity = accounts.require_owner(request)
        tenant = identity["active_tenant_id"]
        with transaction(settings, tenant) as db:
            accounts.lock_owner(db, identity)
            row = db.execute(
                "SELECT shop,shop_id,scopes,status,updated_at,token_expires_at "
                "FROM shopify_connections WHERE tenant_id=%s",
                (tenant,),
            ).fetchone()
            connection = dict(row) if row else None
            if connection and connection["status"] == "connected" and connection["token_expires_at"]:
                if connection["token_expires_at"] <= datetime.now(UTC):
                    connection["status"] = "refresh_required"
            syncs = db.execute(
                "SELECT id,status,products,created_at FROM shopify_syncs WHERE tenant_id=%s "
                "ORDER BY created_at DESC LIMIT %s",
                (tenant, settings.shopify_max_syncs),
            ).fetchall()
            receipt = db.execute(
                "SELECT count(*) AS total,max(received_at) AS latest "
                "FROM shopify_receipts WHERE tenant_id=%s",
                (tenant,),
            ).fetchone()
        return {
            "configured": settings.shopify_enabled,
            "connection": connection,
            "syncs": syncs,
            "webhooks": dict(receipt or {}),
        }

    @app.post("/api/shopify/connect")
    def connect(body: ConnectInput, request: Request, response: Response) -> dict[str, str]:
        identity = accounts.require_owner(request)
        enabled()
        state = secrets.token_urlsafe(32)
        browser = secrets.token_urlsafe(32)
        expiry = datetime.now(UTC) + timedelta(seconds=settings.shopify_state_ttl_seconds)
        with transaction(settings) as db:
            accounts.lock_owner(db, identity)
            db.execute(
                "DELETE FROM shopify_oauth_states WHERE expires_at<=now() OR session_hash=%s",
                (identity["token_hash"],),
            )
            db.execute(
                "INSERT INTO shopify_oauth_states(state_hash,browser_hash,session_hash,account_id,"
                "tenant_id,shop,expires_at) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (
                    accounts.hashed(state),
                    accounts.hashed(browser),
                    identity["token_hash"],
                    identity["id"],
                    identity["active_tenant_id"],
                    body.shop,
                    expiry,
                ),
            )
        response.set_cookie(
            settings.shopify_oauth_cookie_name,
            browser,
            max_age=settings.shopify_state_ttl_seconds,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="lax",
            path="/api/shopify/callback",
        )
        query = urlencode(
            {
                "client_id": settings.shopify_client_id,
                "scope": ",".join(settings.shopify_scopes),
                "redirect_uri": settings.shopify_redirect_uri,
                "state": state,
            }
        )
        return {
            "authorization_url": settings.shopify_origin_template.format(shop=body.shop)
            + AUTHORIZE_PATH
            + "?"
            + query
        }

    @app.get("/api/shopify/callback")
    def callback(request: Request) -> RedirectResponse:
        enabled()
        pairs = list(request.query_params.multi_items())
        if len(pairs) != len({key for key, _ in pairs}) or any(len(value) > 4096 for _, value in pairs):
            raise HTTPException(400, "OAuth callback parameters are invalid")
        values = dict(pairs)
        shop, state, code = (values.get(key, "") for key in ("shop", "state", "code"))
        if not re.fullmatch(SHOP_PATTERN, shop) or not state or not code:
            raise HTTPException(400, "OAuth callback is incomplete")
        try:
            issued = datetime.fromtimestamp(int(values.get("timestamp", "")), UTC)
        except (ValueError, OverflowError, OSError):
            raise HTTPException(400, "OAuth callback timestamp is invalid") from None
        age = (datetime.now(UTC) - issued).total_seconds()
        if not -settings.shopify_clock_skew_seconds <= age <= settings.shopify_callback_max_age_seconds:
            raise HTTPException(403, "OAuth callback has expired")
        message = "&".join(f"{key}={value}" for key, value in sorted(pairs) if key != "hmac")
        secret = settings.shopify_client_secret
        digest = hmac.new(
            secret.get_secret_value().encode() if secret else b"", message.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(digest, values.get("hmac", "")):
            raise HTTPException(403, "OAuth callback signature is invalid")
        browser = request.cookies.get(settings.shopify_oauth_cookie_name, "")
        # Consuming state is committed before provider transport so retries cannot reuse a code.
        with transaction(settings) as db:
            saved = db.execute(
                "DELETE FROM shopify_oauth_states WHERE state_hash=%s "
                "AND browser_hash=%s AND shop=%s AND expires_at>now() RETURNING *",
                (accounts.hashed(state), accounts.hashed(browser), shop),
            ).fetchone()
            if saved is None:
                raise HTTPException(403, "OAuth state is invalid, expired or already used")
        identity = {
            "id": str(saved["account_id"]),
            "active_tenant_id": str(saved["tenant_id"]),
            "token_hash": saved["session_hash"],
        }
        tenant = identity["active_tenant_id"]
        with transaction(settings, tenant) as db:
            # OAuth state names its owner-approved workspace even if another tab
            # selected a different workspace during the provider redirect.
            accounts.lock_owner(db, identity, require_active_tenant=False)
            provider = client()
            tokens = provider.exchange(shop, code=code)
            data = provider.graphql(shop, tokens["access_token"], "identity")
            provider_shop = data.get("shop", {})
            if (
                not isinstance(provider_shop, dict)
                or provider_shop.get("myshopifyDomain") != shop
                or not str(provider_shop.get("id", "")).startswith("gid://shopify/Shop/")
            ):
                raise HTTPException(403, "Shopify store identity verification failed")
            try:
                db.execute(
                    "INSERT INTO shopify_bindings(shop,tenant_id,status) VALUES(%s,%s,'connected') "
                    "ON CONFLICT(shop) DO UPDATE SET status='connected',installed_at=now() "
                    "WHERE shopify_bindings.tenant_id=EXCLUDED.tenant_id",
                    (shop, tenant),
                )
                binding = db.execute(
                    "SELECT tenant_id FROM shopify_bindings WHERE shop=%s", (shop,)
                ).fetchone()
                if not binding or str(binding["tenant_id"]) != tenant:
                    raise HTTPException(409, "Store is bound to a different workspace")
                db.execute(
                    "INSERT INTO shopify_connections(tenant_id,shop,shop_id,encrypted_tokens,scopes,"
                    "token_expires_at,status) VALUES(%s,%s,%s,%s,%s,%s,'connected') "
                    "ON CONFLICT(tenant_id) DO UPDATE SET shop=EXCLUDED.shop,shop_id=EXCLUDED.shop_id,"
                    "encrypted_tokens=EXCLUDED.encrypted_tokens,scopes=EXCLUDED.scopes,"
                    "token_expires_at=EXCLUDED.token_expires_at,status='connected',updated_at=now()",
                    (
                        tenant,
                        shop,
                        provider_shop["id"],
                        encrypted(settings, tenant, shop, tokens),
                        Jsonb(settings.shopify_scopes),
                        tokens["expires_at"],
                    ),
                )
            except psycopg.errors.UniqueViolation:
                raise HTTPException(
                    409, "Disconnect the existing workspace store before connecting another"
                ) from None
            repository.audit(db, tenant, "shopify.connected", shop, settings)
        response = RedirectResponse(
            settings.shopify_return_url or "", status_code=303, headers={"Referrer-Policy": "no-referrer"}
        )
        response.delete_cookie(
            settings.shopify_oauth_cookie_name,
            path="/api/shopify/callback",
            secure=settings.cookie_secure,
            httponly=True,
            samesite="lax",
        )
        return response

    @app.post("/api/shopify/sync")
    def sync(_: EmptyBody, request: Request) -> dict[str, Any]:
        identity = accounts.require_owner(request)
        enabled()
        tenant = identity["active_tenant_id"]
        sync_id = str(uuid4())
        # History survives a failed provider transaction without partial product import.
        with transaction(settings, tenant) as db:
            accounts.lock_owner(db, identity)
            db.execute(
                "INSERT INTO shopify_syncs(tenant_id,id,status) VALUES(%s,%s,'running')", (tenant, sync_id)
            )
            db.execute(
                "DELETE FROM shopify_syncs WHERE tenant_id=%s AND id IN "
                "(SELECT id FROM shopify_syncs WHERE tenant_id=%s ORDER BY created_at DESC OFFSET %s)",
                (tenant, tenant, settings.shopify_max_syncs),
            )
        try:
            with transaction(settings, tenant) as db:
                accounts.lock_owner(db, identity)
                connection = db.execute(
                    "SELECT * FROM shopify_connections WHERE tenant_id=%s FOR UPDATE", (tenant,)
                ).fetchone()
                if (
                    not connection
                    or connection["status"] != "connected"
                    or not connection["encrypted_tokens"]
                ):
                    raise HTTPException(409, "Connect a Shopify store before synchronizing")
                provider = client()
                token = access_token(db, dict(connection), settings, provider)
                cursor = None
                seen_cursors: set[str] = set()
                imported = 0
                for page in range(settings.shopify_max_pages):
                    data = provider.graphql(
                        connection["shop"],
                        token,
                        "products",
                        {"first": settings.shopify_page_size, "after": cursor},
                    )
                    products = data.get("products", {})
                    if not isinstance(products, dict) or not isinstance(products.get("nodes"), list):
                        raise HTTPException(502, "Shopify product page is invalid")
                    nodes = products["nodes"]
                    if (
                        len(nodes) > settings.shopify_page_size
                        or imported + len(nodes) > settings.max_products
                    ):
                        raise HTTPException(422, "Store catalog exceeds configured synchronization bounds")
                    for product in nodes:
                        if not isinstance(product, dict):
                            raise HTTPException(502, "Shopify product is invalid")
                        apply_record(
                            db, tenant, product, timestamp(product.get("updatedAt")), False, settings
                        )
                    imported += len(nodes)
                    info = products.get("pageInfo", {})
                    if not isinstance(info, dict) or not isinstance(info.get("hasNextPage"), bool):
                        raise HTTPException(502, "Shopify pagination metadata is invalid")
                    if not info.get("hasNextPage"):
                        break
                    cursor = info.get("endCursor")
                    if not isinstance(cursor, str) or not cursor or cursor in seen_cursors:
                        raise HTTPException(502, "Shopify pagination cursor is invalid")
                    seen_cursors.add(cursor)
                    if page + 1 == settings.shopify_max_pages:
                        raise HTTPException(422, "Shopify pagination exceeded configured page limit")
                db.execute(
                    "UPDATE shopify_syncs SET status='completed',products=%s WHERE tenant_id=%s AND id=%s",
                    (imported, tenant, sync_id),
                )
                repository.audit(db, tenant, "shopify.sync_completed", sync_id, settings)
        except HTTPException as exc:
            with transaction(settings, tenant) as db:
                db.execute(
                    "UPDATE shopify_syncs SET status='failed' WHERE tenant_id=%s AND id=%s", (tenant, sync_id)
                )
                if exc.status_code == 409 and "credentials" in str(exc.detail):
                    db.execute(
                        "UPDATE shopify_connections SET status='reconnect_required',updated_at=now() "
                        "WHERE tenant_id=%s",
                        (tenant,),
                    )
            raise
        return {"sync": {"id": sync_id, "status": "completed", "products": imported}}

    @app.get("/api/shopify/export")
    def export(request: Request) -> dict[str, Any]:
        identity = accounts.require_owner(request)
        tenant = identity["active_tenant_id"]
        with transaction(settings, tenant) as db:
            accounts.lock_owner(db, identity)
            rows = db.execute(
                "SELECT product_id,payload,event_at,deleted FROM shopify_records "
                "WHERE tenant_id=%s ORDER BY product_id",
                (tenant,),
            ).fetchall()
        return {"records": rows, "published": False}

    @app.post("/api/shopify/disconnect")
    def disconnect(_: EmptyBody, request: Request) -> dict[str, str]:
        identity = accounts.require_owner(request)
        tenant = identity["active_tenant_id"]
        with transaction(settings, tenant) as db:
            accounts.lock_owner(db, identity)
            db.execute(
                "UPDATE shopify_connections SET encrypted_tokens=NULL,token_expires_at=NULL,"
                "status='disconnected',updated_at=now() WHERE tenant_id=%s",
                (tenant,),
            )
            db.execute("UPDATE shopify_bindings SET status='disconnected' WHERE tenant_id=%s", (tenant,))
            db.execute("DELETE FROM shopify_oauth_states WHERE tenant_id=%s", (tenant,))
            repository.audit(db, tenant, "shopify.disconnected", tenant, settings)
        return {"status": "disconnected"}

    @app.delete("/api/shopify/data")
    def delete_data(request: Request) -> dict[str, str]:
        identity = accounts.require_owner(request)
        tenant = identity["active_tenant_id"]
        with transaction(settings, tenant) as db:
            accounts.lock_owner(db, identity)
            retire_imported(db, tenant, settings)
            repository.audit(db, tenant, "shopify.data_retired", tenant, settings)
        return {"status": "retired"}

    @app.post("/api/shopify/webhook")
    async def webhook(request: Request) -> dict[str, Any]:
        enabled()
        raw = await request.body()
        return dict(await run_in_threadpool(process_webhook, request, raw))

    def process_webhook(request: Request, raw: bytes) -> dict[str, Any]:
        secret = settings.shopify_client_secret
        expected = base64.b64encode(
            hmac.new(secret.get_secret_value().encode() if secret else b"", raw, hashlib.sha256).digest()
        ).decode()
        if not hmac.compare_digest(expected, request.headers.get("X-Shopify-Hmac-Sha256", "")):
            raise HTTPException(401, "Webhook signature is invalid")
        shop = request.headers.get("X-Shopify-Shop-Domain", "")
        topic = request.headers.get("X-Shopify-Topic", "")
        delivery = request.headers.get("X-Shopify-Webhook-Id", "")
        try:
            UUID(delivery)
        except ValueError:
            raise HTTPException(400, "Webhook delivery identity is invalid") from None
        if not re.fullmatch(SHOP_PATTERN, shop) or topic not in SUPPORTED_TOPICS:
            raise HTTPException(400, "Webhook shop or topic is unsupported")
        event_at = timestamp(request.headers.get("X-Shopify-Triggered-At"))
        age = (datetime.now(UTC) - event_at).total_seconds()
        if not -settings.shopify_clock_skew_seconds <= age <= settings.shopify_webhook_max_age_seconds:
            raise HTTPException(400, "Webhook timestamp exceeds configured delivery window")
        try:
            payload = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(400, "Webhook JSON is invalid") from None
        if not isinstance(payload, dict):
            raise HTTPException(400, "Webhook payload must be an object")
        with transaction(settings) as db:
            binding = db.execute(
                "SELECT tenant_id,status FROM shopify_bindings WHERE shop=%s", (shop,)
            ).fetchone()
        if not binding:
            raise HTTPException(404, "Webhook store is not connected")
        tenant = str(binding["tenant_id"])
        with transaction(settings, tenant) as db:
            tenant_lock(db, tenant)
            bound = db.execute(
                "SELECT status,installed_at FROM shopify_bindings WHERE shop=%s AND tenant_id=%s",
                (shop, tenant),
            ).fetchone()
            previous = db.execute(
                "SELECT topic,body_hash FROM shopify_receipts WHERE tenant_id=%s AND event_id=%s",
                (tenant, delivery),
            ).fetchone()
            body_hash = hashlib.sha256(raw).hexdigest()
            if previous:
                if previous["body_hash"] != body_hash or previous["topic"] != topic:
                    raise HTTPException(409, "Webhook identity was reused with different content")
                return {"accepted": True, "duplicate": True}
            db.execute(
                "DELETE FROM shopify_receipts WHERE tenant_id=%s "
                "AND received_at<now()-make_interval(days=>%s)",
                (tenant, settings.shopify_receipt_retention_days),
            )
            total = db.execute(
                "SELECT count(*) AS n FROM shopify_receipts WHERE tenant_id=%s", (tenant,)
            ).fetchone()
            if total and total["n"] >= settings.shopify_max_receipts:
                raise HTTPException(503, "Webhook receipt quota reached; retry later")
            effect = False
            if bound and bound["status"] == "connected" and event_at >= bound["installed_at"]:
                if topic == "app/uninstalled":
                    retire_imported(db, tenant, settings)
                    effect = True
                else:
                    changed_at = (
                        timestamp(payload.get("updated_at")) if payload.get("updated_at") else event_at
                    )
                    # Payload timestamps cannot bypass delivery ordering bounds.
                    if changed_at > event_at + timedelta(seconds=settings.shopify_clock_skew_seconds):
                        raise HTTPException(400, "Webhook product timestamp exceeds its delivery time")
                    effect = apply_record(
                        db, tenant, payload, changed_at, topic == "products/delete", settings
                    )
            db.execute(
                "INSERT INTO shopify_receipts(tenant_id,event_id,topic,body_hash,event_at,status) "
                "VALUES(%s,%s,%s,%s,%s,%s)",
                (tenant, delivery, topic, body_hash, event_at, "applied" if effect else "ignored"),
            )
        return {"accepted": True, "duplicate": False, "applied": effect}
