"""A real stalled-claim/two-worker PostgreSQL regression for duplicate effects."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from typing import Any

import pytest


def test_expired_claim_cannot_duplicate_newer_workers_draft(
    client: Any, settings: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from vericommerce_core import jobs
    from vericommerce_core.database import transaction

    # Other independent tests intentionally leave queued work; finish it first.
    for _ in range(100):
        if not jobs.process_one(settings):
            break
    tenant_id = client.get("/api/session").json()["tenant_id"]
    identity = client.post("/api/drafts", json={"product_id": "forma-one"}).json()["job"]["id"]
    claimed = threading.Event()
    resume = threading.Event()

    @contextmanager
    def paused_transaction(config: Any, tenant: str | None = None) -> Iterator[Any]:
        with transaction(config, tenant) as db:
            yield db
        if (
            tenant == tenant_id
            and threading.current_thread().name.startswith("stalled")
            and not claimed.is_set()
        ):
            claimed.set()
            if not resume.wait(timeout=10):
                raise RuntimeError("Concurrency-test barrier timed out")

    monkeypatch.setattr(jobs, "transaction", paused_transaction)
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="stalled") as pool:
        stale_worker = pool.submit(jobs.process_one, settings)
        assert claimed.wait(timeout=10)
        with transaction(settings, tenant_id) as db:
            db.execute(
                "UPDATE jobs SET lease_until=now()-interval '1 second' WHERE tenant_id=%s AND id=%s",
                (tenant_id, identity),
            )
        assert jobs.process_one(settings)
        completed = client.get(f"/api/jobs/{identity}").json()["job"]
        assert completed["status"] == "succeeded" and completed["attempts"] == 2
        resume.set()
        assert stale_worker.result(timeout=10)
    with transaction(settings, tenant_id) as db:
        assert (
            db.execute("SELECT count(*) AS n FROM drafts WHERE tenant_id=%s", (tenant_id,)).fetchone()["n"]
            == 1
        )
        job = db.execute(
            "SELECT status,result,attempts FROM jobs WHERE tenant_id=%s AND id=%s", (tenant_id, identity)
        ).fetchone()
        assert job["status"] == "succeeded" and job["result"] == completed["result"] and job["attempts"] == 2


def test_worker_batch_cannot_exclude_newer_tenants(settings: Any) -> None:
    from pydantic import ValidationError
    from vericommerce_core.settings import Settings

    with pytest.raises(ValidationError):
        Settings(database_url=settings.database_url, max_active_sessions=100, worker_tenant_batch=10)
