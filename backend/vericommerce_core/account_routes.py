"""Same-origin account login, selection and owner membership administration."""

from __future__ import annotations

import threading
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

import psycopg
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from . import account_repository as accounts
from .database import transaction
from .models import EmptyBody
from .security import rate_limit
from .settings import Settings

Email = Annotated[
    str,
    StringConstraints(
        min_length=3,
        max_length=254,
        pattern=r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,63}$",
    ),
]
Role = Literal["owner", "reviewer", "editor", "viewer"]


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: Email
    password: str = Field(min_length=12, max_length=128)
    tenant_name: str = Field(default="My workspace", min_length=1, max_length=100)


class TenantName(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)


class SelectTenant(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tenant_id: UUID


class AddMember(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: Email
    role: Role


class ChangeMember(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_id: UUID
    role: Role | None


def install(app: FastAPI, settings: Settings) -> None:
    capacity = threading.BoundedSemaphore(settings.password_parallelism)

    def login_cookie(response: Response, token: str) -> None:
        response.set_cookie(
            settings.account_cookie_name,
            token,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="strict",
            max_age=settings.account_session_ttl_seconds,
            path="/api",
        )

    def attempts(request: Request) -> None:
        address = request.client.host if request.client else "unknown"
        with transaction(settings) as db:
            rate_limit(
                db, accounts.hashed(address), "account-auth", settings.account_attempts_per_hour, hour=True
            )

    def output_for_token(request: Request, token: str) -> dict[str, Any]:
        request._cookies = {**request.cookies, settings.account_cookie_name: token}
        return accounts.account_output(request)

    @app.get("/api/auth/me")
    def me(request: Request) -> dict[str, Any]:
        return accounts.account_output(request)

    @app.post("/api/auth/register")
    def register(body: Credentials, request: Request, response: Response) -> dict[str, Any]:
        if not settings.registration_enabled:
            raise HTTPException(403, "Account registration is disabled")
        attempts(request)
        if not capacity.acquire(timeout=settings.password_queue_timeout_seconds):
            raise HTTPException(429, "Password processing capacity reached; retry later")
        try:
            encoded = accounts.password_hash(body.password, settings)
        finally:
            capacity.release()
        account_id = str(uuid4())
        try:
            with transaction(settings) as db:
                db.execute("SELECT pg_advisory_xact_lock(hashtext('vericommerce-account-quota'))")
                count = db.execute("SELECT count(*) AS n FROM accounts").fetchone()
                if count and count["n"] >= settings.account_max_accounts:
                    raise HTTPException(429, "Account registration capacity reached")
                db.execute(
                    "INSERT INTO accounts(id,email,password_hash) VALUES(%s,%s,%s)",
                    (account_id, body.email.lower(), encoded),
                )
                tenant = accounts.create_tenant(db, account_id, body.tenant_name, settings)
                token = accounts.create_session(db, account_id, tenant, settings)
        except psycopg.errors.UniqueViolation:
            raise HTTPException(409, "Registration could not be completed for this email") from None
        login_cookie(response, token)
        return output_for_token(request, token)

    @app.post("/api/auth/login")
    def login(body: Credentials, request: Request, response: Response) -> dict[str, Any]:
        attempts(request)
        with transaction(settings) as db:
            account = db.execute(
                "SELECT id,password_hash FROM accounts WHERE email=%s", (body.email.lower(),)
            ).fetchone()
        if not capacity.acquire(timeout=settings.password_queue_timeout_seconds):
            raise HTTPException(429, "Password processing capacity reached; retry later")
        try:
            valid = accounts.password_valid(
                body.password, account["password_hash"] if account else None, settings
            )
        finally:
            capacity.release()
        if not valid or account is None:
            raise HTTPException(401, "Email or password is incorrect")
        with transaction(settings) as db:
            old = request.cookies.get(settings.account_cookie_name, "")
            db.execute("DELETE FROM account_sessions WHERE token_hash=%s", (accounts.hashed(old),))
            membership = db.execute(
                "SELECT tenant_id FROM memberships WHERE account_id=%s ORDER BY tenant_id LIMIT 1",
                (account["id"],),
            ).fetchone()
            token = accounts.create_session(
                db, str(account["id"]), str(membership["tenant_id"]) if membership else None, settings
            )
        login_cookie(response, token)
        return output_for_token(request, token)

    @app.post("/api/auth/logout")
    def logout(_: EmptyBody, request: Request, response: Response) -> dict[str, bool]:
        with transaction(settings) as db:
            db.execute(
                "DELETE FROM account_sessions WHERE token_hash=%s",
                (accounts.hashed(request.cookies.get(settings.account_cookie_name, "")),),
            )
        response.delete_cookie(
            settings.account_cookie_name,
            path="/api",
            secure=settings.cookie_secure,
            httponly=True,
            samesite="strict",
        )
        return {"authenticated": False}

    @app.post("/api/auth/tenants")
    def create_workspace(body: TenantName, request: Request) -> dict[str, Any]:
        identity = accounts.account_identity(request)
        if identity is None:
            raise HTTPException(401, "Account required")
        with transaction(settings) as db:
            tenant = accounts.create_tenant(db, identity["id"], body.name, settings)
            db.execute(
                "UPDATE account_sessions SET active_tenant_id=%s WHERE token_hash=%s",
                (tenant, identity["token_hash"]),
            )
        return accounts.account_output(request)

    @app.post("/api/auth/tenant/select")
    def select_workspace(body: SelectTenant, request: Request) -> dict[str, Any]:
        identity = accounts.account_identity(request)
        if identity is None:
            raise HTTPException(401, "Account required")
        with transaction(settings) as db:
            if not db.execute(
                "SELECT 1 FROM memberships WHERE account_id=%s AND tenant_id=%s",
                (identity["id"], body.tenant_id),
            ).fetchone():
                raise HTTPException(403, "Workspace membership required")
            db.execute(
                "UPDATE account_sessions SET active_tenant_id=%s WHERE token_hash=%s",
                (body.tenant_id, identity["token_hash"]),
            )
        return accounts.account_output(request)

    @app.get("/api/auth/members")
    def list_members(request: Request) -> dict[str, Any]:
        identity = accounts.require_owner(request)
        with transaction(settings) as db:
            tenant = accounts.lock_owner(db, identity)
            return {"members": accounts.members(db, tenant)}

    @app.post("/api/auth/members")
    def add_member(body: AddMember, request: Request) -> dict[str, Any]:
        identity = accounts.require_owner(request)
        tenant = identity["active_tenant_id"]
        with transaction(settings) as db:
            accounts.lock_owner(db, identity)
            account = db.execute("SELECT id FROM accounts WHERE email=%s", (body.email.lower(),)).fetchone()
            if not account:
                raise HTTPException(404, "Register the member account before adding it")
            count = db.execute(
                "SELECT count(*) AS n FROM memberships WHERE tenant_id=%s", (tenant,)
            ).fetchone()
            if count and count["n"] >= settings.account_max_members:
                raise HTTPException(409, "Workspace member limit reached")
            db.execute(
                "INSERT INTO memberships(tenant_id,account_id,role) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
                (tenant, account["id"], body.role),
            )
            return {"members": accounts.members(db, tenant)}

    @app.patch("/api/auth/members")
    def change_member(body: ChangeMember, request: Request) -> dict[str, Any]:
        identity = accounts.require_owner(request)
        tenant = identity["active_tenant_id"]
        with transaction(settings) as db:
            accounts.lock_owner(db, identity)
            row = db.execute(
                "SELECT role FROM memberships WHERE tenant_id=%s AND account_id=%s FOR UPDATE",
                (tenant, body.account_id),
            ).fetchone()
            if not row:
                raise HTTPException(404, "Member not found")
            owners = db.execute(
                "SELECT count(*) AS n FROM memberships WHERE tenant_id=%s AND role='owner'", (tenant,)
            ).fetchone()
            if row["role"] == "owner" and body.role != "owner" and owners and owners["n"] <= 1:
                raise HTTPException(409, "The last owner cannot be removed or demoted")
            if body.role is None:
                db.execute(
                    "DELETE FROM memberships WHERE tenant_id=%s AND account_id=%s", (tenant, body.account_id)
                )
            else:
                db.execute(
                    "UPDATE memberships SET role=%s WHERE tenant_id=%s AND account_id=%s",
                    (body.role, tenant, body.account_id),
                )
            return {"members": accounts.members(db, tenant)}
