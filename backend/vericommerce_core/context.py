"""Explicit retrieval comparisons and bounded traces over authorized current evidence."""

from __future__ import annotations

import math
import re
from typing import Any

import numpy as np

from .database import Connection
from .phase_models import ContextInput
from .repository import citation, current_passages, digest, eligible_products
from .retrieval import RetrievalEngine
from .uploads import policy


def rank_passages(
    engine: RetrievalEngine, passages: list[dict[str, Any]], request: ContextInput
) -> dict[str, Any]:
    configuration = policy(engine.settings)
    unavailable = request.method in {"dense", "hybrid", "rerank"} and engine.model is None
    if unavailable:
        return {
            "method": request.method,
            "available": False,
            "results": [],
            "reason": engine.status()["reason"],
            "retrieval": engine.status(),
        }
    tokens = engine.tokens(request.query, [p["product_name"] for p in passages])

    def terms(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]+", text.casefold()))

    lexical = []
    for passage in passages:
        overlap = len(set(tokens) & terms(passage["text"] + " " + passage["label"] + " " + passage["value"]))
        if overlap:
            lexical.append((str(passage["passage_id"]), overlap / max(len(tokens), 1)))
    lexical.sort(key=lambda item: (-item[1], item[0]))
    dense = []
    if request.method != "keyword" and passages and tokens:
        with engine.lock:
            missing = [
                p
                for p in passages
                if p.get("embedding") is None
                or p.get("embedding_revision") != engine.settings.embedding_revision
            ]
            if missing:
                vectors = list(
                    engine.model.embed(
                        [p["text"] for p in missing], batch_size=engine.settings.embedding_batch_size
                    )
                )
                for passage, vector in zip(missing, vectors, strict=True):
                    passage["embedding"] = vector.tolist()
                    passage["embedding_revision"] = engine.settings.embedding_revision
            query_vector = np.asarray(next(iter(engine.model.query_embed(request.query))), dtype=np.float32)
        for passage in passages:
            similarity = float(np.dot(query_vector, np.asarray(passage["embedding"], dtype=np.float32)))
            if math.isfinite(similarity) and similarity >= engine.settings.dense_min_similarity:
                dense.append((str(passage["passage_id"]), similarity))
        dense.sort(key=lambda item: (-item[1], item[0]))
    if request.method == "keyword":
        ranking = lexical
    elif request.method == "dense":
        ranking = dense
    else:
        scores: dict[str, float] = {}
        # Context used for factual drafting still requires independent subject relevance.
        relevant = {identity for identity, _ in lexical}
        for values in (lexical, dense):
            for index, (identity, _) in enumerate(values, 1):
                if identity in relevant:
                    scores[identity] = scores.get(identity, 0) + 1 / (engine.settings.rrf_constant + index)
        if request.method == "rerank":
            by_id = {str(p["passage_id"]): p for p in passages}
            label_weight = float(configuration["reranker"]["label_weight"])
            text_weight = float(configuration["reranker"]["text_weight"])
            for identity in scores:
                passage = by_id[identity]
                scores[identity] += label_weight * len(set(tokens) & terms(passage["label"]))
                scores[identity] += (
                    text_weight * len(set(tokens) & terms(passage["text"])) / max(len(tokens), 1)
                )
        ranking = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    by_id = {str(p["passage_id"]): p for p in passages}
    results = [
        {**citation(by_id[identity]), "score": score}
        for identity, score in ranking[: engine.settings.max_search_limit]
    ]
    return {
        "method": request.method,
        "available": True,
        "results": results,
        "retrieval": engine.status(),
        "reranker": configuration["reranker"]["name"] if request.method == "rerank" else None,
    }


def select_context(
    db: Connection, tenant_id: str, request: ContextInput, engine: RetrievalEngine
) -> dict[str, Any]:
    matching = eligible_products(
        db, tenant_id, request.query, request.product_id, request.sku, request.color, request.category
    )
    query_tokens = set(re.findall(r"[a-z0-9_-]+", request.query.casefold()))
    passages = [p for identity in matching for p in current_passages(db, tenant_id, identity)]
    response = rank_passages(engine, passages, request)
    budget = min(request.budget_chars or engine.settings.context_max_chars, engine.settings.context_max_chars)
    selected: list[dict[str, Any]] = []
    excluded = []
    used = 0
    for result in response["results"]:
        size = len(result["text"])
        if len(selected) >= engine.settings.context_max_passages or used + size > budget:
            excluded.append({"passage_id": result["passage_id"], "reason": "context_budget"})
        else:
            selected.append(result)
            used += size
    included = {p["passage_id"] for p in response["results"]}
    excluded.extend(
        {"passage_id": str(p["passage_id"]), "reason": "below_method_relevance_threshold"}
        for p in passages
        if str(p["passage_id"]) not in included
    )
    response["context"] = {
        "selected": selected,
        "excluded": excluded,
        "budget_chars": budget,
        "used_chars": used,
        "snapshot_hash": digest([citation(p) for p in passages]),
        "authority": policy(engine.settings)["context"]["authority"],
        "constraints": request.model_dump(exclude={"query", "method", "budget_chars"}),
        "eligible_products": matching,
        "intent": "comparison" if "compare" in query_tokens or "vs" in query_tokens else "lookup",
        "cache_key": digest(
            {
                "snapshot": [citation(p) for p in passages],
                "request": request.model_dump(),
                "model_revision": engine.settings.embedding_revision,
                "policy_version": policy(engine.settings)["version"],
            }
        ),
    }
    return response
