"""Local LLM adapters and the chat orchestrator.

Adapters:
  - MockAdapter: deterministic extractive responder used for tests and for
    running the full pipeline with zero model weights. Clearly labeled.
  - OllamaAdapter: talks to a local Ollama server on 127.0.0.1 (loopback is
    permitted by the Network Guard). NOT VERIFIED in the build environment —
    no Ollama runtime or model weights were available; documented in
    docs/known_limitations.md.

Strict grounding contract: with strict_grounding=True the orchestrator will
only answer from retrieved evidence, cites chunk provenance, and returns
"insufficient local evidence" when retrieval comes back empty or weak.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..config import settings
from ..db import get_session
from ..memory.service import retrieve_active_memories
from ..preferences.service import applied_preference_summary, build_style_directives
from ..retrieval.hybrid import EvidenceBundle, retrieve

INSUFFICIENT = "I could not find sufficient local evidence to answer this question."


class LLMAdapter(ABC):
    name: str = "abstract"

    @abstractmethod
    def generate(self, system: str, prompt: str, max_tokens: int = 512) -> str: ...

    def available(self) -> bool:
        return True


class MockAdapter(LLMAdapter):
    """Extractive, deterministic. Surfaces the top evidence sentences that
    overlap the query. Exists so the entire system is testable offline with
    no weights; it is never presented as a neural model."""
    name = "mock-extractive"

    def generate(self, system: str, prompt: str, max_tokens: int = 512) -> str:
        m = re.search(r"QUESTION:\s*(.+?)(?:\n|$)", prompt, re.S)
        query_terms = set(re.findall(r"[a-z0-9]+", (m.group(1) if m else prompt).lower()))
        sentences = re.split(r"(?<=[.!?])\s+", prompt)
        scored = []
        for s_ in sentences:
            terms = set(re.findall(r"[a-z0-9]+", s_.lower()))
            overlap = len(terms & query_terms)
            if overlap >= 2 and "QUESTION:" not in s_:
                scored.append((overlap, s_.strip()))
        scored.sort(key=lambda x: -x[0])
        if not scored:
            return INSUFFICIENT
        return " ".join(s for _, s in scored[:3])[: max_tokens * 4]


class OllamaAdapter(LLMAdapter):
    """Local Ollama over loopback. UNVERIFIED in this build environment."""

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model
        self.name = f"ollama:{self.model}"

    def available(self) -> bool:
        import httpx
        try:
            return httpx.get(f"{self.base_url}/api/tags", timeout=2).status_code == 200
        except Exception:
            return False

    def generate(self, system: str, prompt: str, max_tokens: int = 512) -> str:
        import httpx
        r = httpx.post(f"{self.base_url}/api/generate", json={
            "model": self.model, "system": system, "prompt": prompt,
            "stream": False, "options": {"num_predict": max_tokens},
        }, timeout=300)
        r.raise_for_status()
        return r.json().get("response", "")


def get_adapter() -> LLMAdapter:
    if settings.llm_runtime == "ollama":
        return OllamaAdapter()
    return MockAdapter()


# --------------------------------------------------------------- orchestration
@dataclass
class ChatResult:
    answer: str
    answer_source: str  # local_sources|approved_memory|base_model|mixed|web_sources|insufficient_evidence
    evidence_bundle: dict
    applied_preferences: list[str]
    applied_memory_ids: list[str]
    adapter: str
    web_results: list[dict] | None = None
    proposed_memory_ids: list[str] | None = None


GROUNDED_SYSTEM = (
    "You are NEXUS Local, an offline assistant. Answer ONLY from the provided "
    "local evidence. Cite sources as [file, page]. If the evidence does not "
    f"contain the answer, reply exactly: {INSUFFICIENT}"
)
OPEN_SYSTEM = (
    "You are NEXUS, the user's personal assistant running on their own machine. "
    "Be direct and useful. Answer the question asked — no filler, no unnecessary "
    "disclaimers, no moralizing on ordinary topics, no sugar-coating. If something "
    "is a bad idea, say so plainly and say why. Prefer provided LOCAL EVIDENCE or "
    "WEB RESULTS when present and mention when you're answering from general "
    "knowledge instead. It's fine to be conversational and to have a sense of humor."
)


def _format_evidence(bundle: EvidenceBundle) -> str:
    blocks = []
    for i, ev in enumerate(bundle.evidences, 1):
        loc = f"{ev.source_file}" + (f", p.{ev.page}" if ev.page else "")
        blocks.append(f"[{i}] ({loc})\n{ev.excerpt}")
    return "\n\n".join(blocks)


def answer(query: str, strict_grounding: bool = False, memory_enabled: bool = True,
           adapter: LLMAdapter | None = None, top_k: int | None = None,
           history: list[dict] | None = None) -> ChatResult:
    from .runtime_mode import is_online
    from ..retrieval.web_search import web_search
    adapter = adapter or get_adapter()
    bundle = retrieve(query, top_k=top_k)

    if not strict_grounding:
        # Relevance gate for free-chat mode: dense cosine always ranks
        # *something* on a non-empty corpus, so require a lexical hit or a
        # meaningful dense score before treating chat as document-grounded.
        # Greetings/small talk fall through to a clean free answer.
        kept = [ev for ev in bundle.evidences
                if ev.bm25_score is not None or (ev.dense_score or 0.0) >= 0.18]
        bundle.evidences = kept

    web_results: list[dict] = []
    if is_online() and not strict_grounding:
        web_results = [r.__dict__ for r in web_search(query, limit=4)]

    memories = retrieve_active_memories(query) if memory_enabled else []
    memory_text = "\n".join(f"- {m.content}" for m in memories)
    style = build_style_directives()
    prefs = applied_preference_summary()

    has_evidence = len(bundle.evidences) > 0

    if strict_grounding and not has_evidence:
        return ChatResult(INSUFFICIENT, "insufficient_evidence", bundle.to_dict(),
                          prefs, [m.id for m in memories], adapter.name)

    system = GROUNDED_SYSTEM if strict_grounding else OPEN_SYSTEM
    if style:
        system += "\nStyle directives from the user's approved preferences:\n" + style

    parts = []
    if history:
        convo = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history[-12:])
        parts.append("CONVERSATION SO FAR:\n" + convo)
    if has_evidence:
        parts.append("LOCAL EVIDENCE:\n" + _format_evidence(bundle))
    if web_results:
        web_block = "\n\n".join(
            f"[W{i}] {r['title']}\n{r['snippet']}\n({r['url']})"
            for i, r in enumerate(web_results, 1))
        parts.append("WEB RESULTS:\n" + web_block)
    if memory_text:
        parts.append("APPROVED USER MEMORY:\n" + memory_text)
    parts.append(f"QUESTION: {query}")
    text = adapter.generate(system, "\n\n".join(parts))

    if strict_grounding and INSUFFICIENT in text:
        source = "insufficient_evidence"
    elif has_evidence and (memories or web_results):
        source = "mixed"
    elif has_evidence:
        source = "local_sources"
    elif web_results:
        source = "web_sources"
    elif memories:
        source = "approved_memory"
    else:
        source = "base_model"

    return ChatResult(text, source, bundle.to_dict(), prefs,
                      [m.id for m in memories], adapter.name,
                      web_results=web_results or None)


def chat_turn(conversation_id: str, query: str) -> ChatResult:
    """Persist a full user->assistant turn on a stored conversation, with
    conversation history and auto-proposed (never auto-approved) memories."""
    from sqlalchemy import select
    from ..models import Conversation, Message
    from .runtime_mode import propose_memories_from_text
    with get_session() as s:
        conv = s.get(Conversation, conversation_id)
        if conv is None or conv.deleted:
            raise ValueError("Conversation not found")
        prior = s.execute(select(Message).where(Message.conversation_id == conversation_id)
                          .order_by(Message.created_at)).scalars().all()
        history = [{"role": m.role, "content": m.content} for m in prior]
        s.add(Message(conversation_id=conversation_id, role="user", content=query))
        if conv.title == "Untitled" and not prior:
            conv.title = query[:60]
        s.commit()
        strict, mem = conv.strict_grounding, conv.memory_enabled
    proposed = propose_memories_from_text(query, conversation_id) if mem else []
    result = answer(query, strict_grounding=strict, memory_enabled=mem, history=history)
    result.proposed_memory_ids = proposed or None
    with get_session() as s:
        s.add(Message(conversation_id=conversation_id, role="assistant",
                      content=result.answer, answer_source=result.answer_source,
                      evidence_bundle=result.evidence_bundle,
                      applied_preferences=result.applied_preferences,
                      applied_memory_ids=result.applied_memory_ids))
        s.commit()
    return result
