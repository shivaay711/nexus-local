"""Retrieval evaluation over a labeled benchmark.

Benchmark JSONL row format:
  {"query": "...", "expected_document": "<filename>", "relevance_notes": "...", "domain": "..."}

Relevance definition (documented, honest): a retrieved chunk is relevant iff
it belongs to the expected document. This is document-level relevance; chunk-
level labels can be added to the same format. Metrics are computed only from
an actually executed run — nothing here fabricates numbers.
"""
from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path

from ..db import get_session
from ..models import Document, EvaluationRun
from ..retrieval.hybrid import retrieve


def precision_at_k(relevant_flags: list[bool], k: int) -> float:
    top = relevant_flags[:k]
    return sum(top) / k if k else 0.0


def recall_at_k(relevant_flags: list[bool], k: int, total_relevant: int) -> float:
    if total_relevant == 0:
        return 0.0
    return sum(relevant_flags[:k]) / total_relevant


def mrr(relevant_flags: list[bool]) -> float:
    for i, flag in enumerate(relevant_flags, 1):
        if flag:
            return 1.0 / i
    return 0.0


def ndcg_at_k(relevant_flags: list[bool], k: int) -> float:
    dcg = sum((1.0 if f else 0.0) / math.log2(i + 1)
              for i, f in enumerate(relevant_flags[:k], 1))
    ideal_hits = min(k, sum(relevant_flags))
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0


def _environment() -> dict:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "processor": platform.processor() or "unknown",
        "gpu": "none detected (evaluation environment)",
    }


def run_retrieval_benchmark(benchmark_path: Path, k: int = 5) -> dict:
    raw = Path(benchmark_path).read_bytes()
    dataset_hash = hashlib.sha256(raw).hexdigest()
    rows = [json.loads(line) for line in raw.decode().splitlines() if line.strip()]

    with get_session() as s:
        docs = {d.filename: d.id for d in s.query(Document).filter(Document.deleted.is_(False))}

    per_query = []
    latencies = []
    for row in rows:
        expected_id = docs.get(row["expected_document"])
        t0 = time.perf_counter()
        bundle = retrieve(row["query"], top_k=k)
        latencies.append((time.perf_counter() - t0) * 1000)
        flags = [ev.document_id == expected_id for ev in bundle.evidences]
        with get_session() as s:
            total_rel = (s.query(Document).get(expected_id).chunks and
                         len(s.query(Document).get(expected_id).chunks)) if expected_id else 0
        per_query.append({
            "query": row["query"],
            "expected_document": row["expected_document"],
            "found_in_top_k": any(flags),
            "precision_at_k": precision_at_k(flags, k),
            "recall_at_k": recall_at_k(flags, k, min(total_rel, k)),
            "mrr": mrr(flags),
            "ndcg_at_k": ndcg_at_k(flags, k),
            "human_review": {"reviewed": False, "reviewer_notes": ""},
        })

    n = len(per_query) or 1
    metrics = {
        "k": k,
        "queries": len(per_query),
        "precision_at_k": round(sum(q["precision_at_k"] for q in per_query) / n, 4),
        "recall_at_k": round(sum(q["recall_at_k"] for q in per_query) / n, 4),
        "mrr": round(sum(q["mrr"] for q in per_query) / n, 4),
        "ndcg_at_k": round(sum(q["ndcg_at_k"] for q in per_query) / n, 4),
        "hit_rate_at_k": round(sum(q["found_in_top_k"] for q in per_query) / n, 4),
        "mean_retrieval_latency_ms": round(sum(latencies) / n, 2),
        "note": "Document-level relevance labels; heuristic, not human-adjudicated ground truth.",
    }

    with get_session() as s:
        run = EvaluationRun(dataset_name=Path(benchmark_path).name, dataset_hash=dataset_hash,
                            config={"k": k, "retrieval": "hybrid-rrf-v1"},
                            metrics=metrics, environment=_environment())
        s.add(run)
        s.commit()
        run_id = run.id

    return {"run_id": run_id, "dataset_hash": dataset_hash,
            "metrics": metrics, "per_query": per_query, "environment": _environment()}
