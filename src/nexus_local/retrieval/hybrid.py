"""Hybrid retrieval: dense cosine search + SQLite FTS5 BM25, fused with
Reciprocal Rank Fusion, assembled into provenance-complete evidence bundles
under a character-approximated token budget."""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from sqlalchemy import select, text as sqltext

from ..config import settings
from ..db import get_session
from ..models import Chunk, Document
from .embedder import Embedder, get_default_embedder, tokenize

PROMPT_TEMPLATE_VERSION = "grounded-v1"
INDEX_VERSION = "v1"


# ------------------------------------------------------------- dense index
class DenseIndex:
    """Flat cosine index persisted as .npz — appropriate for personal-scale
    corpora (up to ~100k chunks). An ANN backend (FAISS/LanceDB) slots in
    behind the same interface when corpora grow."""

    def __init__(self, path: Path):
        self.path = path
        self.ids: list[str] = []
        self.matrix: np.ndarray | None = None
        if path.exists():
            data = np.load(path, allow_pickle=False)
            self.ids = [i.decode() if isinstance(i, bytes) else str(i) for i in data["ids"]]
            self.matrix = data["vectors"]

    def add(self, ids: list[str], vectors: np.ndarray) -> None:
        self.ids.extend(ids)
        self.matrix = vectors if self.matrix is None else np.vstack([self.matrix, vectors])
        self.save()

    def remove(self, drop: set[str]) -> None:
        if self.matrix is None:
            return
        keep = [i for i, cid in enumerate(self.ids) if cid not in drop]
        self.ids = [self.ids[i] for i in keep]
        self.matrix = self.matrix[keep] if keep else None
        self.save()

    def save(self) -> None:
        if self.matrix is None:
            if self.path.exists():
                self.path.unlink()
            return
        np.savez(self.path, ids=np.array(self.ids), vectors=self.matrix)

    def search(self, query_vec: np.ndarray, k: int) -> list[tuple[str, float]]:
        if self.matrix is None or not len(self.ids):
            return []
        scores = self.matrix @ query_vec.reshape(-1)
        order = np.argsort(-scores)[:k]
        return [(self.ids[i], float(scores[i])) for i in order]


def _index_path() -> Path:
    return settings.workspace_dir / "indexes" / "dense.npz"


def embed_pending_chunks(embedder: Embedder | None = None) -> int:
    """Embed all chunks not yet in the dense index. Returns count embedded."""
    embedder = embedder or get_default_embedder()
    index = DenseIndex(_index_path())
    have = set(index.ids)
    with get_session() as s:
        rows = s.execute(
            select(Chunk).join(Document).where(Document.deleted.is_(False))
        ).scalars().all()
        pending = [c for c in rows if c.id not in have]
        if not pending:
            return 0
        vectors = embedder.embed([c.text for c in pending])
        index.add([c.id for c in pending], vectors)
        for c in pending:
            c.embedding_model = embedder.name
        s.commit()
    return len(pending)


# --------------------------------------------------------------- BM25 side
def bm25_search(query: str, k: int) -> list[tuple[str, float]]:
    toks = tokenize(query)
    if not toks:
        return []
    match = " OR ".join(f'"{t}"' for t in toks)
    with get_session() as s:
        rows = s.execute(sqltext(
            "SELECT chunk_id, bm25(chunk_fts) AS score FROM chunk_fts "
            "WHERE chunk_fts MATCH :q ORDER BY score LIMIT :k"),
            {"q": match, "k": k}).all()
    # FTS5 bm25() returns lower-is-better; negate so higher is better.
    return [(r.chunk_id, -float(r.score)) for r in rows]


# ------------------------------------------------------------------ fusion
def rrf_fuse(rankings: list[list[tuple[str, float]]], k: int | None = None) -> list[tuple[str, float]]:
    k = k or settings.rrf_k
    fused: dict[str, float] = {}
    for ranking in rankings:
        for rank, (cid, _) in enumerate(ranking, 1):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (k + rank)
    return sorted(fused.items(), key=lambda x: -x[1])


# --------------------------------------------------------- evidence bundle
@dataclass
class Evidence:
    chunk_id: str
    document_id: str
    source_file: str
    source_path: str
    page: int | None
    heading: str | None
    excerpt: str
    retrieval_score: float
    dense_score: float | None
    bm25_score: float | None
    embedding_model: str


@dataclass
class EvidenceBundle:
    query: str
    evidences: list[Evidence] = field(default_factory=list)
    created_at: str = ""
    index_version: str = INDEX_VERSION
    prompt_template_version: str = PROMPT_TEMPLATE_VERSION
    stage_latency_ms: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return json.loads(json.dumps(self, default=lambda o: o.__dict__))


def retrieve(query: str, top_k: int | None = None,
             embedder: Embedder | None = None,
             document_ids: list[str] | None = None) -> EvidenceBundle:
    """Hybrid retrieve with per-stage latency, dedup, filtering, and a
    context budget. Returns a complete evidence bundle."""
    import time
    top_k = top_k or settings.retrieval_top_k
    embedder = embedder or get_default_embedder()
    bundle = EvidenceBundle(query=query,
                            created_at=dt.datetime.now(dt.timezone.utc).isoformat())

    t0 = time.perf_counter()
    qvec = embedder.embed([query])[0]
    dense = DenseIndex(_index_path()).search(qvec, top_k * 3)
    bundle.stage_latency_ms["dense"] = round((time.perf_counter() - t0) * 1000, 2)

    t0 = time.perf_counter()
    lexical = bm25_search(query, top_k * 3)
    bundle.stage_latency_ms["bm25"] = round((time.perf_counter() - t0) * 1000, 2)

    t0 = time.perf_counter()
    fused = rrf_fuse([dense, lexical])
    bundle.stage_latency_ms["fusion"] = round((time.perf_counter() - t0) * 1000, 2)

    dense_scores = dict(dense)
    bm25_scores = dict(lexical)

    t0 = time.perf_counter()
    budget = settings.context_token_budget * 4  # ~4 chars/token approximation
    used = 0
    seen_texts: set[str] = set()
    with get_session() as s:
        for cid, score in fused:
            if len(bundle.evidences) >= top_k:
                break
            ch = s.get(Chunk, cid)
            if ch is None:
                continue
            doc = s.get(Document, ch.document_id)
            if doc is None or doc.deleted:
                continue
            if document_ids and doc.id not in document_ids:
                continue
            fingerprint = ch.text[:120]
            if fingerprint in seen_texts:  # duplicate-context removal
                continue
            if used + len(ch.text) > budget:
                continue
            seen_texts.add(fingerprint)
            used += len(ch.text)
            bundle.evidences.append(Evidence(
                chunk_id=cid, document_id=doc.id, source_file=doc.filename,
                source_path=doc.path, page=ch.page, heading=ch.heading,
                excerpt=ch.text, retrieval_score=score,
                dense_score=dense_scores.get(cid), bm25_score=bm25_scores.get(cid),
                embedding_model=ch.embedding_model or embedder.name,
            ))
    bundle.stage_latency_ms["assembly"] = round((time.perf_counter() - t0) * 1000, 2)
    return bundle
