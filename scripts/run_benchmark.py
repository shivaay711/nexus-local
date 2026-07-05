"""Run the retrieval benchmark and print + persist the report."""
import json, sys
from pathlib import Path
from nexus_local.config import settings
from nexus_local.db import init_db
from nexus_local.evaluation.retrieval_eval import run_retrieval_benchmark

settings.ensure_dirs(); init_db(settings.db_path)
path = Path(sys.argv[1] if len(sys.argv) > 1 else "data/benchmarks/retrieval_benchmark.jsonl")
report = run_retrieval_benchmark(path, k=5)
print(json.dumps(report["metrics"], indent=2))
out = settings.workspace_dir / "exports" / f"retrieval_report_{report['run_id']}.json"
out.write_text(json.dumps(report, indent=2))
print("saved:", out)
