import shutil
from pathlib import Path

import pytest

from nexus_local.config import settings
from nexus_local import db as dbmod
from nexus_local.db import init_db

FIXTURES = Path(__file__).parent.parent / "data" / "fixtures" / "documents"
BENCHMARK = Path(__file__).parent.parent / "data" / "benchmarks" / "retrieval_benchmark.jsonl"


@pytest.fixture()
def workspace(tmp_path, monkeypatch):
    """Fresh isolated workspace + database per test."""
    monkeypatch.setattr(settings, "workspace_dir", tmp_path)
    settings.ensure_dirs()
    dbmod._engine = None
    dbmod._SessionLocal = None
    init_db(tmp_path / "nexus.db")
    return tmp_path


@pytest.fixture()
def corpus(workspace):
    """Workspace with all demo fixtures imported and embedded."""
    from nexus_local.ingestion.pipeline import import_document
    from nexus_local.retrieval.hybrid import embed_pending_chunks

    docs = {}
    for f in sorted(FIXTURES.iterdir()):
        target = workspace / "documents" / f.name
        shutil.copy(f, target)
        docs[f.name] = import_document(target)
    embed_pending_chunks()
    return docs
