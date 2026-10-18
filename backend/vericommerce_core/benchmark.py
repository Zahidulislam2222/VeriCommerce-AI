"""Frozen synthetic benchmark with measured metrics and separate human attestations."""

from __future__ import annotations

import json
import math
import statistics
import threading
import time
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from .context import rank_passages
from .database import Connection, tenant_lock
from .models import CatalogInput
from .phase_models import BenchmarkReviewInput, ContextInput
from .repository import audit, digest
from .retrieval import RetrievalEngine
from .settings import Settings
from .uploads import policy

_RUN_SLOT = threading.BoundedSemaphore(1)


def dataset(settings: Settings) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(settings.benchmark_path.read_text())
    declared = result.pop("hash")
    if digest(result) != declared:
        raise ValueError("Frozen benchmark integrity check failed")
    CatalogInput.model_validate(result["catalog"])
    result["hash"] = declared
    return result


def reviewed_dataset(db: Connection, tenant_id: str, settings: Settings) -> dict[str, Any]:
    result = dataset(settings)
    reviews = db.execute(
        "SELECT id,account_id,question_ids,image_ids,decision,notes,created_at "
        "FROM benchmark_reviews WHERE tenant_id=%s AND dataset_hash=%s ORDER BY created_at,id",
        (tenant_id, result["hash"]),
    ).fetchall()
    decisions: dict[str, bool] = {}
    for row in reviews:
        for identity in [*row["question_ids"], *row["image_ids"]]:
            decisions[identity] = row["decision"] == "approved"
    items = [*result["questions"], *result["images"]]
    for item in items:
        item["reviewed"] = decisions.get(item["id"], False)
    human_approved = all(item["reviewed"] for item in items)
    result["human_review_status"] = "approved" if human_approved else "pending"
    result["review_status"] = result["human_review_status"]
    delegated = json.loads(settings.benchmark_agent_review_path.read_text())
    if (
        delegated.get("dataset_hash") == result["hash"]
        and delegated.get("reviewer_type") == "agent"
        and delegated.get("owner_delegated") is True
        and delegated.get("status") == "approved"
        and set(delegated.get("question_ids", [])) == {q["id"] for q in result["questions"]}
        and set(delegated.get("image_ids", [])) == {i["id"] for i in result["images"]}
    ):
        result["agent_review"] = delegated
        if not human_approved:
            result["review_status"] = "agent_reviewed"
    result["reviews"] = reviews
    return result


def save_review(
    db: Connection, tenant_id: str, account_id: str, body: BenchmarkReviewInput, settings: Settings
) -> dict[str, Any]:
    tenant_lock(db, tenant_id)
    corpus = dataset(settings)
    if corpus["hash"] != body.dataset_hash:
        raise HTTPException(409, "Review refers to a different frozen dataset")
    if not body.question_ids and not body.image_ids:
        raise HTTPException(422, "Select the exact reviewed questions or images")
    if not set(body.question_ids).issubset({q["id"] for q in corpus["questions"]}) or not set(
        body.image_ids
    ).issubset({i["id"] for i in corpus["images"]}):
        raise HTTPException(422, "Unknown frozen review item")
    count = db.execute(
        "SELECT count(*) AS n FROM benchmark_reviews WHERE tenant_id=%s", (tenant_id,)
    ).fetchone()
    if count and count["n"] >= settings.max_audit_events:
        raise HTTPException(429, "Review history quota reached")
    identity = str(uuid4())
    db.execute(
        "INSERT INTO benchmark_reviews(tenant_id,id,account_id,dataset_hash,question_ids,"
        "image_ids,decision,notes) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            tenant_id,
            identity,
            account_id,
            body.dataset_hash,
            Jsonb(body.question_ids),
            Jsonb(body.image_ids),
            body.decision,
            body.notes,
        ),
    )
    audit(db, tenant_id, "benchmark.human_review", identity, settings)
    return {"review_id": identity, "dataset_hash": body.dataset_hash, "decision": body.decision}


