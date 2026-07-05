from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from .models import AuditLog, Base

_engine = None
_SessionLocal: sessionmaker | None = None


def init_db(db_path: Path | str) -> None:
    """Create the engine, all tables, and the FTS5 lexical index."""
    global _engine, _SessionLocal
    url = f"sqlite:///{db_path}" if str(db_path) != ":memory:" else "sqlite://"
    _engine = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(_engine, "connect")
    def _set_pragmas(dbapi_conn, _):  # WAL for durability + concurrency
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(_engine)
    with _engine.connect() as conn:
        conn.execute(text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5("
            "chunk_id UNINDEXED, document_id UNINDEXED, body)"
        ))
        conn.commit()


def get_session() -> Session:
    if _SessionLocal is None:
        _make_factory()
    return _SessionLocal()  # type: ignore[misc]


def _make_factory() -> None:
    global _SessionLocal
    if _engine is None:
        raise RuntimeError("init_db() must be called first")
    _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)


def engine():
    return _engine


def audit(session: Session, action: str, entity: str, entity_id: str, detail: str | None = None) -> None:
    session.add(AuditLog(action=action, entity=entity, entity_id=entity_id, detail=detail))
