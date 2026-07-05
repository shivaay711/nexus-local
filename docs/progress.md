# Progress

2026-07-05 — Initial verified build. 48/48 tests pass. Live smoke test of the
API (import → grounded ask → guard status) executed. Network Guard verified
against a live httpx call to a remote endpoint. Retrieval benchmark executed
on the demo corpus: MRR 1.0, hit_rate@5 1.0, P@5 0.25, ~4.7 ms mean retrieval
latency (small-corpus fixture; see known_limitations.md §3).

2026-07-05 (v0.2) — ChatGPT-style upgrade: conversation history now reaches
the model (verified by spy-adapter test), free-chat persona, Online/Offline
runtime toggle (flips Network Guard, audited), DuckDuckGo web search in
Online mode (parser unit-tested; live site unverified in build env),
auto-proposed memories from self-disclosures (approval gate intact, tested),
conversation list/delete endpoints, rebuilt web UI (sidebar + chat + memory
banner + mode pill). 52/52 tests passing; live API smoke of new endpoints
executed.
