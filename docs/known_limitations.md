# Known Limitations (honest, current)

1. **Default embedder is lexical-statistical.** The hashing embedder (feature-
   hashed TF-IDF with bigrams) is deterministic and fully offline but weaker
   than a neural embedder for paraphrase-heavy queries. Hybrid fusion with BM25
   mitigates this. `SentenceTransformerEmbedder` is implemented as a drop-in
   but was NOT verified in the build environment (no local model bundle).
2. **Ollama adapter unverified.** Code exists and follows the documented local
   API, but the build environment had no GPU, Ollama runtime, or weights. The
   shipped, tested adapter is the clearly-labeled `mock-extractive`.
3. **Benchmark scale.** The retrieval benchmark (8 queries, 6 documents) is a
   correctness fixture, not a research-grade benchmark. hit_rate@5 = 1.0 and
   MRR = 1.0 on this corpus indicate the pipeline works, not that it
   generalizes. Relevance labels are document-level.
4. **No frontend / desktop app.** The REST API is the product surface today.
   A React dashboard and Tauri shell are roadmap items, not stub folders.
5. **Training Lab not implemented.** QLoRA/LoRA training was intentionally not
   built rather than shipped unverifiable: the build environment has no GPU
   and training code could not be run honestly. The approval gate that a
   future lab must consume exists (training_example memories require explicit
   approval; verified by test).
6. **Network Guard is process-level.** It patches Python sockets in the app
   process. Child processes and non-Python native code are not constrained.
   docs/offline_mode.md shows Windows Firewall rules for hard enforcement.
7. **PDF extraction is imperfect.** Scanned PDFs yield no text (no OCR
   configured); parser confidence and errors are recorded per document.
8. **Grounding evaluation is heuristic.** Token-overlap faithfulness is a
   proxy, labeled as such, with human-review fields in every report.
9. **Single-user, loopback-only.** No auth layer yet beyond binding to
   127.0.0.1; a desktop-session token is the planned mechanism.

## v0.2 additions (2026-07-05)
10. **Web search (Online mode) parser is unit-tested but NOT verified against
    the live DuckDuckGo site** — the build environment has no egress to it.
    Failure mode is safe: returns no results rather than erroring. Verify on
    real hardware by toggling Online and asking a current-events question.
11. **Auto-memory heuristics are regex-based** ("my name is", "I prefer", "I
    work at"...). They only propose; approval remains explicit. They will miss
    indirect self-disclosures — that's the conservative choice.
12. **Online mode disables the Network Guard for the whole process** while
    active. The app always boots offline; online never persists across
    restarts. Mode changes are written to the audit log.
