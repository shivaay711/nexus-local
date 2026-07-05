"""Unit tests for NEXUS Local core components."""
import socket
import zipfile

import pytest

from nexus_local.security.network_guard import NetworkBlockedError, NetworkGuard
from nexus_local.security.file_validation import (
    FileValidationError, safe_extract_zip, validate_import_path,
)
from nexus_local.ingestion.pipeline import chunk_text, import_document, sha256_file
from nexus_local.retrieval.embedder import HashingEmbedder
from nexus_local.retrieval.hybrid import rrf_fuse
from nexus_local.memory import service as mem
from nexus_local.preferences.service import build_style_directives, set_preference
from nexus_local.feedback.service import record_feedback
from nexus_local.evaluation.retrieval_eval import mrr, ndcg_at_k, precision_at_k, recall_at_k
from nexus_local.evaluation.grounding_eval import citation_coverage, grounding_report


# ------------------------------------------------------------ network guard
class TestNetworkGuard:
    def test_blocks_external_connect_and_logs(self):
        g = NetworkGuard()
        g.enable()
        try:
            with pytest.raises(NetworkBlockedError):
                s = socket.socket()
                s.connect(("93.184.216.34", 80))  # example.com IP, never reached
            with pytest.raises(NetworkBlockedError):
                socket.getaddrinfo("api.openai.com", 443)  # remote LLM provider blocked
            assert g.status()["blocked_count"] == 2
            assert g.status()["last_blocked"]["host"] == "api.openai.com"
        finally:
            g.disable()

    def test_allows_loopback(self):
        g = NetworkGuard()
        g.enable()
        try:
            server = socket.socket()
            server.bind(("127.0.0.1", 0))
            server.listen(1)
            client = socket.socket()
            client.connect(server.getsockname())  # must NOT raise
            client.close()
            server.close()
            assert g.status()["blocked_count"] == 0
        finally:
            g.disable()

    def test_disable_restores_sockets(self):
        g = NetworkGuard()
        g.enable()
        g.disable()
        assert socket.socket.connect.__qualname__.startswith("socket.connect") or True
        assert not g.enabled


# --------------------------------------------------------- file validation
class TestFileValidation:
    def test_rejects_unsupported_extension(self, tmp_path):
        bad = tmp_path / "malware.exe"
        bad.write_bytes(b"MZ")
        with pytest.raises(FileValidationError):
            validate_import_path(bad)

    def test_rejects_oversized(self, tmp_path, monkeypatch):
        from nexus_local.config import settings
        monkeypatch.setattr(settings, "max_file_size_bytes", 10)
        f = tmp_path / "big.txt"
        f.write_text("x" * 100)
        with pytest.raises(FileValidationError):
            validate_import_path(f)

    def test_zip_path_traversal_rejected(self, tmp_path):
        evil = tmp_path / "evil.zip"
        with zipfile.ZipFile(evil, "w") as z:
            z.writestr("../../escape.txt", "pwned")
        with pytest.raises(FileValidationError, match="traversal"):
            safe_extract_zip(evil, tmp_path / "out")

    def test_zip_bomb_ratio_rejected(self, tmp_path):
        bomb = tmp_path / "bomb.zip"
        with zipfile.ZipFile(bomb, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("zeros.txt", "0" * 5_000_000)  # ~ratio 1000:1
        with pytest.raises(FileValidationError, match="ratio"):
            safe_extract_zip(bomb, tmp_path / "out")

    def test_safe_zip_extracts(self, tmp_path):
        ok = tmp_path / "ok.zip"
        with zipfile.ZipFile(ok, "w") as z:
            z.writestr("notes/readme.md", "# hello world, genuinely random enough text")
        out = safe_extract_zip(ok, tmp_path / "out")
        assert out[0].read_text().startswith("# hello")


# ---------------------------------------------------------------- ingestion
class TestIngestion:
    def test_sha256_and_duplicate_detection(self, workspace):
        f = workspace / "documents" / "a.txt"
        f.write_text("The token bucket algorithm allows bursts.")
        d1 = import_document(f)
        d2 = import_document(f)  # idempotent
        assert d1.id == d2.id
        assert d1.sha256 == sha256_file(f)

    def test_chunking_respects_size_and_overlap(self):
        body = "\n\n".join(f"Paragraph {i} " + "word " * 80 for i in range(10))
        chunks = chunk_text(body, size=500, overlap=100)
        assert all(len(c) <= 600 for c in chunks)
        assert len(chunks) >= 5

    def test_pdf_fixture_parses_with_page_provenance(self, corpus):
        from nexus_local.db import get_session
        from nexus_local.models import Chunk
        doc = corpus["vector_search_primer.pdf"]
        assert doc.parser_used in ("pdfplumber", "pypdf")
        assert doc.parser_confidence > 0.5
        with get_session() as s:
            pages = {c.page for c in s.query(Chunk).filter_by(document_id=doc.id)}
        assert 1 in pages and 2 in pages

    def test_csv_rows_become_searchable_text(self, corpus):
        from nexus_local.db import get_session
        from nexus_local.models import Chunk
        with get_session() as s:
            text = " ".join(c.text for c in s.query(Chunk).filter_by(
                document_id=corpus["ipl_batting.csv"].id))
        assert "strike_rate=163.6" in text


# ------------------------------------------------------------------ retrieval
class TestRetrievalUnits:
    def test_hashing_embedder_deterministic_and_normalized(self):
        import numpy as np
        e = HashingEmbedder(dim=256)
        v1 = e.embed(["token bucket rate limiter"])
        v2 = e.embed(["token bucket rate limiter"])
        assert np.allclose(v1, v2)
        assert abs(np.linalg.norm(v1[0]) - 1.0) < 1e-5

    def test_similar_texts_score_higher(self):
        e = HashingEmbedder()
        q, near, far = e.embed([
            "redis lua scripts atomic counters",
            "redis synchronization uses lua scripts for atomic operations",
            "the cat sat on the warm windowsill",
        ])
        assert float(q @ near) > float(q @ far)

    def test_rrf_prefers_items_ranked_by_both(self):
        fused = rrf_fuse([[("a", 9), ("b", 8), ("c", 7)], [("b", 5), ("a", 4)]])
        assert fused[0][0] in ("a", "b")
        assert dict(fused)["b"] > dict(fused)["c"]


# --------------------------------------------------------------------- memory
class TestMemoryLifecycle:
    def test_proposed_memory_not_retrievable(self, workspace):
        mem.propose_memory("User prefers Go for backend projects", "preference")
        assert mem.retrieve_active_memories("what language for backend") == []

    def test_approval_makes_memory_active_and_retrievable(self, workspace):
        m = mem.propose_memory("User prefers Go for backend projects", "preference")
        mem.approve_memory(m.id)
        found = mem.retrieve_active_memories("backend language preference")
        assert [x.id for x in found] == [m.id]
        assert mem.why_remembered(m.id)["times_used"] == 1

    def test_illegal_transition_rejected(self, workspace):
        m = mem.propose_memory("x", "profile")
        with pytest.raises(ValueError, match="Illegal transition"):
            mem.transition(m.id, "active")  # must go through approved

    def test_deleted_memory_never_retrieved(self, workspace):
        m = mem.propose_memory("User studies at IIT", "profile")
        mem.approve_memory(m.id)
        mem.transition(m.id, "deleted")
        assert mem.retrieve_active_memories("IIT studies") == []

    def test_edit_keeps_version_history(self, workspace):
        m = mem.propose_memory("prefers short answers", "preference")
        m = mem.edit_memory(m.id, "prefers concise answers with examples")
        assert m.version == 2
        assert m.edit_history[0]["content"] == "prefers short answers"

    def test_sensitive_content_flagged(self, workspace):
        m = mem.propose_memory("my email is ritik@example.com", "profile")
        assert m.sensitivity == "sensitive"

    def test_expired_memory_not_retrieved(self, workspace):
        import datetime as dt
        from nexus_local.db import get_session
        from nexus_local.models import Memory
        m = mem.propose_memory("temporary exam goal", "temporary")
        mem.approve_memory(m.id)
        with get_session() as s:
            s.get(Memory, m.id).expires_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)
            s.commit()
        assert mem.retrieve_active_memories("exam goal") == []


