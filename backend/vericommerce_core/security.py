"""Same-origin workspace guards, opaque cookies, and durable abuse bounds."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from http.cookies import SimpleCookie

from fastapi import HTTPException, Request
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from . import account_repository as accounts
from .database import Connection, tenant_lock, transaction
from .settings import Settings


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def rate_limit(db: Connection, key: str, scope: str, maximum: int, hour: bool = False) -> None:
    interval = "hour" if hour else "minute"
    row = db.execute(
        "INSERT INTO rate_limits(bucket_key,scope,bucket_start,count) "
        "VALUES(%s,%s,date_trunc(%s,now()),1) ON CONFLICT(bucket_key,scope,bucket_start) "
        "DO UPDATE SET count=rate_limits.count+1 RETURNING count",
        (key, scope, interval),
    ).fetchone()
    if row and row["count"] > maximum:
        raise HTTPException(
            429,
            "Workspace rate limit reached; retry after the current time window",
            headers={"Retry-After": "60" if not hour else "3600"},
        )
    db.execute("DELETE FROM rate_limits WHERE bucket_start<now()-interval '2 hours'")


def workspace_context(request: Request, tenant_id: str) -> str:
    """An optional browser-tab expectation is checked after authoritative identity."""
    expected = request.headers.get("X-Workspace-ID")
    if expected is not None and expected != tenant_id:
        raise HTTPException(
            409, {"code": "workspace_changed", "message": "Workspace changed; reload before continuing"}
        )
    request.state.tenant_id = tenant_id
    return tenant_id


def session_tenant(request: Request, capability: str = "read") -> str:
    settings: Settings = request.app.state.settings
    identity = accounts.account_identity(request, required=False)
    if identity is not None:
        if not identity["active_tenant_id"] or capability not in accounts.CAPABILITIES.get(
            identity["role"], []
        ):
            raise HTTPException(403, "Selected workspace membership lacks the required permission")
        return workspace_context(request, str(identity["active_tenant_id"]))
    if capability not in {"read", "edit", "approve"}:
        raise HTTPException(403, "Merchant account permission required")
    token = request.cookies.get(settings.cookie_name, "")
    if not token or len(token) > 128:
        raise HTTPException(401, "Start a private workspace session first")
    with transaction(settings) as db:
        row = db.execute(
            "SELECT tenant_id FROM demo_sessions WHERE token_hash=%s AND expires_at>now() AND mode='demo'",
            (token_hash(token),),
        ).fetchone()
    if row is None:
        raise HTTPException(401, "Workspace session expired; start a new workspace")
    return workspace_context(request, str(row["tenant_id"]))


def require_capability(capability: str) -> Callable[[Request], str]:
    def dependency(request: Request) -> str:
        return session_tenant(request, capability)

    return dependency


@contextmanager
def authorized_transaction(request: Request, tenant_id: str, capability: str) -> Iterator[Connection]:
    """Serialize permission revocation with every protected workspace mutation."""
    settings: Settings = request.app.state.settings
    with transaction(settings, tenant_id) as db:
        tenant_lock(db, tenant_id)
        account_token = request.cookies.get(settings.account_cookie_name, "")
        if account_token:
            row = db.execute(
                "SELECT m.role FROM account_sessions s JOIN memberships m ON m.account_id=s.account_id "
                "AND m.tenant_id=s.active_tenant_id WHERE s.token_hash=%s AND s.expires_at>now() "
                "AND s.active_tenant_id=%s",
                (token_hash(account_token), tenant_id),
            ).fetchone()
            if not row or capability not in accounts.CAPABILITIES.get(row["role"], []):
                raise HTTPException(403, "Current workspace membership lacks the required permission")
        else:
            token = request.cookies.get(settings.cookie_name, "")
            row = db.execute(
                "SELECT 1 FROM demo_sessions WHERE tenant_id=%s AND token_hash=%s "
                "AND expires_at>now() AND mode='demo'",
                (tenant_id, token_hash(token)),
            ).fetchone()
            if not row or capability not in {"read", "edit", "approve"}:
                raise HTTPException(403, "Current workspace session permission required")
        workspace_context(request, tenant_id)
        yield db


def authenticated_tenant(request: Request) -> str:
    """Legacy route adapter; each new route should name its capability explicitly."""
    capability = "read"
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        if request.url.path.endswith("/approve"):
            capability = "approve"
        elif request.url.path not in {"/api/search", "/api/answers", "/api/session"}:
            capability = "edit"
    return session_tenant(request, capability)


class RequestGuards:
    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app = app
        self.settings = settings

    def enforce_rate(self, headers: dict[str, str], scope: Scope) -> None:
        cookie = SimpleCookie()
        try:
            cookie.load(headers.get("cookie", ""))
        except Exception:
            cookie = SimpleCookie()
        token = cookie.get(self.settings.cookie_name)
        account_token = cookie.get(self.settings.account_cookie_name)
        client = scope.get("client")
        address = client[0] if client else "unknown"
        key = token_hash(address)
        with transaction(self.settings) as db:
            if account_token and len(account_token.value) <= 128:
                identity = token_hash(account_token.value)
                row = db.execute(
                    "SELECT 1 FROM account_sessions WHERE token_hash=%s AND expires_at>now()", (identity,)
                ).fetchone()
                if row:
                    key = identity
            if token and len(token.value) <= 128:
                identity = token_hash(token.value)
                row = db.execute(
                    "SELECT 1 FROM demo_sessions WHERE token_hash=%s AND expires_at>now()", (identity,)
                ).fetchone()
                if row:
                    key = identity
            rate_limit(db, key, "api", self.settings.requests_per_minute)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope.get("path", "").startswith("/api/"):
            await self.app(scope, receive, send)
            return
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        method = scope["method"]
        webhook = scope["path"] == "/api/shopify/webhook" and method == "POST"
        if method in {"POST", "PUT", "PATCH", "DELETE"} and not webhook:
            if headers.get("origin") not in self.settings.allowed_origins:
                await JSONResponse({"detail": "An allowed same-origin request is required"}, 403)(
                    scope, receive, send
                )
                return
            if headers.get("sec-fetch-site") in {"cross-site", "none"}:
                await JSONResponse({"detail": "Cross-site writes are not allowed"}, 403)(scope, receive, send)
                return
            media_type = headers.get("content-type", "").split(";")[0].strip()
            if media_type != "application/json" and not (method == "DELETE" and not media_type):
                await JSONResponse({"detail": "Use application/json"}, 415)(scope, receive, send)
                return
        body = bytearray()
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                body.extend(message.get("body", b""))
                maximum = self.settings.max_body_bytes
                if webhook:
                    maximum = self.settings.shopify_webhook_max_bytes
                elif scope["path"] == "/api/uploads":
                    maximum = max(maximum, (self.settings.upload_max_bytes * 4 // 3) + 8192)
                if len(body) > maximum:
                    await JSONResponse({"detail": "Workspace request exceeds configured body limit"}, 413)(
                        scope, receive, send
                    )
                    return
                if not message.get("more_body", False):
                    break
        if (
            method == "DELETE"
            and body
            and not webhook
            and headers.get("content-type", "").split(";")[0].strip() != "application/json"
        ):
            await JSONResponse({"detail": "Use application/json"}, 415)(scope, receive, send)
            return
        if scope["path"] not in {"/api/healthz", "/api/readyz", "/api/version"}:
            try:
                await run_in_threadpool(self.enforce_rate, headers, scope)
            except HTTPException as exc:
                await JSONResponse({"detail": exc.detail}, exc.status_code, headers=exc.headers)(
                    scope, receive, send
                )
                return
            except Exception:
                await JSONResponse({"detail": "Evidence database is temporarily unavailable"}, 503)(
                    scope, receive, send
                )
                return
        replayed = False

        async def replay() -> Message:
            nonlocal replayed
            if method in {"POST", "PUT", "PATCH", "DELETE"} and not replayed:
                replayed = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        async def private_response(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower()
                    not in {b"cache-control", b"vary", b"x-content-type-options", b"x-workspace-id"}
                ]
                response_headers.extend(
                    [
                        (b"cache-control", b"no-store"),
                        (b"vary", b"Cookie"),
                        (b"x-content-type-options", b"nosniff"),
                    ]
                )
                tenant_id = scope.get("state", {}).get("tenant_id")
                if tenant_id:
                    response_headers.append((b"x-workspace-id", str(tenant_id).encode()))
                message = {**message, "headers": response_headers}
            await send(message)

        await self.app(scope, replay, private_response)
