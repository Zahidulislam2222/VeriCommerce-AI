"""Restricted-runtime backup proof: real saved payloads and honest empty rehearsal."""

from __future__ import annotations

from typing import Any

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo
from pydantic import SecretStr


def test_strict_restore_probe_reads_actual_saved_payloads_under_rls(client: Any, settings: Any) -> None:
    from vericommerce_core.jobs import process_one
    from vericommerce_core.restore_probe import probe

    job_id = client.post("/api/drafts", json={"product_id": "forma-one"}).json()["job"]["id"]
    for _ in range(100):
        job = client.get(f"/api/jobs/{job_id}").json()["job"]
        if job["status"] == "succeeded":
            break
        process_one(settings)
    assert job["status"] == "succeeded"
    report = probe(settings)
    assert report["restricted_runtime_role"] is True and report["populated_data_verified"] is True
    assert report["rls_without_context"] == "denied"
    assert report["source_payloads_readable"] > 0 and report["draft_payloads_readable"] > 0
    assert report["cross_tenant_checks_denied"] == report["tenants"]
    assert report == probe(settings)
    assert all(set(table) == {"rows", "sha256"} for table in report["tables"].values())


def test_empty_restore_rehearsal_requires_explicit_allow_empty_and_still_checks_rls(settings: Any) -> None:
    from vericommerce_core.migrate import migrate
    from vericommerce_core.restore_probe import probe

    database = "vc_restore_empty_test"
    admin = settings.migration_database_url.get_secret_value()
    with psycopg.connect(make_conninfo(admin, dbname="postgres"), autocommit=True) as db:
        if not db.execute("SELECT 1 FROM pg_database WHERE datname=%s", (database,)).fetchone():
            db.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
    target = settings.model_copy(
        update={
            "database_url": SecretStr(
                make_conninfo(settings.database_url.get_secret_value(), dbname=database)
            ),
            "migration_database_url": SecretStr(make_conninfo(admin, dbname=database)),
        }
    )
    migrate(target)
    with pytest.raises(RuntimeError, match="saved workspace evidence"):
        probe(settings, database)
    report = probe(settings, database, allow_empty=True)
    assert report["restricted_runtime_role"] is True and report["rls_without_context"] == "denied"
    assert report["populated_data_verified"] is False and report["tenants"] == 0
    assert report["source_payloads_readable"] == 0 and report["draft_payloads_readable"] == 0
    assert all(table["rows"] == 0 for table in report["tables"].values())
    with pytest.raises(RuntimeError, match="explicitly isolated"):
        probe(settings, "postgres")
