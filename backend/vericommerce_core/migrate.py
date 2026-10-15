"""Apply versioned migrations using a separate project-local administrator."""

from __future__ import annotations

import hashlib

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

from .settings import Settings, get_settings


def migrate(settings: Settings) -> None:
    admin = settings.migration_database_url
    if admin is None:
        raise RuntimeError("VC_MIGRATION_DATABASE_URL is required only for migrations")
    runtime = conninfo_to_dict(settings.database_url.get_secret_value())
    username = str(runtime.get("user", ""))
    password = str(runtime.get("password", ""))
    if not username or not password:
        raise RuntimeError("Runtime DSN must explicitly configure its restricted role and password")
    with psycopg.connect(admin.get_secret_value(), connect_timeout=settings.db_connect_timeout_seconds) as db:
        db.execute("SELECT pg_advisory_xact_lock(hashtext('vericommerce-schema'))")
        admin_name = db.execute("SELECT current_user").fetchone()
        if admin_name and admin_name[0] == username:
            raise RuntimeError("Runtime and migration roles must be different")
        existing = db.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (username,)).fetchone()
        if existing is None:
            db.execute(
                sql.SQL(
                    "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD {}"
                ).format(sql.Identifier(username), sql.Literal(password))
            )
        else:
            db.execute(
                sql.SQL("ALTER ROLE {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD {}").format(
                    sql.Identifier(username), sql.Literal(password)
                )
            )
        db.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(name text PRIMARY KEY, sha256 text NOT NULL, applied_at timestamptz DEFAULT now())"
        )
        for path in sorted(settings.migrations_path.glob("*.sql")):
            content = path.read_text()
            digest = hashlib.sha256(content.encode()).hexdigest()
            previous = db.execute(
                "SELECT sha256 FROM schema_migrations WHERE name=%s", (path.name,)
            ).fetchone()
            if previous:
                if previous[0] != digest:
                    raise RuntimeError("Applied migration changed: " + path.name)
                continue
            db.execute(content)
            db.execute("INSERT INTO schema_migrations(name,sha256) VALUES(%s,%s)", (path.name, digest))
        db.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(username)))
        for table in (
            "demo_sessions",
            "rate_limits",
            "products",
            "source_revisions",
            "sources",
            "passages",
            "drafts",
            "jobs",
            "audit_events",
            "evaluations",
        ):
            db.execute(
                sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON {} TO {}").format(
                    sql.Identifier(table), sql.Identifier(username)
                )
            )


if __name__ == "__main__":
    migrate(get_settings())
    print("Evidence schema migrations applied; restricted runtime role configured.")
