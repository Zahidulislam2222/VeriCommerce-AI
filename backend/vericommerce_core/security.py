"""Same-origin workspace guards, opaque cookies, and durable abuse bounds."""

from __future__ import annotations

import hashlib
from http.cookies import SimpleCookie

from fastapi import HTTPException, Request
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .database import Connection, transaction
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


def authenticated_tenant(request: Request) -> str:
    settings: Settings = request.app.state.settings
    token = request.cookies.get(settings.cookie_name, "")
    if not token or len(token) > 128:
        raise HTTPException(401, "Start a private workspace session first")
    with transaction(settings) as db:
        row = db.execute(
            "SELECT tenant_id FROM demo_sessions WHERE token_hash=%s AND expires_at>now()",
            (token_hash(token),),
        ).fetchone()
    if row is None:
        raise HTTPException(401, "Workspace session expired; start a new workspace")
    return str(row["tenant_id"])


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
        client = scope.get("client")
        address = client[0] if client else "unknown"
        key = token_hash(address)
        with transaction(self.settings) as db:
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
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            if headers.get("origin") not in self.settings.allowed_origins:
                await JSONResponse({"detail": "An allowed same-origin request is required"}, 403)(
                    scope, receive, send
                )
                return
            if headers.get("sec-fetch-site") in {"cross-site", "none"}:
                await JSONResponse({"detail": "Cross-site writes are not allowed"}, 403)(scope, receive, send)
                return
            if headers.get("content-type", "").split(";")[0].strip() != "application/json":
                await JSONResponse({"detail": "Use application/json"}, 415)(scope, receive, send)
                return
        body = bytearray()
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                body.extend(message.get("body", b""))
                if len(body) > self.settings.max_body_bytes:
                    await JSONResponse({"detail": "Workspace request exceeds configured body limit"}, 413)(
                        scope, receive, send
                    )
                    return
                if not message.get("more_body", False):
                    break
        if scope["path"] not in {"/api/healthz", "/api/readyz"}:
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
                    if key.lower() not in {b"cache-control", b"vary"}
                ]
                response_headers.extend(
                    [
                        (b"cache-control", b"no-store"),
                        (b"vary", b"Cookie"),
                        (b"x-content-type-options", b"nosniff"),
                    ]
                )
                message = {**message, "headers": response_headers}
            await send(message)

        await self.app(scope, replay, private_response)
