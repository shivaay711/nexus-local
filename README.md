<div align="center">

# 🧠✨ NEXUS Local

## 🔐 Private • Offline-First • Local Personal AI System

### Local RAG • Full Provenance • Approval-Gated Memory • Preference Learning • Network Guard

<br>

![Offline First](https://img.shields.io/badge/Offline--First-100%25-brightgreen?style=for-the-badge)
![No Cloud APIs](https://img.shields.io/badge/Cloud%20APIs-None-blue?style=for-the-badge)
![No Telemetry](https://img.shields.io/badge/Telemetry-Disabled-red?style=for-the-badge)
![Privacy](https://img.shields.io/badge/Privacy-Local%20Only-purple?style=for-the-badge)
![Tests](https://img.shields.io/badge/Tests-48%20Passing-success?style=for-the-badge)
![Local AI](https://img.shields.io/badge/AI-Open--Weight%20Models-orange?style=for-the-badge)

<br>

> **Your files. Your memory. Your AI. Your machine.**  
> NEXUS Local is a private AI platform that runs locally with no cloud APIs, no telemetry, and no hidden data sharing.

<br>

</div>

---

## 📌 Table of Contents

- [About NEXUS Local](#-about-nexus-local)
- [Why This Project Exists](#-why-this-project-exists)
- [Simple Explanation](#-simple-explanation)
- [What This Project Is Not](#-what-this-project-is-not)
- [Core Features](#-core-features)
- [System Architecture](#-system-architecture)
- [Supported File Types](#-supported-file-types)
- [Quick Start](#-quick-start)
- [Ask a Grounded Question](#-ask-a-grounded-question)
- [Using a Real Local Model](#-using-a-real-local-model)
- [REST API](#-rest-api)
- [Memory System](#-memory-system)
- [Network Guard](#-network-guard)
- [Evaluation and Benchmarks](#-evaluation-and-benchmarks)
- [Testing](#-testing)
- [Project Structure](#-project-structure)
- [Known Limitations](#-known-limitations)
- [For Contributors](#-for-contributors)
- [Development Workflow](#-development-workflow)
- [Project Philosophy](#-project-philosophy)
- [Roadmap Ideas](#-roadmap-ideas)
- [License](#-license)

---

## 🌟 About NEXUS Local

**NEXUS Local** is a private, offline-first personal AI system that runs fully on a consumer laptop.

It is built around a local hybrid RAG pipeline, approval-gated memory, preference learning, explicit feedback, and a tested application-level Network Guard.

The goal of this project is simple:

> Build a useful personal AI system that can work with your local files while keeping your data under your control.

NEXUS Local is designed for users who want an AI assistant for their own documents, code, notes, PDFs, datasets, and knowledge base without sending sensitive data to cloud services.

---

## 🎯 Why This Project Exists

Most AI assistants depend on cloud APIs.

That creates important questions:

- Where does my data go?
- Is my data being logged?
- Is my private information used for training?
- Can I verify where the answer came from?
- Can I control what the assistant remembers?
- Can the assistant work without internet?

**NEXUS Local explores a different approach.**

It focuses on:

| Goal | Meaning |
|---|---|
| 🔐 Privacy | Data stays on your machine |
| 📚 Provenance | Answers show where they came from |
| 🧠 Controlled Memory | Nothing is remembered without approval |
| 🛡️ Offline Safety | Network Guard blocks external calls |
| 🧪 Testability | Important behavior is covered by tests |
| 🧾 Honesty | Limitations are clearly documented |

---

## 🧩 Simple Explanation

In simple words:

> **NEXUS Local is like a private ChatGPT-style assistant for your own local files.**

You can import your files and ask questions like:

```text
What does this document say about fail-open policy?
```

Then NEXUS Local:

1. Searches your local files
2. Finds relevant chunks
3. Builds an evidence bundle
4. Sends only local context to a local model adapter
5. Generates an answer with provenance
6. Refuses when local evidence is missing, if strict grounded mode is enabled

---

## 🚫 What This Project Is Not

NEXUS Local is honest about its scope.

It is **not**:

- A foundation model trained from scratch
- A replacement for proprietary frontier models
- A cloud-based AI assistant
- A guaranteed truth engine
- A hidden background trainer
- A fully finished desktop product yet

Local models can still make mistakes.

Retrieval can miss relevant information.

A local answer is only as good as:

- The files available locally
- The parsing quality
- The retrieval quality
- The model being used
- The grounding mode selected

That is why this project emphasizes **evidence, provenance, refusal behavior, and test-backed claims**.

---

## 🔥 Core Features

---

### 🔐 1. Offline-First Privacy

NEXUS Local is built around one core privacy rule:

> **Nothing leaves your machine unless you explicitly change the system design.**

Privacy-focused behavior includes:

- Runs locally
- No cloud APIs required
- No telemetry
- No external analytics
- No background data sharing
- Loopback-only API by default
- Network Guard for air-gapped mode
- Local storage using SQLite and local indexes

---

### 📥 2. Multi-Format Document Ingestion

NEXUS Local can ingest many common file formats.

Supported formats include:

| File Type | Extension | Status |
|---|---:|---|
| Markdown | `.md` | ✅ Supported |
| Text | `.txt` | ✅ Supported |
| Python | `.py` | ✅ Supported |
| CSV | `.csv` | ✅ Supported |
| JSON | `.json` | ✅ Supported |
| Jupyter Notebook | `.ipynb` | ✅ Supported |
| HTML | `.html` | ✅ Supported |
| Word Document | `.docx` | ✅ Supported |
| PDF | `.pdf` | ✅ Supported |

The ingestion pipeline includes:

- SHA-256 file hashing
- Duplicate file detection
- Parser confidence tracking
- Chunk creation
- Metadata capture
- PDF fallback parsing chain

PDF support uses:

```text
pdfplumber → pypdf
```

This means if the first PDF parser fails or gives poor output, the system can fall back to another parser.

---

### 🔎 3. Hybrid Retrieval Engine

NEXUS Local does not rely on only one search method.

It uses a **hybrid retrieval pipeline** that combines semantic-style retrieval and keyword search.

The retrieval system includes:

| Retrieval Component | Purpose |
|---|---|
| Dense retrieval | Finds approximate semantic matches |
| Local hashing embedder | Provides local embedding behavior |
| SQLite FTS5 | Provides fast full-text search |
| BM25 ranking | Improves keyword relevance |
| RRF fusion | Combines multiple rankings |
| Duplicate-context removal | Reduces repeated chunks |
| Token-budget assembly | Fits context into prompt limits |
| Latency tracking | Measures retrieval performance |

The goal is to improve retrieval reliability while keeping everything local.

---

### 📚 4. Provenance-Complete Evidence Bundles

Every answer can be connected back to its sources.

Evidence bundles may include:

| Evidence Field | Meaning |
|---|---|
| File name | Which file was used |
| Page number | Which PDF page was used |
| Chunk ID | Which text chunk was retrieved |
| Retrieval score | How relevant the chunk was |
| Embedder version | Which embedder produced the representation |
| Index version | Which search index was used |
| Prompt template version | Which answer prompt format was used |
| Stage latency | How long each retrieval stage took |

This makes answers easier to inspect, debug, and trust.

---

### 🧱 5. Strict Grounded Mode

Strict grounded mode is designed to reduce unsupported answers.

When strict grounded mode is enabled, NEXUS Local must find relevant local evidence before answering.

If no evidence is found, it refuses with:

```text
insufficient local evidence
```

This behavior is covered by tests.

The purpose is simple:

> If the system cannot support an answer using local evidence, it should not pretend that it can.

---

### 🧠 6. Approval-Gated Long-Term Memory

NEXUS Local includes a long-term memory system, but it does not silently remember everything.

The memory rule is:

> **Nothing becomes retrievable long-term memory until the user explicitly approves it.**

Memory lifecycle states include:

| State | Meaning |
|---|---|
| Proposed | Suggested memory, not yet active |
| Approved | User-approved and retrievable |
| Expired | No longer active |
| Deleted | Removed and never retrieved |

Important memory behavior:

- Proposed memories are not retrievable
- Approved memories can be retrieved
- Deleted memories are never retrieved
- Expired memories are never retrieved
- Memory behavior is controlled by a state machine

This gives the user control over what the system remembers.

---

### 🎯 7. Preference Learning

NEXUS Local can store user preferences in a validated preference profile.

Example preferences:

- Preferred tone
- Preferred answer length
- Preferred formatting
- Preferred explanation style
- Preferred technical depth
- Preferred workflow patterns

Important:

> Preferences change prompting only.  
> They do not silently train the model.

This means the system can adapt to the user without pretending to retrain itself in the background.

---

### 💬 8. Explicit Feedback Loop

Users can give feedback on answers.

For example:

- Mark an answer as helpful
- Mark an answer as wrong
- Provide a better answer
- Suggest improved wording
- Create a proposed training candidate

A better edited answer can become a **proposed training candidate**, but it still requires explicit approval.

This keeps improvement transparent and user-controlled.

---

### 📊 9. Retrieval Evaluation

NEXUS Local includes evaluation tools for measuring retrieval quality.

Supported evaluation metrics include:

| Metric | Meaning |
|---|---|
| P@K | Precision at K |
| R@K | Recall at K |
| MRR | Mean Reciprocal Rank |
| nDCG | Ranking quality |
| Latency | Speed of retrieval |

The benchmark system also captures:

- Dataset hash
- Environment details
- Retrieval configuration
- Runtime metadata
- Grounding heuristic results
- Citation heuristic results

Grounding and citation checks are clearly labeled as **heuristics**, not perfect truth guarantees.

---

### 🛡️ 10. Network Guard

NEXUS Local includes a tested application-level Network Guard.

In Air-Gapped mode, Network Guard blocks:

- Non-loopback sockets
- DNS calls
- External network attempts

It allows loopback connections such as:

```text
127.0.0.1
localhost
```

This allows local services like Ollama while blocking external calls.

Network Guard also logs blocked attempts.

This feature is verified against a live `httpx` network call.

---

### 🌐 11. Local REST API

NEXUS Local exposes a local REST API.

Default API base:

```text
http://127.0.0.1:8400/api/v1
```

OpenAPI docs:

```text
http://127.0.0.1:8400/api/v1/docs
```

The API is loopback-only by default.

---

## 🏗️ System Architecture

```text
┌────────────────────────────────────┐
│          Local User Files           │
│  md / txt / py / csv / json / pdf   │
│  ipynb / html / docx                │
└──────────────────┬─────────────────┘
                   │
                   ▼
┌────────────────────────────────────┐
│        Ingestion Pipeline           │
│  parsing + chunking + SHA-256 dedup │
│  parser confidence + metadata       │
└──────────────────┬─────────────────┘
                   │
                   ▼
┌────────────────────────────────────┐
│        Local Storage Layer          │
│  SQLite + FTS5 + local indexes      │
│  chunks + metadata + provenance     │
└──────────────────┬─────────────────┘
                   │
                   ▼
┌────────────────────────────────────┐
│        Hybrid Retrieval             │
│  dense retrieval + BM25 + RRF        │
│  duplicate removal + token budget   │
└──────────────────┬─────────────────┘
                   │
                   ▼
┌────────────────────────────────────┐
│        Evidence Bundle              │
│  file/page/chunk/scores/versions    │
└──────────────────┬─────────────────┘
                   │
                   ▼
┌────────────────────────────────────┐
│        Local LLM Adapter            │
│  mock-extractive / Ollama / GGUF    │
└──────────────────┬─────────────────┘
                   │
                   ▼
┌────────────────────────────────────┐
│        Grounded Answer              │
│  answer + citations + provenance    │
└────────────────────────────────────┘
```

---

## 📁 Supported File Types

| Category | Formats |
|---|---|
| Notes | `.md`, `.txt` |
| Code | `.py`, `.ipynb` |
| Data | `.csv`, `.json` |
| Web | `.html` |
| Documents | `.docx`, `.pdf` |

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone <repo-url>
cd nexus-local
```

### 2. Install the project

```bash
pip install -e ".[dev]"
```

### 3. Run the test suite

```bash
python -m pytest -q
```

Expected result:

```text
48 tests passing
```

### 4. Start the local API

```bash
python scripts/run_api.py
```

API runs at:

```text
http://127.0.0.1:8400
```

### 5. Import sample documents

```bash
python scripts/import_folder.py data/fixtures/documents
```

### 6. Run the retrieval benchmark

```bash
python scripts/run_benchmark.py
```

---

## 💬 Ask a Grounded Question

Example request:

```bash
curl -X POST localhost:8400/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "what does a fail-open policy do?", "strict_grounding": true}'
```

Expected behavior:

- If local evidence exists, NEXUS Local answers with citations.
- If local evidence does not exist, strict grounded mode refuses instead of guessing.

---

## 🤖 Using a Real Local Model

By default, NEXUS Local uses:

```text
mock-extractive
```

This is a deterministic extractive responder.

It is useful because:

- It runs with zero model weights
- It makes the full pipeline testable
- It gives deterministic outputs
- It avoids requiring GPU setup for basic testing

But it is **not** a neural model.

---

### Run with Ollama

To use a real local model, install Ollama and pull a small instruct model.

For RTX 4050 / RTX 4060 laptop GPUs with 6–8 GB VRAM:

```bash
ollama pull qwen2.5:3b-instruct
```

A 3B Q4 model should fit comfortably.

A 7B Q4 model may work with partial GPU offload.

Then enable Ollama runtime in your `.env` file:

```env
NEXUS_LLM_RUNTIME=ollama
```

Ollama runs on loopback, so the Network Guard permits it.

---

## 🌐 REST API

NEXUS Local exposes its API under:

```text
/api/v1
```

OpenAPI documentation:

```text
http://127.0.0.1:8400/api/v1/docs
```

Example API usage:

```bash
curl -X POST localhost:8400/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "summarize the imported documents", "strict_grounding": true}'
```

---

## 🧠 Memory System

NEXUS Local uses an approval-gated memory lifecycle.

### Memory lifecycle

```text
User Feedback / Candidate Memory
              ↓
        Proposed Memory
              ↓
      Explicit User Approval
              ↓
        Approved Memory
              ↓
   Retrieval-Eligible Memory
```

Deleted or expired memories are never retrieved.

This prevents silent long-term memory behavior.

---

## 🎯 Preference Profile

Preferences are stored separately from memory.

Preference examples:

```json
{
  "answer_style": "concise",
  "citation_style": "detailed",
  "technical_depth": "intermediate"
}
```

Preferences affect prompting only.

They do not train or fine-tune the model.

---

## 🛡️ Network Guard

Network Guard helps enforce offline-first behavior.

### In Air-Gapped mode, it blocks:

```text
External sockets
DNS calls
Non-loopback network requests
```

### It allows:

```text
localhost
127.0.0.1
local Ollama runtime
```

For stronger isolation, pair this with OS-level firewall rules.

See:

```text
docs/offline_mode.md
```

---

## 📊 Evaluation and Benchmarks

Run retrieval benchmark:

```bash
python scripts/run_benchmark.py
```

The benchmark can report:

- P@K
- R@K
- MRR
- nDCG
- Latency
- Dataset hash
- Environment capture

This makes retrieval experiments more reproducible.

---

## 🧪 Testing

Run all tests:

```bash
python -m pytest -q
```

Current verified behavior includes:

- Document ingestion
- SHA-256 deduplication
- PDF fallback parsing
- Parser confidence tracking
- Hybrid retrieval
- SQLite FTS5 search
- RRF fusion
- Duplicate context removal
- Token-budget assembly
- Evidence bundle generation
- Strict grounded refusal
- Memory approval lifecycle
- Deleted memory exclusion
- Expired memory exclusion
- Preference profile validation
- Feedback proposal flow
- Network Guard blocking behavior
- REST API behavior

---

## 📂 Project Structure

Example structure:

```text
nexus-local/
│
├── docs/
│   ├── known_limitations.md
│   └── offline_mode.md
│
├── scripts/
│   ├── run_api.py
│   ├── import_folder.py
│   └── run_benchmark.py
│
├── data/
│   └── fixtures/
│       └── documents/
│
├── tests/
│   └── ...
│
├── README.md
├── pyproject.toml
└── ...
```

---

## ⚠️ Known Limitations

NEXUS Local is useful, but it is still a local AI system with practical limits.

Current limitations:

| Limitation | Explanation |
|---|---|
| Hashing embedder | Default embedder is weaker than neural embeddings |
| Sentence-transformers adapter | Exists but is not verified in this build environment |
| Ollama adapter | Included but not verified here with GPU weights |
| No frontend yet | Current focus is backend and API |
| No desktop app yet | Can be added later |
| LoRA training lab | Not implemented deliberately |
| Network Guard scope | Process-level protection, not full OS isolation |
| Retrieval limitations | Retrieval may miss relevant context |
| Local model limitations | Small local models can hallucinate |

More details:

```text
docs/known_limitations.md
docs/offline_mode.md
```

---

## 🛠️ For Contributors

NEXUS Local is designed to be easy to understand, test, and extend.

Good contribution areas:

| Area | Contribution Ideas |
|---|---|
| Frontend | Add web UI, desktop UI, chat interface |
| Retrieval | Improve ranking, filtering, chunking |
| Embeddings | Add stronger local embedding adapters |
| Memory | Improve approval UI and lifecycle tests |
| Security | Add OS firewall setup guides |
| Docs | Add tutorials, diagrams, examples |
| Evaluation | Add more benchmark datasets |
| API | Improve endpoint documentation |
| Models | Improve Ollama/GGUF support |
| Packaging | Improve offline installation flow |

---

## 🧑‍💻 Development Workflow

```bash
git clone <repo-url>
cd nexus-local

pip install -e ".[dev]"
python -m pytest -q
python scripts/run_api.py
```

Before opening a pull request:

```bash
python -m pytest -q
```

Please keep contributions:

- Honest
- Tested
- Documented
- Easy to review
- Clear about limitations

Do not claim a feature is verified unless it is covered by tests or clearly marked as experimental.

---

## ✅ Pull Request Checklist

Before submitting a PR, please check:

- [ ] Tests pass locally
- [ ] New behavior is documented
- [ ] Limitations are clearly stated
- [ ] No cloud dependency is introduced silently
- [ ] Privacy behavior is not weakened
- [ ] Network behavior is explained
- [ ] New features are marked verified only if tested

---

## 🧭 Project Philosophy

NEXUS Local follows five principles:

| Principle | Meaning |
|---|---|
| 🏠 Local First | User data should stay on the machine |
| 📚 Evidence First | Answers should show sources |
| ✅ Approval First | Memory should never be silent |
| 🧾 Honesty First | Limitations should be visible |
| 🧪 Test First | Important behavior should be verified |

---

## 🗺️ Roadmap Ideas

Possible future improvements:

- [ ] Web dashboard
- [ ] Desktop app
- [ ] Better document preview
- [ ] Memory approval UI
- [ ] Stronger local embedding models
- [ ] Better chunk visualization
- [ ] Advanced citation viewer
- [ ] Local model comparison tools
- [ ] Offline installer
- [ ] OS-level firewall guide
- [ ] More retrieval benchmark datasets
- [ ] More examples and tutorials

---

## 📌 Project Status

NEXUS Local currently provides:

- Working local RAG backend
- Multi-format ingestion
- Hybrid retrieval
- Provenance tracking
- Approval-gated memory lifecycle
- Preference profile support
- Feedback proposal flow
- Retrieval evaluation
- Network Guard
- Local REST API
- Test-backed behavior

It is ready for experimentation, contribution, and extension into a full local personal AI application.

---

## ⭐ Why This Project Matters

Most AI tools rely on cloud APIs and unclear data flows.

NEXUS Local explores a different path:

> **A personal AI system that is private, inspectable, offline-first, and controlled by the user.**

This project is for builders who care about:

- Local AI
- Privacy
- Open-source AI systems
- Transparent retrieval
- Trustworthy personal memory
- Offline-first software
- Test-backed engineering

---

<div align="center">

# 🧠 NEXUS Local

### Private AI. Local Knowledge. User-Controlled Memory.

<br>

**If this project helps you, consider giving it a ⭐ on GitHub.**

<br>

Made for developers who believe personal AI should be private, transparent, and user-controlled.

</div>
