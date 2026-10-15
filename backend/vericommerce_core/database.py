"""Bounded PostgreSQL connections and transaction-local tenant contexts."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg.rows import dict_row

from .settings import Settings

Connection = psycopg.Connection[dict[str, Any]]


@contextmanager
def transaction(settings: Settings, tenant_id: str | None = None) -> Iterator[Connection]:
    with psycopg.connect(
        settings.database_url.get_secret_value(),
        row_factory=dict_row,
        connect_timeout=settings.db_connect_timeout_seconds,
    ) as connection:
        connection.execute(
            "SELECT set_config('statement_timeout', %s, true)", (str(settings.db_statement_timeout_ms),)
        )
        if tenant_id is not None:
            connection.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant_id,))
        yield connection


def check_runtime_role(connection: Connection) -> None:
    role = connection.execute(
        "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user"
    ).fetchone()
    if role is None or role["rolsuper"] or role["rolbypassrls"]:
        raise RuntimeError("Runtime database role must not be superuser or BYPASSRLS")


def tenant_lock(connection: Connection, tenant_id: str) -> None:
    connection.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (tenant_id,))
