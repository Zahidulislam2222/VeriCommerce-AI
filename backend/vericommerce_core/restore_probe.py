"""Prove restored evidence is usable under the restricted runtime role and RLS."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from typing import Any
from uuid import uuid4

from psycopg import sql
from psycopg.conninfo import make_conninfo
from pydantic import SecretStr

from .database import GLOBAL_TABLES, TENANT_TABLES, check_runtime_role, transaction
from .settings import Settings, get_settings

PROTECTED_TABLES = TENANT_TABLES


def hash_rows(rows: list[dict[str, Any]]) -> str:
    serialized = sorted(json.dumps(row, sort_keys=True, default=str, separators=(",", ":")) for row in rows)
    return hashlib.sha256("\n".join(serialized).encode()).hexdigest()


def probe(settings: Settings, database: str | None = None, allow_empty: bool = False) -> dict[str, Any]:
    if database is not None:
        if not re.fullmatch(r"vc_restore_[a-z0-9_]+", database):
            raise RuntimeError("Restore probe accepts only explicitly isolated vc_restore_* database names")
        target = make_conninfo(settings.database_url.get_secret_value(), dbname=database)
        settings = settings.model_copy(update={"database_url": SecretStr(target)})
    with transaction(settings) as db:
        check_runtime_role(db)
        tenants = [
            str(row["tenant_id"])
            for row in db.execute("SELECT tenant_id FROM demo_sessions ORDER BY tenant_id").fetchall()
        ]
        if not tenants and not allow_empty:
            raise RuntimeError("Restore probe requires saved workspace evidence from a real flow")
        visibility = db.execute("SELECT count(*) AS n FROM products").fetchone()
        if visibility is None or visibility["n"] != 0:
            raise RuntimeError("RLS without a tenant context exposed product rows")
        global_rows = {
            table: [
                row["payload"]
                for row in db.execute(
                    sql.SQL("SELECT to_jsonb(t) AS payload FROM {} t").format(sql.Identifier(table))
                ).fetchall()
            ]
            for table in GLOBAL_TABLES
        }
    records: dict[str, list[dict[str, Any]]] = {table: [] for table in PROTECTED_TABLES}
    denied = 0
    for tenant_id in tenants:
        with transaction(settings, tenant_id) as db:
            for table in PROTECTED_TABLES:
                rows = [
                    row["payload"]
                    for row in db.execute(
                        sql.SQL("SELECT to_jsonb(t) AS payload FROM {} t").format(sql.Identifier(table))
                    ).fetchall()
                ]
                if any(str(row["tenant_id"]) != tenant_id for row in rows):
                    raise RuntimeError("Cross-tenant row exposed by restored RLS")
                records[table].extend(dict(row) for row in rows)
            other = next((identity for identity in tenants if identity != tenant_id), str(uuid4()))
            visibility = db.execute(
                "SELECT count(*) AS n FROM source_revisions WHERE tenant_id=%s", (other,)
            ).fetchone()
            if visibility is None or visibility["n"] != 0:
                raise RuntimeError("Restored source evidence crossed tenant boundary")
            denied += 1
    populated = bool(records["source_revisions"] and records["drafts"])
    if not populated and not allow_empty:
        raise RuntimeError("Restore probe requires actual saved source and draft payloads")
    all_records = {**global_rows, **records}
    return {
        "restricted_runtime_role": True,
        "rls_without_context": "denied",
        "tenants": len(tenants),
        "cross_tenant_checks_denied": denied,
        "tables": {
            table: {"rows": len(rows), "sha256": hash_rows(rows)}
            for table, rows in sorted(all_records.items())
        },
        "source_payloads_readable": len(records["source_revisions"]),
        "draft_payloads_readable": len(records["drafts"]),
        "populated_data_verified": populated,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database")
    parser.add_argument("--allow-empty", action="store_true")
    args = parser.parse_args()
    print(json.dumps(probe(get_settings(), args.database, args.allow_empty), sort_keys=True))
