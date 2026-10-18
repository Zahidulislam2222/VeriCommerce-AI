"""Password identities and membership-derived opaque server sessions."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, Request

from .database import Connection, tenant_lock, transaction
from .settings import Settings

CAPABILITIES = {
    "owner": ["read", "edit", "approve", "manage_members", "shopify"],
    "reviewer": ["read", "approve"],
    "editor": ["read", "edit"],
    "viewer": ["read"],
}


def hashed(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def derive(password: str, salt: bytes, settings: Settings) -> bytes:
    return hashlib.scrypt(
        password.encode(),
        salt=salt,
        n=settings.password_scrypt_n,
        r=settings.password_scrypt_r,
        p=settings.password_scrypt_p,
        maxmem=settings.password_scrypt_maxmem,
        dklen=32,
    )


def password_hash(password: str, settings: Settings) -> str:
    salt = secrets.token_bytes(16)
    result = derive(password, salt, settings)
    return "$".join(
        [
            "scrypt",
            str(settings.password_scrypt_n),
            str(settings.password_scrypt_r),
            str(settings.password_scrypt_p),
            base64.b64encode(salt).decode(),
            base64.b64encode(result).decode(),
        ]
    )


def password_valid(password: str, encoded: str | None, settings: Settings) -> bool:
    if encoded is None:
        derive(password, bytes(16), settings)
        return False
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$")
        if algorithm != "scrypt" or (int(n), int(r), int(p)) != (
            settings.password_scrypt_n,
            settings.password_scrypt_r,
            settings.password_scrypt_p,
        ):
            return False
        actual = derive(password, base64.b64decode(salt, validate=True), settings)
        return hmac.compare_digest(actual, base64.b64decode(expected, validate=True))
    except (ValueError, TypeError):
        return False


def create_tenant(db: Connection, account_id: str, name: str, settings: Settings) -> str:
    db.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (account_id,))
    count = db.execute("SELECT count(*) AS n FROM memberships WHERE account_id=%s", (account_id,)).fetchone()
    if count and count["n"] >= settings.account_max_tenants:
        raise HTTPException(409, "Account workspace limit reached")
    tenant = str(uuid4())
    # Permanent merchant registry is distinct from any usable demo-cookie identity.
    db.execute(
        "INSERT INTO demo_sessions(tenant_id,token_hash,expires_at,mode,name) "
        "VALUES(%s,%s,'infinity','merchant',%s)",
        (tenant, hashed(secrets.token_urlsafe(32)), name),
    )
    db.execute(
        "INSERT INTO memberships(tenant_id,account_id,role) VALUES(%s,%s,'owner')", (tenant, account_id)
    )
    return tenant


def create_session(db: Connection, account_id: str, tenant_id: str | None, settings: Settings) -> str:
    token = secrets.token_urlsafe(32)
    expiry = datetime.now(UTC) + timedelta(seconds=settings.account_session_ttl_seconds)
    db.execute("DELETE FROM account_sessions WHERE expires_at<=now()")
    db.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (account_id,))
    db.execute(
        "DELETE FROM account_sessions WHERE token_hash IN "
        "(SELECT token_hash FROM account_sessions WHERE account_id=%s "
        "ORDER BY created_at DESC OFFSET %s)",
        (account_id, settings.account_max_sessions - 1),
    )
    db.execute(
        "INSERT INTO account_sessions(token_hash,account_id,active_tenant_id,expires_at) VALUES(%s,%s,%s,%s)",
        (hashed(token), account_id, tenant_id, expiry),
    )
    return token


def account_identity(request: Request, required: bool = True) -> dict[str, Any] | None:
    settings: Settings = request.app.state.settings
    token = request.cookies.get(settings.account_cookie_name, "")
    if not token:
        if required:
            raise HTTPException(401, "Account login required")
        return None
    if len(token) > 128:
        raise HTTPException(401, "Account session is invalid")
    with transaction(settings) as db:
        row = db.execute(
            "SELECT a.id,a.email,s.active_tenant_id,s.token_hash,m.role "
            "FROM account_sessions s JOIN accounts a ON a.id=s.account_id "
            "LEFT JOIN memberships m ON m.account_id=a.id AND m.tenant_id=s.active_tenant_id "
            "WHERE s.token_hash=%s AND s.expires_at>now()",
            (hashed(token),),
        ).fetchone()
    if row is None:
        raise HTTPException(401, "Account session expired; log in again")
    return {
        **dict(row),
        "id": str(row["id"]),
        "active_tenant_id": str(row["active_tenant_id"]) if row["active_tenant_id"] else None,
    }


def account_output(request: Request) -> dict[str, Any]:
    identity = account_identity(request, required=False)
    if identity is None:
        return {"authenticated": False, "memberships": [], "capabilities": ["read", "edit", "approve"]}
    settings: Settings = request.app.state.settings
    with transaction(settings) as db:
        rows = db.execute(
            "SELECT m.tenant_id,t.name,m.role FROM memberships m "
            "JOIN demo_sessions t ON t.tenant_id=m.tenant_id "
            "WHERE m.account_id=%s ORDER BY t.created_at,m.tenant_id",
            (identity["id"],),
        ).fetchall()
    return {
        "authenticated": True,
        "user": {"id": identity["id"], "email": identity["email"]},
        "memberships": [{**r, "tenant_id": str(r["tenant_id"])} for r in rows],
        "active_tenant_id": identity["active_tenant_id"],
        "capabilities": CAPABILITIES.get(identity["role"], []),
    }


def require_owner(request: Request) -> dict[str, Any]:
    identity = account_identity(request)
    if identity is None or identity["role"] != "owner":
        raise HTTPException(403, "Workspace owner permission required")
    from .security import workspace_context

    workspace_context(request, str(identity["active_tenant_id"]))
    return identity


def lock_owner(db: Connection, identity: dict[str, Any], require_active_tenant: bool = True) -> str:
    """Recheck authorization inside the same tenant lock as the protected mutation."""
    tenant = str(identity["active_tenant_id"])
    tenant_lock(db, tenant)
    row = db.execute(
        "SELECT role FROM memberships WHERE tenant_id=%s AND account_id=%s", (tenant, identity["id"])
    ).fetchone()
    session = db.execute(
        "SELECT 1 FROM account_sessions WHERE token_hash=%s AND account_id=%s AND expires_at>now() "
        "AND (%s OR active_tenant_id=%s)",
        (identity["token_hash"], identity["id"], not require_active_tenant, tenant),
    ).fetchone()
    if not row or row["role"] != "owner" or not session:
        raise HTTPException(403, "Current workspace owner permission required")
    return tenant


def members(db: Connection, tenant: str) -> list[dict[str, Any]]:
    return list(
        db.execute(
            "SELECT a.id AS account_id,a.email,m.role FROM memberships m "
            "JOIN accounts a ON a.id=m.account_id WHERE m.tenant_id=%s ORDER BY a.email",
            (tenant,),
        ).fetchall()
    )
