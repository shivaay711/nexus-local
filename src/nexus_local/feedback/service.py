"""Explicit feedback loop. All feedback is stored locally and reviewable.
Feedback never triggers training; it can nominate candidate training examples
that then require explicit approval through the memory system."""
from __future__ import annotations

from sqlalchemy import select

from ..db import audit, get_session
from ..models import FeedbackRecord, Message

VALID_KINDS = {
    "helpful", "not_helpful", "too_long", "too_short", "incorrect", "wrong_tone",
    "wrong_sources", "better_answer", "use_style_in_future", "never_like_this",
    "save_preferred_format",
}


def record_feedback(message_id: str, kind: str, detail: str | None = None) -> FeedbackRecord:
    if kind not in VALID_KINDS:
        raise ValueError(f"Unknown feedback kind: {kind}")
    with get_session() as s:
        if s.get(Message, message_id) is None:
            raise ValueError("Message not found")
        rec = FeedbackRecord(message_id=message_id, kind=kind, detail=detail)
        s.add(rec)
        audit(s, "feedback", "message", message_id, kind)
        s.commit()
        return rec


def list_feedback() -> list[FeedbackRecord]:
    with get_session() as s:
        return list(s.execute(select(FeedbackRecord)).scalars())


def nominate_training_example(message_id: str, corrected_answer: str) -> str:
    """A 'better_answer' edit becomes a *proposed* training-example memory.
    It is unusable for anything until the user explicitly approves it."""
    from ..memory.service import propose_memory
    with get_session() as s:
        msg = s.get(Message, message_id)
        if msg is None:
            raise ValueError("Message not found")
    record_feedback(message_id, "better_answer", corrected_answer)
    mem = propose_memory(
        content=f"TRAINING CANDIDATE\nOriginal: {msg.content[:500]}\nCorrected: {corrected_answer[:2000]}",
        memory_type="training_example",
    )
    return mem.id
