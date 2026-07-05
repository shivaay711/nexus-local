"""Memory lifecycle. Hard invariant: nothing becomes retrievable without an
explicit user approval transition. Deleted memories are never retrieved."""
from __future__ import annotations

import datetime as dt
import re

from sqlalchemy import select

from ..db import audit, get_session
from ..models import Memory

VALID_TYPES = {
    "preference", "profile", "project", "study", "work_style", "communication_style",
    "temporary", "instruction", "correction", "goal", "constraint", "training_example",
}
# proposed -> (approve|reject) ; approved memories are active; expiry/archive/delete follow.
TRANSITIONS = {
    "proposed": {"approved", "rejected"},
    "approved": {"active"},
    "active": {"expiring", "archived", "deleted"},
    "expiring": {"archived", "deleted", "active"},
    "archived": {"active", "deleted"},
    "rejected": {"deleted"},
}

SENSITIVE_PATTERNS = [
    (re.compile(r"\b\d{12}\b"), "possible Aadhaar number"),
    (re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), "possible PAN"),
    (re.compile(r"\b(?:\d[ -]*?){13,19}\b"), "possible card number"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "email address"),
    (re.compile(r"(password|api[_ ]?key|secret)\s*[:=]", re.I), "credential-like text"),
]


def classify_sensitivity(content: str) -> tuple[str, list[str]]:
    hits = [label for rx, label in SENSITIVE_PATTERNS if rx.search(content)]
    return ("sensitive" if hits else "normal"), hits


def propose_memory(content: str, memory_type: str, source_conversation_id: str | None = None,
                   confidence: float = 0.5) -> Memory:
    if memory_type not in VALID_TYPES:
        raise ValueError(f"Unknown memory type: {memory_type}")
    sensitivity, _ = classify_sensitivity(content)
    with get_session() as s:
        m = Memory(content=content, memory_type=memory_type, state="proposed",
                   source_conversation_id=source_conversation_id,
                   confidence=confidence, sensitivity=sensitivity)
        s.add(m)
        s.flush()
        audit(s, "propose", "memory", m.id)
        s.commit()
        return m


def transition(memory_id: str, new_state: str) -> Memory:
    with get_session() as s:
        m = s.get(Memory, memory_id)
        if m is None:
            raise ValueError("Memory not found")
        if new_state not in TRANSITIONS.get(m.state, set()):
            raise ValueError(f"Illegal transition {m.state} -> {new_state}")
        m.state = new_state
        if new_state == "deleted":
            m.deleted = True
        audit(s, f"state:{new_state}", "memory", m.id)
        s.commit()
        return m


def approve_memory(memory_id: str) -> Memory:
    transition(memory_id, "approved")
    return transition(memory_id, "active")


def edit_memory(memory_id: str, new_content: str) -> Memory:
    with get_session() as s:
        m = s.get(Memory, memory_id)
        if m is None or m.deleted:
            raise ValueError("Memory not found")
        history = list(m.edit_history or [])
        history.append({"version": m.version, "content": m.content,
                        "at": dt.datetime.now(dt.timezone.utc).isoformat()})
        m.edit_history = history
        m.content = new_content
        m.version += 1
        m.sensitivity, _ = classify_sensitivity(new_content)
        audit(s, "edit", "memory", m.id)
        s.commit()
        return m


def retrieve_active_memories(query: str, limit: int = 5) -> list[Memory]:
    """Lexical-overlap retrieval over ACTIVE memories only, with expiry
    enforcement and usage accounting."""
    q_terms = set(re.findall(r"[a-z0-9]+", query.lower()))
    now = dt.datetime.now(dt.timezone.utc)
    with get_session() as s:
        rows = s.execute(select(Memory).where(
            Memory.state == "active", Memory.deleted.is_(False))).scalars().all()
        scored = []
        for m in rows:
            if m.expires_at is not None:
                exp = m.expires_at if m.expires_at.tzinfo else m.expires_at.replace(tzinfo=dt.timezone.utc)
                if exp < now:
                    m.state = "expiring"
                    continue
            terms = set(re.findall(r"[a-z0-9]+", m.content.lower()))
            overlap = len(terms & q_terms)
            # instructions and preferences apply broadly, not only on overlap
            if m.memory_type in ("instruction", "preference") or overlap > 0:
                scored.append((overlap, m))
        scored.sort(key=lambda x: -x[0])
        chosen = [m for _, m in scored[:limit]]
        for m in chosen:
            m.retrieval_count += 1
            m.last_used_at = now
        s.commit()
        return chosen


def export_memories() -> list[dict]:
    with get_session() as s:
        rows = s.execute(select(Memory).where(Memory.deleted.is_(False))).scalars().all()
        return [{
            "id": m.id, "content": m.content, "type": m.memory_type, "state": m.state,
            "confidence": m.confidence, "sensitivity": m.sensitivity,
            "created_at": m.created_at.isoformat(), "version": m.version,
            "retrieval_count": m.retrieval_count,
            "source_conversation_id": m.source_conversation_id,
        } for m in rows]


def why_remembered(memory_id: str) -> dict:
    with get_session() as s:
        m = s.get(Memory, memory_id)
        if m is None:
            raise ValueError("Memory not found")
        return {
            "id": m.id, "content": m.content, "state": m.state,
            "source_conversation_id": m.source_conversation_id,
            "created_at": m.created_at.isoformat(),
            "approved": m.state in ("approved", "active"),
            "sensitivity": m.sensitivity,
            "times_used": m.retrieval_count,
            "last_used_at": m.last_used_at.isoformat() if m.last_used_at else None,
            "edit_history": m.edit_history,
        }
