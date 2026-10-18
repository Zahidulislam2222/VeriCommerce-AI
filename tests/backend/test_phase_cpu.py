"""Real pinned ONNX CPU context and frozen held-out benchmark; no mocked scores."""

from __future__ import annotations

import math
import os
import statistics
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def cpu_settings(settings: Any) -> Any:
    from vericommerce_core.settings import Settings

    cache = os.environ.get("VC_TEST_EMBEDDING_CACHE_DIR")
    if not cache:
        pytest.skip("Real CPU phase verification requires explicit prewarmed VC_TEST_EMBEDDING_CACHE_DIR")
    return Settings(
        _env_file=Path(__file__).resolve().parents[2] / "backend/.env.example",
        database_url=settings.database_url,
        allowed_origins=settings.allowed_origins,
        embedding_enabled=True,
        embedding_download_allowed=False,
        embedding_cache_dir=Path(cache),
        policy_path=settings.policy_path,
        seed_path=settings.seed_path,
        intelligence_policy_path=settings.intelligence_policy_path,
        benchmark_path=settings.benchmark_path,
        benchmark_agent_review_path=settings.benchmark_agent_review_path,
        evaluation_path=settings.evaluation_path,
        migrations_path=settings.migrations_path,
        migration_database_url=None,
        requests_per_minute=1000,
        session_creations_per_hour=100,
    )


def test_actual_cpu_context_all_methods_and_independently_recomputed_64_query_metrics(
    cpu_settings: Any,
) -> None:
    from vericommerce_core.benchmark import dataset
    from vericommerce_core.main import create_app
    from vericommerce_core.uploads import policy

    with TestClient(
        create_app(cpu_settings), base_url="https://testserver", headers={"Origin": "https://testserver"}
    ) as client:
        engine = client.app.state.engine  # type: ignore[union-attr]
        assert engine.model is not None and engine.status()["status"] == "dense_available", engine.status()
        vector = next(iter(engine.model.query_embed("documented battery life")))
        assert np.isfinite(vector).all() and len(vector) > 0
        response = client.post("/api/session", json={})
        assert response.status_code == 200, response.text
        tenant = response.json()["tenant_id"]
        for method in ("keyword", "dense", "hybrid", "rerank"):
            response = client.post(
                "/api/context",
                json={
                    "query": "battery life",
                    "product_id": "forma-one",
                    "method": method,
                    "budget_chars": 2000,
                },
                headers={"X-Workspace-ID": tenant},
            )
            assert response.status_code == 200, response.text
            result = response.json()
            assert response.headers["X-Workspace-ID"] == tenant
            assert result["available"] and result["method"] == method
            selected = result["context"]["selected"]
            assert selected and all(p["product_id"] == "forma-one" for p in selected)
            assert any("40 hours" in p["text"] for p in selected)
            assert all(math.isfinite(p["score"]) for p in result["results"])
            assert sum(len(p["text"]) for p in selected) == result["context"]["used_chars"] <= 2000
            assert result["context"]["snapshot_hash"] and result["context"]["cache_key"]
        denied = client.post(
            "/api/context", json={"query": "battery life", "sku": "test-nonexistent-sku", "method": "dense"}
        )
        assert denied.status_code == 200 and denied.json()["context"]["selected"] == []
        response = client.post("/api/benchmarks", json={}, headers={"X-Workspace-ID": tenant})
        assert response.status_code == 200, response.text
        benchmark = response.json()["benchmark"]
        corpus = dataset(cpu_settings)
        cases = {q["id"]: q for q in corpus["questions"] if q["split"] == "test"}
        assert len(cases) == 64 and benchmark["dataset_hash"] == corpus["hash"]
        selection = policy(cpu_settings)["context"]
        assert benchmark["method_selection"] == selection["selection_method"]
        assert benchmark["selection_basis"] == selection["selection_basis"]
        assert {r["method"] for r in benchmark["results"]} == {"keyword", "dense", "hybrid", "rerank"}
        products = {p["id"]: p for p in corpus["catalog"]["products"]}
        for report in benchmark["results"]:
            assert report["available"] and report["total"] == len(cases)
            assert {c["id"] for c in report["cases"]} == set(cases)
            recalls, ndcgs, latencies = [], [], []
            correct_abstention = 0
            for actual in report["cases"]:
                expected = cases[actual["id"]]
                product = products[expected["product_id"]]
                relevant = {
                    product["id"] + "-" + str(index)
                    for index, claim in enumerate(product["claims"])
                    if claim["sourceId"] == expected["expected_source_id"]
                    and claim["label"] == expected["expected_label"]
                }
                assert set(actual["relevant"]) == relevant
                returned = actual["retrieved"]
                assert len(returned) <= 10 and len(returned) == len(set(returned))
                if not expected["expected_abstain"]:
                    recalls.append(len(set(returned) & relevant) / max(len(relevant), 1))
                    gain = sum(
                        1 / math.log2(index + 2)
                        for index, identity in enumerate(returned)
                        if identity in relevant
                    )
                    ideal = sum(1 / math.log2(index + 2) for index in range(min(len(relevant), 10)))
                    ndcgs.append(gain / ideal if ideal else 0)
                correct_abstention += (not bool(returned)) == expected["expected_abstain"]
                assert math.isfinite(actual["latency_ms"]) and actual["latency_ms"] >= 0
                latencies.append(actual["latency_ms"])
            assert report["recall_at_10"] == pytest.approx(statistics.mean(recalls))
            assert report["ndcg_at_10"] == pytest.approx(statistics.mean(ndcgs))
            assert report["abstention_accuracy"] == pytest.approx(correct_abstention / len(cases))
            assert report["latency_ms_p50"] == pytest.approx(statistics.median(latencies))
            assert report["latency_ms_p95"] == pytest.approx(
                sorted(latencies)[math.ceil(len(latencies) * 0.95) - 1]
            )
        persisted = client.get("/api/benchmarks", headers={"X-Workspace-ID": tenant})
        assert persisted.status_code == 200 and persisted.json()["benchmarks"][0]["id"] == benchmark["id"]
