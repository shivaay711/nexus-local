# Architecture Overview

```mermaid
flowchart LR
    subgraph Local Machine
        UI[REST clients / future dashboard] --> API[FastAPI /api/v1]
        API --> ING[Ingestion\nparse->hash->chunk]
        API --> RET[Hybrid Retrieval\ndense + BM25 + RRF]
        API --> ORC[Chat Orchestrator]
        API --> MEM[Memory Lifecycle]
        API --> PREF[Preferences]
        API --> FB[Feedback]
        API --> EVAL[Evaluation]
        ORC --> RET
        ORC --> MEM
        ORC --> PREF
        ORC --> LLM[LLM Adapter\nmock | ollama loopback]
        ING --> DB[(SQLite + FTS5)]
        RET --> DB
        RET --> VIX[(Dense index .npz)]
        MEM --> DB
        NG[Network Guard\nsocket + DNS patch] -. blocks .-> WAN((Internet))
    end
```

## Memory lifecycle
```mermaid
stateDiagram-v2
    [*] --> proposed
    proposed --> approved: user approves
    proposed --> rejected: user rejects
    approved --> active
    active --> expiring: expiry reached
    active --> archived
    active --> deleted
    expiring --> active: renewed
    archived --> active
    archived --> deleted
    rejected --> deleted
```
Invariant (test-enforced): only `active` memories are retrievable.

## RAG pipeline
```mermaid
flowchart LR
    Q[query] --> E[embed query]
    Q --> B[FTS5 BM25]
    E --> D[dense cosine top-3k]
    D --> F[RRF fusion]
    B --> F
    F --> A[budgeted assembly\ndedup + filters]
    A --> EB[Evidence bundle\nfile/page/chunk provenance,\nscores, versions, latency]
    EB --> LLMp[grounded prompt]
```

## ER diagram (core)
```mermaid
erDiagram
    DOCUMENT ||--o{ CHUNK : has
    CONVERSATION ||--o{ MESSAGE : has
    MESSAGE ||--o{ FEEDBACK : receives
    MEMORY }o--|| CONVERSATION : "sourced from"
    EVALUATION_RUN
    AUDIT_LOG
    SECURITY_EVENT
    PREFERENCE
```
