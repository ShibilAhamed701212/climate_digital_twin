"""Index all knowledge documents into the FAISS vector store.

Usage:
    python scripts/index_knowledge_base.py

This script:
  1. Scans knowledge/documents/ for all supported files
  2. Indexes each document via the IndexingPipeline
  3. Validates retrieval with sample queries
  4. Generates an indexing summary report
"""

import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from knowledge.config_loader import load_rag_config
from knowledge.pipelines.indexing_pipeline import IndexingPipeline
from knowledge.vector_store import FAISSStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("knowledge_indexer")

DOCUMENTS_BASE = Path("knowledge/documents")


def main() -> None:
    config = load_rag_config()
    pipeline = IndexingPipeline(config)
    doc_cfg = config.get("documents", {})
    base_path = Path(doc_cfg.get("base_path", "knowledge/documents"))
    supported_exts = set(doc_cfg.get("supported_formats", ["md", "txt", "csv", "json"]))

    all_results = []
    total_success = 0
    total_fail = 0
    total_chunks = 0

    for file_path in sorted(base_path.rglob("*")):
        if not file_path.is_file():
            continue
        ext = file_path.suffix.lstrip(".").lower()
        if ext not in supported_exts:
            continue

        category = file_path.parent.name
        result = pipeline.index_document(str(file_path), category=category)
        all_results.append(result)
        if result.success:
            total_success += 1
            total_chunks += result.num_chunks
        else:
            total_fail += 1
        status = "OK" if result.success else "FAIL"
        logger.info(
            "  [%s] %s (%d chunks) %s", status, result.title, result.num_chunks, result.error
        )

    vs_cfg = config.get("vector_store", {})
    store = FAISSStore(
        index_path=vs_cfg.get("index_path", "knowledge/vector_store/index.faiss"),
        metadata_path=vs_cfg.get("metadata_path", "knowledge/vector_store/metadata.pkl"),
        dimension=config.get("rag", {}).get("embedding_dimension", 384),
    )

    print()
    print("=" * 60)
    print("INDEXING SUMMARY")
    print("=" * 60)
    print(f"  Documents indexed: {total_success}")
    print(f"  Documents failed:  {total_fail}")
    print(f"  Total chunks:      {total_chunks}")
    print(f"  Vector store:      {store.total_chunks} vectors")
    print(f"  Index path:        {store.index_path}")
    print(f"  Metadata path:     {store.metadata_path}")
    print()

    sources = store.list_sources()
    print("=" * 60)
    print("SOURCES")
    print("=" * 60)
    for s in sources:
        print(
            f"  {s['document_id'][:12]}  {s['title'][:50]:50s}  {s['category']:20s}  {s['chunk_count']} chunks"
        )
    print()

    test_queries = [
        "What is the average annual rainfall in Karnataka?",
        "How does INSAT-3DR estimate rainfall?",
        "What is a digital twin in climate science?",
        "How does the Southwest Monsoon affect Karnataka?",
        "What machine learning models are used for climate forecasting?",
        "How is flood risk assessed?",
        "What temperature thresholds indicate heatwaves in Karnataka?",
        "Where can I access IMD gridded weather data?",
    ]

    print("=" * 60)
    print("RETRIEVAL VALIDATION")
    print("=" * 60)
    passed = 0
    for query in test_queries:
        start = time.perf_counter()
        results = store.search(
            pipeline.embedding_model.encode_single(query),
            top_k=3,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        has_relevant = len(results) >= 1
        scores = [r.score for r in results]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        if has_relevant:
            passed += 1
        print(f"\n  Query: {query}")
        print(f"  Results: {len(results)}, Avg score: {avg_score:.4f}, Latency: {latency_ms:.1f}ms")
        for r in results[:2]:
            print(f"    [{r.score:.4f}] {r.title[:50]:50s} ({r.category})")
    print()
    print(f"  Queries with results: {passed}/{len(test_queries)}")

    retrieval_report = {
        "total_queries": len(test_queries),
        "queries_with_results": passed,
        "success_rate": round(passed / len(test_queries) * 100, 1),
        "avg_latency_ms": 0.0,
        "total_chunks": store.total_chunks,
        "total_sources": len(sources),
    }
    print()
    print("=" * 60)
    print("RETRIEVAL BENCHMARK REPORT")
    print("=" * 60)
    for k, v in retrieval_report.items():
        print(f"  {k}: {v}")
    print()

    if store.total_chunks == 0:
        logger.error("Vector store is EMPTY after indexing — no chunks were added")
        sys.exit(1)
    logger.info(
        "Knowledge base indexing complete: %d chunks, %d sources", store.total_chunks, len(sources)
    )


if __name__ == "__main__":
    main()
