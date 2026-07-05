# Roadmap

**Done (verified):** Phases 0–5 core — config, DB, Network Guard, ingestion,
hybrid RAG + evidence bundles + strict grounding, memory lifecycle,
preferences, feedback, retrieval evaluation, REST API, 48-test suite.

**Next:**
1. Ollama runtime verification on real hardware (RTX 4060) + streaming.
2. sentence-transformers embedder verification with a locally imported bundle
   (e.g. bge-small-en-v1.5) + re-run benchmark for honest A/B numbers.
3. React dashboard (chat, retrieval inspector, memory center) → Tauri shell.
4. Reranker adapter (local cross-encoder) behind the existing interface.
5. Training Lab: dataset curation UI, hardware checks, QLoRA runner, base-vs-
   adapter evaluation — only with verified GPU training.
6. Encrypted workspace option; desktop-session token auth; backup/restore.
