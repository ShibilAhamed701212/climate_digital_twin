"""Page 8: Knowledge Base — RAG-powered query, ingestion, and collection management."""  # noqa: N999

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import streamlit as st


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
                    results = api.search_knowledge(query, k)
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
                        result = api.ingest_document(
                            doc_title, doc_source or "manual", doc_content, tags
                        )
                        doc_id = result.get("document_id", "unknown")
                        chunks = result.get("chunks", 0)
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

        with col1:            # Fetch real collections from the gateway or RAG service
            collections = []
            try:
                import requests as _req

                from dashboard.config.config import API_BASE_URL

                gateway_url = API_BASE_URL.rstrip("/")
                resp = _req.get(f"{gateway_url}/rag/collections", timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    raw = data.get("collections", data if isinstance(data, list) else [])
                    for c in raw:
                        if isinstance(c, dict):
                            collections.append(c)
            except Exception:
                pass

            # Fallback: try the dedicated RAG service
            if not collections:
                try:
                    import requests as _req

                    from dashboard.config.config import RAG_SERVICE_URL

                    rag_url = RAG_SERVICE_URL.rstrip("/")
                    resp = _req.get(f"{rag_url}/health", timeout=5)
                    if resp.status_code == 200:
                        health = resp.json()
                        doc_count = health.get("total_documents", health.get("documents", 0))
                        chunk_count = health.get("total_chunks", health.get("chunks", 0))
                        if doc_count or chunk_count:
                            collections = [{
                                "id": "default",
                                "name": "Default Collection",
                                "docs": doc_count,
                                "chunks": chunk_count,
                            }]
                except Exception:
                    pass

            if not collections:
                st.info(
                    "No collections available yet. Ingest documents above to populate the knowledge base."
                )
            else:
                for coll in collections:
                    with st.container():
                        stc1, stc2, stc3, stc4 = st.columns([3, 1, 1, 1])
                        coll_name = coll.get("name", coll.get("id", "Unknown"))
                        stc1.markdown(f"**{coll_name}**")
                        stc2.metric("Docs", coll.get("docs", coll.get("document_count", 0)))
                        stc3.metric("Chunks", coll.get("chunks", coll.get("chunk_count", 0)))
                        if stc4.button("Select", key=f"sel_{coll.get('id', coll_name)}"):
                            st.session_state["selected_collection"] = coll.get("id", coll_name)
                            st.info(f"Selected collection: {coll_name}")
                        st.divider()

    st.divider()
    st.caption(f"Knowledge Base | {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
