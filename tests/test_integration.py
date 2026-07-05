"""Integration tests: full pipelines over the real fixture corpus."""
import pytest
from fastapi.testclient import TestClient

from nexus_local.llm.orchestrator import INSUFFICIENT, MockAdapter, answer, chat_turn
from nexus_local.retrieval.hybrid import retrieve
from nexus_local.memory import service as mem
from tests.conftest import BENCHMARK, FIXTURES


class TestHybridRetrieval:
    def test_retrieves_correct_document_for_topical_query(self, corpus):
        b = retrieve("how does token bucket handle bursts", top_k=5)
        assert b.evidences, "no evidence retrieved"
        assert b.evidences[0].source_file == "distributed_rate_limiting.md"

    def test_pdf_page_provenance_in_evidence(self, corpus):
        b = retrieve("reciprocal rank fusion formula", top_k=5)
        pdf_hits = [e for e in b.evidences if e.source_file == "vector_search_primer.pdf"]
        assert pdf_hits and pdf_hits[0].page == 2

    def test_evidence_bundle_completeness(self, corpus):
        b = retrieve("Grad-CAM heatmaps solar defect", top_k=3)
        ev = b.evidences[0]
        for field in ("chunk_id", "document_id", "source_path", "excerpt",
                      "embedding_model"):
            assert getattr(ev, field)
        assert b.prompt_template_version and b.index_version
        assert set(b.stage_latency_ms) == {"dense", "bm25", "fusion", "assembly"}

    def test_stage_scores_present(self, corpus):
        b = retrieve("sliding window counter memory", top_k=5)
        assert any(e.bm25_score is not None for e in b.evidences)
        assert any(e.dense_score is not None for e in b.evidences)

    def test_document_filter(self, corpus):
        target = corpus["solar_cell_defects.txt"].id
        b = retrieve("temperature scaling confidence", document_ids=[target])
        assert all(e.document_id == target for e in b.evidences)

    def test_deleted_document_excluded(self, corpus):
        from nexus_local.ingestion.pipeline import delete_document
        delete_document(corpus["ipl_batting.csv"].id)
        b = retrieve("highest strike rate batsman", top_k=8)
        assert all(e.source_file != "ipl_batting.csv" for e in b.evidences)


class TestOrchestration:
    def test_grounded_answer_from_local_sources(self, corpus):
        r = answer("How does the token bucket algorithm handle bursts?",
                   strict_grounding=True, adapter=MockAdapter())
        assert r.answer_source in ("local_sources", "mixed")
        assert "burst" in r.answer.lower()
        assert r.evidence_bundle["evidences"]

    def test_strict_grounding_refuses_without_evidence(self, workspace):
        # empty corpus -> must refuse, never invent
        r = answer("What is the capital of France?", strict_grounding=True,
                   adapter=MockAdapter())
        assert r.answer == INSUFFICIENT
        assert r.answer_source == "insufficient_evidence"

    def test_memory_influences_answer_source(self, corpus):
        m = mem.propose_memory("User prefers answers that mention Go", "preference")
        mem.approve_memory(m.id)
        r = answer("token bucket bursts", adapter=MockAdapter())
        assert m.id in r.applied_memory_ids
        assert r.answer_source == "mixed"

    def test_chat_turn_persists_messages(self, corpus):
        from nexus_local.db import get_session
        from nexus_local.models import Conversation, Message
        with get_session() as s:
            c = Conversation(title="t", strict_grounding=True)
            s.add(c)
            s.commit()
            cid = c.id
        chat_turn(cid, "sliding window log memory usage?")
        with get_session() as s:
            msgs = s.query(Message).filter_by(conversation_id=cid).all()
        assert [m.role for m in msgs] == ["user", "assistant"]
        assert msgs[1].evidence_bundle is not None


