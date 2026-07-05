"""Domain model. Every entity carries timestamps, provenance, and (where it
matters) content hashes and soft-delete flags."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _id() -> str:
    return uuid.uuid4().hex


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    created_at: Mapped[dt.datetime] = mapped_column(default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(default=_now, onupdate=_now)


class Document(TimestampMixin, Base):
    __tablename__ = "documents"
    path: Mapped[str] = mapped_column(Text)
    filename: Mapped[str] = mapped_column(String(512))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    media_type: Mapped[str] = mapped_column(String(64))
    parser_used: Mapped[str] = mapped_column(String(64), default="")
    parser_confidence: Mapped[float] = mapped_column(Float, default=1.0)
    parse_error: Mapped[str | None] = mapped_column(Text, default=None)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document")


class Chunk(TimestampMixin, Base):
    __tablename__ = "chunks"
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    page: Mapped[int | None] = mapped_column(Integer, default=None)
    heading: Mapped[str | None] = mapped_column(String(512), default=None)
    embedding_model: Mapped[str] = mapped_column(String(128), default="")
    document: Mapped[Document] = relationship(back_populates="chunks")


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"
    title: Mapped[str] = mapped_column(String(256), default="Untitled")
    strict_grounding: Mapped[bool] = mapped_column(Boolean, default=False)
    memory_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


class Message(TimestampMixin, Base):
    __tablename__ = "messages"
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    answer_source: Mapped[str | None] = mapped_column(String(48), default=None)
    evidence_bundle: Mapped[dict | None] = mapped_column(JSON, default=None)
    applied_preferences: Mapped[list | None] = mapped_column(JSON, default=None)
    applied_memory_ids: Mapped[list | None] = mapped_column(JSON, default=None)


class Memory(TimestampMixin, Base):
    __tablename__ = "memories"
    content: Mapped[str] = mapped_column(Text)
    memory_type: Mapped[str] = mapped_column(String(48))
    state: Mapped[str] = mapped_column(String(24), default="proposed", index=True)
    source_conversation_id: Mapped[str | None] = mapped_column(String(32), default=None)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    sensitivity: Mapped[str] = mapped_column(String(24), default="normal")
    retrieval_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[dt.datetime | None] = mapped_column(default=None)
    expires_at: Mapped[dt.datetime | None] = mapped_column(default=None)
    version: Mapped[int] = mapped_column(Integer, default=1)
    edit_history: Mapped[list] = mapped_column(JSON, default=list)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


class Preference(TimestampMixin, Base):
    __tablename__ = "preferences"
    key: Mapped[str] = mapped_column(String(64), unique=True)
    value: Mapped[str] = mapped_column(String(256))
    version: Mapped[int] = mapped_column(Integer, default=1)


class FeedbackRecord(TimestampMixin, Base):
    __tablename__ = "feedback"
    message_id: Mapped[str] = mapped_column(String(32), index=True)
    kind: Mapped[str] = mapped_column(String(48))  # helpful|too_long|incorrect|...
    detail: Mapped[str | None] = mapped_column(Text, default=None)


class SecurityEvent(TimestampMixin, Base):
    __tablename__ = "security_events"
    kind: Mapped[str] = mapped_column(String(48), index=True)
    detail: Mapped[str] = mapped_column(Text)


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_log"
    action: Mapped[str] = mapped_column(String(64))
    entity: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(32))
    detail: Mapped[str | None] = mapped_column(Text, default=None)


class EvaluationRun(TimestampMixin, Base):
    __tablename__ = "evaluation_runs"
    dataset_name: Mapped[str] = mapped_column(String(128))
    dataset_hash: Mapped[str] = mapped_column(String(64))
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    environment: Mapped[dict] = mapped_column(JSON, default=dict)
