"""CPU-only pinned ONNX retrieval with explicit lexical fallback and abstention."""

from __future__ import annotations

import re
import threading
from typing import Any

import numpy as np

from .database import Connection
from .models import EvidencePolicy, SearchInput
from .repository import citation, current_passages, eligible_products
from .settings import Settings


class RetrievalEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.policy: dict[str, Any] = EvidencePolicy.model_validate_json(
            settings.policy_path.read_text()
        ).model_dump()
        self.model: Any = None
        self.reason = "disabled"
        self.lock = threading.Lock()

    def load(self) -> None:
        if not self.settings.embedding_enabled:
            return
        try:
            from fastembed import TextEmbedding
            from huggingface_hub import snapshot_download

            path = snapshot_download(
                repo_id=self.settings.embedding_repository or "",
                revision=self.settings.embedding_revision,
                cache_dir=str(self.settings.embedding_cache_dir),
                local_files_only=not self.settings.embedding_download_allowed,
                allow_patterns=[
                    "config.json",
                    "tokenizer.json",
                    "tokenizer_config.json",
                    "special_tokens_map.json",
                    self.settings.embedding_model_file or "",
                ],
                token=False,
            )
            self.model = TextEmbedding(
                model_name=self.settings.embedding_model or "",
                specific_model_path=path,
                cache_dir=str(self.settings.embedding_cache_dir),
                threads=self.settings.embedding_threads,
                providers=["CPUExecutionProvider"],
                local_files_only=True,
            )
            self.reason = "loaded_pinned_cpu_model"
        except Exception as exc:
            self.model = None
            self.reason = "model_unavailable:" + type(exc).__name__

    def status(self) -> dict[str, Any]:
        return {
            "status": "dense_available" if self.model is not None else "lexical_only",
            "method": "hybrid_rrf" if self.model is not None else "lexical",
            "model": self.settings.embedding_model,
            "revision": self.settings.embedding_revision,
            "reason": self.reason,
        }

    def tokens(self, query: str, product_names: list[str]) -> list[str]:
        excluded = set(self.policy["stop_words"])
        for name in product_names:
            excluded.update(re.findall(r"[a-z0-9]+", name.lower()))
        original = [t for t in re.findall(r"[a-z0-9]+", query.lower()) if t not in excluded]
        expanded = list(original)
        for token in original:
            expanded.extend(self.policy["query_expansions"].get(token, []))
        return sorted(set(expanded))

    def search(self, db: Connection, tenant_id: str, request: SearchInput) -> dict[str, Any]:
        limit = min(request.limit or self.settings.search_limit, self.settings.max_search_limit)
        eligible = set(eligible_products(db, tenant_id, request.query, request.product_id))
        passages = [p for p in current_passages(db, tenant_id) if p["product_id"] in eligible]
        if not passages:
            return {"method": self.status()["method"], "results": [], "retrieval": self.status()}
        tokens = self.tokens(request.query, [p["product_name"] for p in passages])
        if not tokens:
            return {"method": self.status()["method"], "results": [], "retrieval": self.status()}
        tsquery = " | ".join(tokens)
        ranks = db.execute(
            "SELECT p.id,ts_rank_cd(p.search_vector,to_tsquery('english',%s)) AS score FROM passages p "
            "JOIN sources s ON s.tenant_id=p.tenant_id AND s.current_revision_id=p.revision_id "
            "WHERE p.tenant_id=%s AND p.product_id=ANY(%s) "
            "AND NOT EXISTS (SELECT 1 FROM source_tombstones t WHERE t.tenant_id=s.tenant_id "
            "AND t.source_id=s.id) "
            "AND NOT EXISTS (SELECT 1 FROM product_tombstones t WHERE t.tenant_id=p.tenant_id "
            "AND t.product_id=p.product_id) "
            "AND p.search_vector @@ to_tsquery('english',%s) ORDER BY score DESC,p.id",
            (tsquery, tenant_id, list(eligible), tsquery),
        ).fetchall()
        eligible_passages = {str(p["passage_id"]) for p in passages}
        lexical = [
            (str(row["id"]), float(row["score"]))
            for row in ranks
            if row["score"] >= self.settings.lexical_min_score and str(row["id"]) in eligible_passages
        ]
        # A dense similarity alone is insufficient evidence of a documented answer.
        # Only passages with independently matching lexical subject matter are eligible.
        allowed_ids = {identity for identity, _ in lexical}
        if not allowed_ids:
            return {"method": self.status()["method"], "results": [], "retrieval": self.status()}
        scores = dict(lexical)
        if self.model is not None:
            with self.lock:
                missing = [
                    p
                    for p in passages
                    if p["embedding"] is None or p["embedding_revision"] != self.settings.embedding_revision
                ]
                if missing:
                    vectors = list(
                        self.model.embed(
                            [p["text"] for p in missing], batch_size=self.settings.embedding_batch_size
                        )
                    )
                    for passage, vector in zip(missing, vectors, strict=True):
                        passage["embedding"] = vector.tolist()
                        db.execute(
                            "UPDATE passages SET embedding=%s,embedding_revision=%s "
                            "WHERE tenant_id=%s AND id=%s",
                            (
                                vector.tolist(),
                                self.settings.embedding_revision,
                                tenant_id,
                                passage["passage_id"],
                            ),
                        )
                query_vector = np.array(next(iter(self.model.query_embed(request.query))), dtype=np.float32)
            dense = []
            for passage in passages:
                vector = np.array(passage["embedding"], dtype=np.float32)
                similarity = float(np.dot(query_vector, vector))
                if similarity >= self.settings.dense_min_similarity:
                    dense.append((str(passage["passage_id"]), similarity))
            dense.sort(key=lambda item: (-item[1], item[0]))
            scores = {}
            for ranking in (lexical, dense):
                for rank, (identity, _) in enumerate(ranking, start=1):
                    if identity in allowed_ids:
                        scores[identity] = scores.get(identity, 0) + 1 / (self.settings.rrf_constant + rank)
        by_id = {str(p["passage_id"]): p for p in passages}
        ranked = sorted(scores, key=lambda identity: (-scores[identity], identity))[:limit]
        return {
            "method": self.status()["method"],
            "results": [{**citation(by_id[identity]), "score": scores[identity]} for identity in ranked],
            "retrieval": self.status(),
        }

    def answer(self, db: Connection, tenant_id: str, request: SearchInput) -> dict[str, Any]:
        search = self.search(db, tenant_id, request)
        results = search["results"]
        if not results:
            return {
                "answer": self.policy["abstention"],
                "abstained": True,
                "method": "unsupported_abstention",
                "citations": [],
                "retrieval": self.status(),
            }
        text = "\n\n".join(
            "“"
            + result["text"]
            + "” ["
            + result["source_name"]
            + ", revision "
            + result["source_version"]
            + ", page "
            + result["page"]
            + "]"
            for result in results
        )
        return {
            "answer": text,
            "abstained": False,
            "method": self.policy["answer_method"],
            "citations": results,
            "retrieval": self.status(),
        }
