"""NEXUS Local REST API (/api/v1). Binds to 127.0.0.1 only. Every request
gets a request ID; errors are structured; Network Guard status is exposed."""

import uuid

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..config import OfflineMode, settings
from ..db import get_session, init_db
from ..feedback.service import list_feedback, nominate_training_example, record_feedback
from ..ingestion.pipeline import delete_document, import_document
from ..llm.orchestrator import answer, chat_turn, get_adapter
from ..memory import service as memory_svc
from ..models import Conversation, Document, EvaluationRun, Memory, Message, SecurityEvent
from ..preferences.service import SCHEMA, get_profile, set_preference
from ..retrieval.hybrid import embed_pending_chunks, retrieve
from ..security.network_guard import guard


def create_app(db_path=None) -> FastAPI:
    settings.ensure_dirs()
    init_db(db_path or settings.db_path)
    if settings.network_guard_enabled and settings.offline_mode == OfflineMode.AIR_GAPPED:
        guard.enable()

    app = FastAPI(title="NEXUS Local API", version="0.1.0",
                  docs_url="/api/v1/docs", openapi_url="/api/v1/openapi.json")

    @app.middleware("http")
    async def request_id(request: Request, call_next):
        rid = uuid.uuid4().hex[:12]
        try:
            response = await call_next(request)
        except HTTPException:
            raise
        except Exception as e:  # structured error envelope
            return JSONResponse(status_code=500, content={
                "error": {"type": type(e).__name__, "message": str(e), "request_id": rid}})
        response.headers["X-Request-ID"] = rid
        return response

    # ------------------------------------------------------------- health
    @app.get("/api/v1/health")
    def health():
        from ..llm.runtime_mode import is_online
        return {"status": "ok", "offline_mode": settings.offline_mode.value,
                "online": is_online(),
                "network_guard": guard.enabled, "llm_adapter": get_adapter().name}

    class ModeRequest(BaseModel):
        online: bool

    @app.post("/api/v1/mode")
    def set_mode(req: ModeRequest):
        from ..llm.runtime_mode import set_online
        return set_online(req.online)

    @app.get("/api/v1/security/network-guard")
    def network_guard_status():
        return guard.status()

    @app.get("/api/v1/system/diagnostics")
    def diagnostics():
        import platform
        import shutil
        with get_session() as s:
            docs = s.query(Document).filter(Document.deleted.is_(False)).count()
            convs = s.query(Conversation).filter(Conversation.deleted.is_(False)).count()
            mems = s.query(Memory).filter(Memory.state == "active").count()
        gpu = False
        try:
            import torch  # noqa: F401  (optional)
            gpu = torch.cuda.is_available()
        except Exception:
            pass
        return {
            "platform": platform.platform(), "python": platform.python_version(),
            "gpu_cuda_available": gpu,
            "disk_free_gb": round(shutil.disk_usage(str(settings.workspace_dir)).free / 1e9, 1),
            "documents": docs, "conversations": convs, "active_memories": mems,
            "blocked_network_attempts": len(guard.blocked_attempts),
        }

    # ---------------------------------------------------------- documents
    class ImportRequest(BaseModel):
        path: str

    @app.post("/api/v1/documents/import", status_code=201)
    def import_doc(req: ImportRequest):
        try:
            doc = import_document(req.path)
        except (ValueError, FileNotFoundError) as e:
            raise HTTPException(422, str(e))
        embedded = embed_pending_chunks()
        return {"id": doc.id, "filename": doc.filename, "sha256": doc.sha256,
                "parser": doc.parser_used, "parser_confidence": doc.parser_confidence,
                "parse_error": doc.parse_error, "chunks_embedded": embedded}

    @app.get("/api/v1/documents")
    def list_documents(limit: int = Query(50, le=200), offset: int = 0):
        with get_session() as s:
            rows = s.execute(select(Document).where(Document.deleted.is_(False))
                             .limit(limit).offset(offset)).scalars().all()
            return [{"id": d.id, "filename": d.filename, "sha256": d.sha256,
                     "media_type": d.media_type, "parser": d.parser_used,
                     "parser_confidence": d.parser_confidence} for d in rows]

    @app.delete("/api/v1/documents/{doc_id}", status_code=204)
    def remove_document(doc_id: str):
        delete_document(doc_id)

    # ------------------------------------------------------------- search
    @app.get("/api/v1/search")
    def search(q: str, k: int = Query(8, le=25)):
        return retrieve(q, top_k=k).to_dict()

    # --------------------------------------------------------------- chat
    class ConversationCreate(BaseModel):
        title: str = "Untitled"
        strict_grounding: bool = False
        memory_enabled: bool = True

    @app.post("/api/v1/conversations", status_code=201)
    def create_conversation(req: ConversationCreate):
        with get_session() as s:
            c = Conversation(**req.model_dump())
            s.add(c)
            s.commit()
            return {"id": c.id, "title": c.title, "strict_grounding": c.strict_grounding}

    @app.get("/api/v1/conversations")
    def list_conversations():
        with get_session() as s:
            rows = s.execute(select(Conversation).where(Conversation.deleted.is_(False))
                             .order_by(Conversation.updated_at.desc())).scalars().all()
            return [{"id": c.id, "title": c.title, "strict_grounding": c.strict_grounding,
                     "created_at": c.created_at.isoformat()} for c in rows]

    @app.delete("/api/v1/conversations/{conv_id}", status_code=204)
    def delete_conversation(conv_id: str):
        with get_session() as s:
            c = s.get(Conversation, conv_id)
            if c:
                c.deleted = True
                s.commit()

    class MessageCreate(BaseModel):
        content: str = Field(min_length=1)

    @app.post("/api/v1/conversations/{conv_id}/messages")
    def send_message(conv_id: str, req: MessageCreate):
        try:
            result = chat_turn(conv_id, req.content)
        except ValueError as e:
            raise HTTPException(404, str(e))
        return {"answer": result.answer, "answer_source": result.answer_source,
                "evidence_bundle": result.evidence_bundle,
                "applied_preferences": result.applied_preferences,
                "applied_memory_ids": result.applied_memory_ids,
                "adapter": result.adapter,
                "web_results": result.web_results,
                "proposed_memory_ids": result.proposed_memory_ids}

    @app.get("/api/v1/conversations/{conv_id}/messages")
    def list_messages(conv_id: str):
        with get_session() as s:
            rows = s.execute(select(Message).where(Message.conversation_id == conv_id)
                             .order_by(Message.created_at)).scalars().all()
            return [{"id": m.id, "role": m.role, "content": m.content,
                     "answer_source": m.answer_source} for m in rows]

    class AskRequest(BaseModel):
        query: str
        strict_grounding: bool = False
        memory_enabled: bool = True

    @app.post("/api/v1/ask")
    def ask(req: AskRequest):
        r = answer(req.query, req.strict_grounding, req.memory_enabled)
        return {"answer": r.answer, "answer_source": r.answer_source,
                "evidence_bundle": r.evidence_bundle,
                "applied_preferences": r.applied_preferences,
                "applied_memory_ids": r.applied_memory_ids, "adapter": r.adapter}

    # ------------------------------------------------------------- memory
    class MemoryPropose(BaseModel):
        content: str
        memory_type: str
        source_conversation_id: str | None = None

    @app.post("/api/v1/memories/propose", status_code=201)
    def propose(req: MemoryPropose):
        try:
            m = memory_svc.propose_memory(req.content, req.memory_type,
                                          req.source_conversation_id)
        except ValueError as e:
            raise HTTPException(422, str(e))
        return {"id": m.id, "state": m.state, "sensitivity": m.sensitivity}

    @app.post("/api/v1/memories/{mem_id}/approve")
    def approve(mem_id: str):
        try:
            m = memory_svc.approve_memory(mem_id)
        except ValueError as e:
            raise HTTPException(422, str(e))
        return {"id": m.id, "state": m.state}

    @app.post("/api/v1/memories/{mem_id}/reject")
    def reject(mem_id: str):
        try:
            m = memory_svc.transition(mem_id, "rejected")
        except ValueError as e:
            raise HTTPException(422, str(e))
        return {"id": m.id, "state": m.state}

    class MemoryEdit(BaseModel):
        content: str

    @app.patch("/api/v1/memories/{mem_id}")
    def edit(mem_id: str, req: MemoryEdit):
        try:
            m = memory_svc.edit_memory(mem_id, req.content)
        except ValueError as e:
            raise HTTPException(404, str(e))
        return {"id": m.id, "version": m.version}

    @app.delete("/api/v1/memories/{mem_id}", status_code=204)
    def delete_memory(mem_id: str):
        try:
            memory_svc.transition(mem_id, "deleted")
        except ValueError:
            with get_session() as s:  # allow delete from any state via force path
                m = s.get(Memory, mem_id)
                if m is None:
                    raise HTTPException(404, "Memory not found")
                m.state, m.deleted = "deleted", True
                s.commit()

    @app.get("/api/v1/memories")
    def list_memories(state: str | None = None):
        with get_session() as s:
            q = select(Memory).where(Memory.deleted.is_(False))
            if state:
                q = q.where(Memory.state == state)
            return [{"id": m.id, "content": m.content, "type": m.memory_type,
                     "state": m.state, "sensitivity": m.sensitivity}
                    for m in s.execute(q).scalars()]

    @app.get("/api/v1/memories/{mem_id}/why")
    def why(mem_id: str):
        try:
            return memory_svc.why_remembered(mem_id)
        except ValueError as e:
            raise HTTPException(404, str(e))

    @app.get("/api/v1/memories/export/all")
    def export_all():
        return memory_svc.export_memories()

    # -------------------------------------------------------- preferences
    class PreferenceSet(BaseModel):
        key: str
        value: str

    @app.get("/api/v1/preferences")
    def preferences():
        return {"profile": get_profile(), "schema": {k: sorted(v) for k, v in SCHEMA.items()}}

    @app.put("/api/v1/preferences")
    def put_preference(req: PreferenceSet):
        try:
            p = set_preference(req.key, req.value)
        except ValueError as e:
            raise HTTPException(422, str(e))
        return {"key": p.key, "value": p.value, "version": p.version}

    # ----------------------------------------------------------- feedback
    class FeedbackCreate(BaseModel):
        message_id: str
        kind: str
        detail: str | None = None

    @app.post("/api/v1/feedback", status_code=201)
    def feedback(req: FeedbackCreate):
        try:
            rec = record_feedback(req.message_id, req.kind, req.detail)
        except ValueError as e:
            raise HTTPException(422, str(e))
        return {"id": rec.id, "kind": rec.kind}

    @app.get("/api/v1/feedback")
    def get_feedback():
        return [{"id": f.id, "message_id": f.message_id, "kind": f.kind,
                 "detail": f.detail} for f in list_feedback()]

    class TrainingNominate(BaseModel):
        message_id: str
        corrected_answer: str

    @app.post("/api/v1/training-examples/nominate", status_code=201)
    def nominate(req: TrainingNominate):
        try:
            mem_id = nominate_training_example(req.message_id, req.corrected_answer)
        except ValueError as e:
            raise HTTPException(404, str(e))
        return {"memory_id": mem_id, "state": "proposed",
                "note": "Requires explicit approval before any training use."}

    # --------------------------------------------------------- evaluation
    @app.post("/api/v1/evaluations/retrieval")
    def eval_retrieval(benchmark_path: str, k: int = 5):
        from pathlib import Path
        from ..evaluation.retrieval_eval import run_retrieval_benchmark
        p = Path(benchmark_path)
        if not p.exists():
            raise HTTPException(422, "Benchmark file not found")
        return run_retrieval_benchmark(p, k=k)

    @app.get("/api/v1/evaluations")
    def list_evaluations():
        with get_session() as s:
            return [{"id": r.id, "dataset": r.dataset_name, "dataset_hash": r.dataset_hash,
                     "metrics": r.metrics, "created_at": r.created_at.isoformat()}
                    for r in s.execute(select(EvaluationRun)).scalars()]

    # ------------------------------------------------------------- audit
    @app.get("/api/v1/audit-log")
    def audit_log(limit: int = Query(100, le=500)):
        from ..models import AuditLog
        with get_session() as s:
            rows = s.execute(select(AuditLog).order_by(AuditLog.created_at.desc())
                             .limit(limit)).scalars().all()
            return [{"action": a.action, "entity": a.entity, "entity_id": a.entity_id,
                     "detail": a.detail, "at": a.created_at.isoformat()} for a in rows]

    @app.get("/api/v1/security/events")
    def security_events():
        with get_session() as s:
            return [{"kind": e.kind, "detail": e.detail, "at": e.created_at.isoformat()}
                    for e in s.execute(select(SecurityEvent)).scalars()]

    return app
