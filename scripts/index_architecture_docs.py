"""Index project architecture documentation as additional knowledge sources."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from knowledge.config_loader import load_rag_config
from knowledge.pipelines.indexing_pipeline import IndexingPipeline

config = load_rag_config()
pipeline = IndexingPipeline(config)

docs_dir = Path("docs")
results = []
for f in sorted(docs_dir.glob("phase-*.md")):
    r = pipeline.index_document(str(f), category="architecture", source="project-docs")
    results.append(r)
    status = "OK" if r.success else "FAIL"
    print(f"  [{status}] {r.title} ({r.num_chunks} chunks)")

total_ok = sum(1 for r in results if r.success)
total_fail = sum(1 for r in results if not r.success)
print(f"Total: {total_ok} OK, {total_fail} FAIL")