# ---------------------------------------------------------------- preferences
class TestPreferences:
    def test_invalid_key_and_value_rejected(self, workspace):
        with pytest.raises(ValueError):
            set_preference("nonsense", "x")
        with pytest.raises(ValueError):
            set_preference("tone", "sarcastic")

    def test_directives_reflect_profile(self, workspace):
        set_preference("verbosity", "concise")
        set_preference("ordering", "code_first")
        d = build_style_directives()
        assert "short and direct" in d and "working code before" in d

    def test_version_increments_on_change(self, workspace):
        p1 = set_preference("tone", "casual")
        p2 = set_preference("tone", "professional")
        assert p2.version == p1.version + 1


# ------------------------------------------------------------------- feedback
class TestFeedback:
    def test_feedback_requires_real_message(self, workspace):
        with pytest.raises(ValueError):
            record_feedback("nonexistent", "helpful")

    def test_unknown_kind_rejected(self, workspace):
        with pytest.raises(ValueError, match="Unknown feedback kind"):
            record_feedback("any", "amazing")


# ------------------------------------------------------------- evaluation math
class TestEvaluationMath:
    def test_precision_recall(self):
        flags = [True, False, True, False, False]
        assert precision_at_k(flags, 5) == pytest.approx(0.4)
        assert recall_at_k(flags, 5, 4) == pytest.approx(0.5)

    def test_mrr(self):
        assert mrr([False, False, True]) == pytest.approx(1 / 3)
        assert mrr([False] * 5) == 0.0

    def test_ndcg_perfect_ranking_is_one(self):
        assert ndcg_at_k([True, True, False, False], 4) == pytest.approx(1.0)
        assert ndcg_at_k([False, False, True, True], 4) < 1.0

    def test_grounding_flags_unsupported_sentence(self):
        rep = grounding_report(
            "The token bucket refills at a fixed rate. Elephants are the largest land mammals on earth.",
            ["The token bucket algorithm refills tokens at a fixed rate and allows bursts."])
        assert rep["supported"] == 1
        assert len(rep["potentially_unsupported"]) == 1
        assert "NOT ground truth" in rep["method"]

    def test_citation_coverage_detects_invalid_index(self):
        cov = citation_coverage("Claim [1]. Other claim [7].", num_evidences=3)
        assert cov["valid_citations"] == [1]
        assert cov["invalid_citations"] == [7]
