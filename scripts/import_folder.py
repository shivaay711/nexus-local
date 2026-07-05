"""Import every supported file in a folder, then embed pending chunks."""
import sys
from pathlib import Path
from nexus_local.config import settings
from nexus_local.db import init_db
from nexus_local.ingestion.pipeline import import_document
from nexus_local.retrieval.hybrid import embed_pending_chunks

settings.ensure_dirs(); init_db(settings.db_path)
folder = Path(sys.argv[1])
for f in sorted(folder.iterdir()):
    if f.suffix.lower() in settings.allowed_extensions:
        d = import_document(f)
        print(f"imported {d.filename} parser={d.parser_used} conf={d.parser_confidence}")
print("chunks embedded:", embed_pending_chunks())