class TestAPI:
    @pytest.fixture()
    def client(self, workspace):
        from nexus_local.api.app import create_app
        # workspace fixture already ran init_db; app reuses it
        app = create_app(db_path=workspace / "nexus.db")
        return TestClient(app)

    def test_health_and_guard_status(self, client):
        assert client.get("/api/v1/health").json()["status"] == "ok"
        g = client.get("/api/v1/security/network-guard").json()
        assert "enabled" in g and "blocked_count" in g

    def test_full_flow_import_search_ask_memory_feedback(self, client, workspace):
        import shutil
        src = FIXTURES / "distributed_rate_limiting.md"
        dst = workspace / "documents" / src.name
        shutil.copy(src, dst)

        r = client.post("/api/v1/documents/import", json={"path": str(dst)})
        assert r.status_code == 201 and r.json()["chunks_embedded"] > 0

        s = client.get("/api/v1/search", params={"q": "fail-open policy redis"}).json()
        assert s["evidences"]

        conv = client.post("/api/v1/conversations",
                           json={"title": "x", "strict_grounding": True}).json()
        msg = client.post(f"/api/v1/conversations/{conv['id']}/messages",
                          json={"content": "what does a fail-open policy do?"}).json()
        assert msg["answer_source"] in ("local_sources", "mixed")

        m = client.post("/api/v1/memories/propose",
                        json={"content": "User builds Throttle in Go",
                              "memory_type": "project"}).json()
        assert m["state"] == "proposed"
        assert client.post(f"/api/v1/memories/{m['id']}/approve").json()["state"] == "active"
        assert client.get(f"/api/v1/memories/{m['id']}/why").json()["approved"] is True
        assert client.delete(f"/api/v1/memories/{m['id']}").status_code == 204
        assert client.get("/api/v1/memories", params={"state": "active"}).json() == []

        msgs = client.get(f"/api/v1/conversations/{conv['id']}/messages").json()
        fb = client.post("/api/v1/feedback",
                         json={"message_id": msgs[1]["id"], "kind": "helpful"})
        assert fb.status_code == 201

        audit = client.get("/api/v1/audit-log").json()
        assert any(a["action"] == "import" for a in audit)

    def test_invalid_import_rejected(self, client, workspace):
        bad = workspace / "documents" / "x.exe"
        bad.write_bytes(b"MZ")
        assert client.post("/api/v1/documents/import",
                           json={"path": str(bad)}).status_code == 422

    def test_preference_validation_via_api(self, client):
        assert client.put("/api/v1/preferences",
                          json={"key": "tone", "value": "casual"}).status_code == 200
        assert client.put("/api/v1/preferences",
                          json={"key": "tone", "value": "rude"}).status_code == 422

    def test_training_nomination_requires_approval(self, client, workspace, corpus):
        conv = client.post("/api/v1/conversations", json={"title": "t"}).json()
        client.post(f"/api/v1/conversations/{conv['id']}/messages",
                    json={"content": "token bucket?"})
        msgs = client.get(f"/api/v1/conversations/{conv['id']}/messages").json()
        r = client.post("/api/v1/training-examples/nominate",
                        json={"message_id": msgs[1]["id"],
                              "corrected_answer": "Better answer text"}).json()
        assert r["state"] == "proposed"  # unusable until explicit approval
        pending = client.get("/api/v1/memories", params={"state": "proposed"}).json()
        assert any(p["id"] == r["memory_id"] for p in pending)


class TestBenchmark:
    def test_retrieval_benchmark_runs_and_records(self, corpus):
        from nexus_local.evaluation.retrieval_eval import run_retrieval_benchmark
        report = run_retrieval_benchmark(BENCHMARK, k=5)
        m = report["metrics"]
        assert m["queries"] == 8
        assert 0.0 <= m["mrr"] <= 1.0
        assert m["hit_rate_at_k"] >= 0.75, f"retrieval quality regressed: {m}"
        assert report["dataset_hash"]
        from nexus_local.db import get_session
        from nexus_local.models import EvaluationRun
        with get_session() as s:
            assert s.query(EvaluationRun).count() == 1


class TestOnlineMode:
    def test_mode_toggle_flips_guard(self, workspace):
        from nexus_local.llm.runtime_mode import set_online, is_online
        from nexus_local.security.network_guard import guard
        try:
            st = set_online(True)
            assert st["online"] is True and guard.enabled is False and is_online()
            st = set_online(False)
            assert st["online"] is False and guard.enabled is True
        finally:
            set_online(False)
            guard.disable()  # leave test env clean

    def test_web_parser_extracts_results(self):
        from nexus_local.retrieval.web_search import parse_duckduckgo_html
        page = ('<a rel="nofollow" class="result__a" href="/l/?uddg=https%3A%2F%2Fexample.com%2Fa">'
                'Example <b>Title</b></a> junk '
                '<a class="result__snippet" href="#">A useful &amp; short snippet</a>')
        rs = parse_duckduckgo_html(page)
        assert rs[0].title == "Example Title"
        assert rs[0].url == "https://example.com/a"
        assert rs[0].snippet == "A useful & short snippet"

    def test_auto_memory_proposes_not_activates(self, workspace):
        from nexus_local.llm.runtime_mode import propose_memories_from_text
        from nexus_local.memory.service import retrieve_active_memories
        ids = propose_memories_from_text("hi, my name is Ritik and I prefer Go for backends")
        assert len(ids) == 2
        assert retrieve_active_memories("Ritik Go backend") == []  # still needs approval

    def test_history_reaches_model(self, workspace):
        from nexus_local.db import get_session
        from nexus_local.models import Conversation
        from nexus_local.llm.orchestrator import chat_turn, LLMAdapter

        captured = {}
        class Spy(LLMAdapter):
            name = "spy"
            def generate(self, system, prompt, max_tokens=512):
                captured["prompt"] = prompt
                return "ok"
        import nexus_local.llm.orchestrator as orch
        orig = orch.get_adapter
        orch.get_adapter = lambda: Spy()
        try:
            with get_session() as s:
                c = Conversation(title="Untitled")
                s.add(c)
                s.commit()
                cid = c.id
            chat_turn(cid, "my dog is called Bruno")
            chat_turn(cid, "what is my dog called?")
            assert "CONVERSATION SO FAR" in captured["prompt"]
            assert "Bruno" in captured["prompt"]
        finally:
            orch.get_adapter = orig


class TestFreeChatGate:
    def test_greeting_does_not_pull_junk_evidence(self, corpus):
        r = answer("hi", strict_grounding=False, adapter=MockAdapter())
        assert r.evidence_bundle["evidences"] == []
        assert r.answer_source in ("base_model", "approved_memory")

    def test_topical_query_still_grounds_in_free_mode(self, corpus):
        r = answer("how does the token bucket handle bursts?",
                   strict_grounding=False, adapter=MockAdapter())
        assert r.answer_source in ("local_sources", "mixed")
        assert len(r.evidence_bundle["evidences"]) > 0
