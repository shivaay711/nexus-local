# Decision Log

- **2026-07-05 · Single installable package, bounded-context subpackages.**
  The spec's 14-package monorepo adds packaging overhead with no benefit at
  this scale. `nexus_local.{security,ingestion,retrieval,llm,memory,
  preferences,feedback,evaluation,api}` preserves the bounded contexts with
  one `pip install -e .`.
- **2026-07-05 · Hashing embedder as tested default.** A neural embedder
  requires downloading weights, which contradicts a reproducible air-gapped
  test suite. Feature-hashed TF-IDF + BM25 + RRF is fully offline and
  deterministic; the neural adapter is a drop-in upgrade.
- **2026-07-05 · Flat numpy dense index.** Personal corpora are small; exact
  cosine over a memory-mapped matrix beats ANN complexity below ~100k chunks.
  Interface allows a FAISS/LanceDB backend later.
- **2026-07-05 · MockAdapter ships and is honest.** An extractive deterministic
  responder makes the whole system testable with zero weights, and every
  response labels the adapter name.
- **2026-07-05 · Training Lab deferred, approval gate built.** No GPU in the
  build environment means training could not be verified; shipping unrunnable
  training code violates the project's own truthfulness rules. The explicit
  approval pathway (training_example memories) is built and tested so the lab
  can consume it.
- **2026-07-05 · Removed `from __future__ import annotations` in api/app.py.**
  PEP 563 string annotations break FastAPI's resolution of function-local
  Pydantic models (they get misclassified as query params). Found via test.
