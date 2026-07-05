# NEXUS Local — Web Interface

A local-first React dashboard for the NEXUS Local backend: grounded chat with
source citations, a retrieval inspector (per-stage latency + dense/BM25/RRF
scores per chunk), an approval-gated memory center, and a document library.
Everything talks to your local API on 127.0.0.1 — nothing leaves the machine.

## Prerequisites
- The NEXUS backend running: `python scripts/run_api.py` (serves on :8400)
- Node.js 18+ (you have v22)

## Run (development)
```bash
npm install
npm run dev
```
Open http://localhost:5173. The dev server proxies `/api` → `127.0.0.1:8400`,
so the backend must be running in another terminal.

## What each screen does
- **Chat** — ask questions; toggle strict grounding and memory. Answers show a
  source label (grounded / insufficient evidence / memory), inline citations,
  and a "Why this answer?" link that opens the retrieval inspector.
- **Retrieval inspector** (drawer) — per-stage latency (dense, bm25, fusion,
  assembly) and every retrieved chunk with its RRF / dense / BM25 scores,
  file, and page. This is the provenance view.
- **Memory** — propose a memory, approve/reject it, delete it. Only *active*
  memories are ever used; the UI mirrors the backend state machine.
- **Documents** — everything indexed, with parser and confidence.

## Build for production
```bash
npm run build      # outputs to dist/
npm run preview    # serve the built app locally
```

## Notes
- The left-rail status dots poll `/api/v1/health` every 8s. If the backend is
  down they go grey — start `run_api.py` and they recover automatically.
- No data is stored in the browser; it's a thin client over the local API.