def run_benchmark(db: Connection, tenant_id: str, engine: RetrievalEngine) -> dict[str, Any]:
    if not _RUN_SLOT.acquire(blocking=False):
        raise HTTPException(409, "Another bounded CPU benchmark is running; retry later")
    try:
        tenant_lock(db, tenant_id)
        count = db.execute(
            "SELECT count(*) AS n FROM benchmark_runs WHERE tenant_id=%s", (tenant_id,)
        ).fetchone()
        if count and count["n"] >= engine.settings.max_evaluations:
            raise HTTPException(429, "Workspace benchmark quota reached")
        corpus = reviewed_dataset(db, tenant_id, engine.settings)
        by_product: dict[str, list[dict[str, Any]]] = {}
        for product in corpus["catalog"]["products"]:
            passages = []
            for index, claim in enumerate(product["claims"]):
                passages.append(
                    {
                        "passage_id": product["id"] + "-" + str(index),
                        "product_id": product["id"],
                        "product_name": product["name"],
                        "source_id": claim["sourceId"],
                        "source_name": product["name"] + " catalog",
                        "source_version": corpus["version"],
                        "revision_id": corpus["hash"],
                        "page": claim["page"],
                        "text": claim["passage"],
                        "label": claim["label"],
                        "value": claim["value"],
                        "embedding": None,
                        "embedding_revision": None,
                    }
                )
            by_product[product["id"]] = passages
        questions = [q for q in corpus["questions"] if q["split"] == "test"]
        reports = []
        for method in ("keyword", "dense", "hybrid", "rerank"):
            recalls = []
            ndcg = []
            correct_abstention = 0
            latencies = []
            cases = []
            available = method == "keyword" or engine.model is not None
            if available:
                for question in questions:
                    start = time.perf_counter()
                    passages = by_product[question["product_id"]]
                    response = rank_passages(
                        engine,
                        passages,
                        ContextInput(
                            query=question["query"], product_id=question["product_id"], method=method
                        ),
                    )
                    elapsed = (time.perf_counter() - start) * 1000
                    latencies.append(elapsed)
                    relevant = {
                        str(p["passage_id"])
                        for p in passages
                        if p["source_id"] == question["expected_source_id"]
                        and p["label"] == question["expected_label"]
                    }
                    returned = [r["passage_id"] for r in response["results"][:10]]
                    if not question["expected_abstain"]:
                        recalls.append(len(set(returned) & relevant) / max(len(relevant), 1))
                        gain = sum(
                            1 / math.log2(index + 2)
                            for index, identity in enumerate(returned)
                            if identity in relevant
                        )
                        ideal = sum(1 / math.log2(index + 2) for index in range(min(len(relevant), 10)))
                        ndcg.append(gain / ideal if ideal else 0)
                    correct_abstention += (not bool(returned)) == question["expected_abstain"]
                    cases.append(
                        {
                            "id": question["id"],
                            "retrieved": returned,
                            "relevant": sorted(relevant),
                            "latency_ms": elapsed,
                            "expected_abstain": question["expected_abstain"],
                        }
                    )
            ordered = sorted(latencies)
            reports.append(
                {
                    "method": method,
                    "available": available,
                    "total": len(questions),
                    "answerable": sum(not q["expected_abstain"] for q in questions),
                    "recall_at_10": statistics.mean(recalls) if recalls else None,
                    "ndcg_at_10": statistics.mean(ndcg) if ndcg else None,
                    "abstention_accuracy": correct_abstention / len(questions) if available else None,
                    "latency_ms_p50": statistics.median(latencies) if latencies else None,
                    "latency_ms_p95": ordered[math.ceil(len(ordered) * 0.95) - 1] if ordered else None,
                    "cases": cases,
                }
            )
        result = {
            "id": str(uuid4()),
            "dataset_version": corpus["version"],
            "dataset_hash": corpus["hash"],
            "review_status": corpus["review_status"],
            "human_review_status": corpus["human_review_status"],
            "split": "test",
            "results": reports,
            "notice": policy(engine.settings)["benchmark_notice"],
            "method_selection": policy(engine.settings)["context"]["selection_method"],
            "selection_basis": policy(engine.settings)["context"]["selection_basis"],
        }
        db.execute(
            "INSERT INTO benchmark_runs(tenant_id,id,result) VALUES(%s,%s,%s)",
            (tenant_id, result["id"], Jsonb(result)),
        )
        audit(db, tenant_id, "benchmark.measured", result["id"], engine.settings)
        return result
    finally:
        _RUN_SLOT.release()
