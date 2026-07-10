"""Page 8: Knowledge Base — RAG-powered query, ingestion, and collection management."""  # noqa: N999

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import numpy as np
import streamlit as st


def _query_knowledge_base(query: str, k: int = 5) -> list[dict[str, Any]]:
    """Synthetic query — returns sample results when no RAG service is available."""
    np.random.seed(len(query))
    results = []
    for i in range(k):
        results.append(
            {
                "chunk_id": f"chunk_{i}",
                "document_id": f"doc_{np.random.randint(1, 10)}",
                "text": f"Sample document content related to '{query[:50]}'. "
                f"This is a simulated result #{i + 1} with relevance "
                f"to climate patterns and risk assessment.",
                "score": float(np.random.uniform(0.5, 0.98)),
                "rank": i + 1,
                "metadata": {"source": "synthetic", "topic": "climate"},
            }
        )
    return results


def _ingest_document(
    title: str, _source: str, content: str, _tags: list[str] | None = None
) -> dict[str, Any]:
    return {"document_id": "syn-" + title[:8].lower(), "chunks": max(1, len(content) // 500)}


def render(api: Any, filters: dict) -> None:  # noqa: ARG001
    st.header("Knowledge Base")
    st.markdown("Search and query climate documents using RAG (Retrieval-Augmented Generation).")

    tab_query, tab_ingest, tab_collections = st.tabs(["Query", "Ingest Documents", "Collections"])

    with tab_query:
        st.subheader("Ask a Question")

        query = st.text_area(
            "Enter your climate-related question:",
            placeholder="e.g., What are the flood risks in Mumbai during monsoon?",
            height=100,
        )

        col_k, col_btn = st.columns([1, 3])
        with col_k:
            k = st.number_input("Number of results", min_value=1, max_value=20, value=5)
        with col_btn:
            search_btn = st.button("Search", type="primary", use_container_width=True)

        if search_btn and query.strip():
            with st.spinner("Searching knowledge base..."):
                try:
                    results = _query_knowledge_base(query, k)
                    st.session_state["kb_results"] = results
                except Exception as exc:
                    st.warning(f"Knowledge base search unavailable: {exc}")

        if "kb_results" in st.session_state:
            results = st.session_state["kb_results"]
            st.subheader(f"Results ({len(results)})")

            for r in results:
                with st.container():
                    cols = st.columns([0.8, 0.2])
                    with cols[0]:
                        st.markdown(f"**Result #{r['rank']}** — Score: `{r['score']:.3f}`")
                        st.caption(f"Document: {r['document_id']} | Chunk: {r['chunk_id']}")
                        st.markdown(r["text"][:300] + "...")
                    with cols[1]:
                        score_pct = int(r["score"] * 100)
                        st.markdown(f"**{score_pct}%**")
                        st.progress(r["score"])
                    st.divider()

    with tab_ingest:
        st.subheader("Ingest a Document")

        doc_title = st.text_input("Document Title", placeholder="e.g., Mumbai Climate Report 2024")
        doc_source = st.text_input("Source", placeholder="e.g., IMD, IPCC, Research Paper")
        doc_tags = st.text_input(
            "Tags (comma-separated)", placeholder="e.g., flood, mumbai, monsoon"
        )
        doc_content = st.text_area(
            "Document Content",
            height=200,
            placeholder="Paste or type the document content here...",
        )

        if st.button("Ingest Document", type="primary", use_container_width=True):
            if not doc_title or not doc_content:
                st.error("Title and content are required.")
            else:
                with st.spinner("Ingesting document..."):
                    try:
                        tags = (
                            [t.strip() for t in doc_tags.split(",") if t.strip()]
                            if doc_tags
                            else []
                        )
                        result = _ingest_document(
                            doc_title, doc_source or "manual", doc_content, tags
                        )
                        doc_id = result["document_id"]
                        chunks = result["chunks"]
                        st.success(f"Document ingested! ID: {doc_id}, Chunks: {chunks}")
                    except Exception as exc:
                        st.error(f"Ingestion failed: {exc}")

    with tab_collections:
        st.subheader("Document Collections")

        col1, col2 = st.columns([2, 1])
        with col2:
            new_collection = st.text_input("New collection name", placeholder="e.g., monsoon_data")
            if st.button("Create Collection", use_container_width=True) and new_collection:
                st.info(f"Collection '{new_collection}' created (placeholder).")

        with col1:
            collections = [
                {"id": "default", "name": "Default Collection", "docs": 12, "chunks": 156},
                {"id": "imd_reports", "name": "IMD Reports", "docs": 8, "chunks": 94},
                {"id": "ipcc_data", "name": "IPCC Assessment Data", "docs": 5, "chunks": 312},
            ]

            for coll in collections:
                with st.container():
                    stc1, stc2, stc3, stc4 = st.columns([3, 1, 1, 1])
                    stc1.markdown(f"**{coll['name']}**")
                    stc2.metric("Docs", coll["docs"])
                    stc3.metric("Chunks", coll["chunks"])
                    if stc4.button("Select", key=f"sel_{coll['id']}"):
                        st.session_state["selected_collection"] = coll["id"]
                        st.info(f"Selected collection: {coll['name']}")
                    st.divider()

    st.divider()
    st.caption(f"Knowledge Base | {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
