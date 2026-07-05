"""Local embedding adapters.

Default: HashingEmbedder — a deterministic feature-hashed TF-IDF-style
embedder. Zero downloads, fully air-gapped, fast on CPU. It is honestly
weaker semantically than a neural embedder; hybrid fusion with BM25
compensates for exact-term queries, and the SentenceTransformerEmbedder
adapter is a drop-in upgrade once a local model bundle is imported.
"""
from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod

import numpy as np

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class Embedder(ABC):
    name: str = "abstract"
    dim: int = 0

    @abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray: ...


class HashingEmbedder(Embedder):
    """Feature hashing with unigrams + bigrams, log-TF weighting, L2 norm."""

    def __init__(self, dim: int = 1024):
        self.dim = dim
        self.name = f"hashing-v1-d{dim}"

    def _bucket(self, token: str) -> tuple[int, float]:
        h = hashlib.blake2b(token.encode(), digest_size=8).digest()
        idx = int.from_bytes(h[:4], "little") % self.dim
        sign = 1.0 if h[4] & 1 else -1.0
        return idx, sign

    def embed(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            toks = tokenize(text)
            grams = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
            counts: dict[str, int] = {}
            for g in grams:
                counts[g] = counts.get(g, 0) + 1
            for g, c in counts.items():
                idx, sign = self._bucket(g)
                out[row, idx] += sign * (1.0 + math.log(c))
            norm = np.linalg.norm(out[row])
            if norm > 0:
                out[row] /= norm
        return out


class SentenceTransformerEmbedder(Embedder):
    """Adapter for a locally stored sentence-transformers model directory.
    NOT VERIFIED in the build environment (no model weights available);
    the interface is exercised by tests through HashingEmbedder."""

    def __init__(self, model_path: str):
        from sentence_transformers import SentenceTransformer  # local import
        self.model = SentenceTransformer(model_path, device="cpu")
        self.dim = self.model.get_sentence_embedding_dimension()
        self.name = f"st:{model_path}"

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self.model.encode(texts, normalize_embeddings=True), dtype=np.float32)


def get_default_embedder() -> Embedder:
    from ..config import settings
    if settings.embedder == "hashing":
        return HashingEmbedder()
    raise ValueError(f"Embedder '{settings.embedder}' requires a local model path; "
                     "configure via the model manager API.")
