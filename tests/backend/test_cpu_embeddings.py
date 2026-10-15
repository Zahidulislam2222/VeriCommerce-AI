"""Actual optional pinned ONNX CPU inference, never a mocked dense score."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np
import pytest


def test_pinned_cpu_model_hybrid_retrieval_and_persisted_vectors(client: Any, settings: Any) -> None:
    from vericommerce_core.database import transaction
    from vericommerce_core.models import SearchInput
    from vericommerce_core.retrieval import RetrievalEngine
    from vericommerce_core.settings import Settings

    cache = os.environ.get("VC_TEST_EMBEDDING_CACHE_DIR")
    if not cache:
        pytest.skip("Actual dense test requires an explicitly prewarmed VC_TEST_EMBEDDING_CACHE_DIR")
    example = Path(__file__).resolve().parents[2] / "backend/.env.example"
    options: dict[str, Any] = {
        "_env_file": example,
        "database_url": settings.database_url,
        "allowed_origins": settings.allowed_origins,
        "embedding_enabled": True,
        "embedding_download_allowed": False,
        "embedding_cache_dir": Path(cache),
        "policy_path": settings.policy_path,
    }
    dense_settings = Settings(**options)
    engine = RetrievalEngine(dense_settings)
    engine.load()
    assert engine.model is not None, engine.status()
    vector = next(iter(engine.model.embed("A documented product specification.")))
    assert len(vector) > 0 and np.isfinite(vector).all()
    tenant_id = client.get("/api/session").json()["tenant_id"]
    with transaction(settings, tenant_id) as db:
        result = engine.answer(db, tenant_id, SearchInput(query="battery life", product_id="forma-one"))
        assert result["abstained"] is False and "40 hours" in result["answer"]
        assert result["retrieval"]["method"] == "hybrid_rrf"
        stored = db.execute(
            "SELECT count(*) AS n FROM passages WHERE tenant_id=%s AND embedding IS NOT NULL "
            "AND embedding_revision=%s",
            (tenant_id, dense_settings.embedding_revision),
        ).fetchone()
        assert stored["n"] == 3
        unsupported = engine.answer(
            db, tenant_id, SearchInput(query="Does it cure eczema?", product_id="verdant-serum")
        )
        assert unsupported["abstained"] is True


def test_unavailable_model_cache_reports_honest_lexical_fallback(settings: Any, tmp_path: Path) -> None:
    from vericommerce_core.retrieval import RetrievalEngine
    from vericommerce_core.settings import Settings

    example = Path(__file__).resolve().parents[2] / "backend/.env.example"
    options: dict[str, Any] = {
        "_env_file": example,
        "database_url": settings.database_url,
        "embedding_enabled": True,
        "embedding_download_allowed": False,
        "embedding_cache_dir": tmp_path / "missing-model",
        "policy_path": settings.policy_path,
    }
    engine = RetrievalEngine(Settings(**options))
    engine.load()
    assert engine.model is None and engine.status()["status"] == "lexical_only"
    assert engine.status()["reason"].startswith("model_unavailable:")
