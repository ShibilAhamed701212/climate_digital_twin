from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.dependencies import get_rag_service
from backend.api.models import (
    BatchIngestRequest,
    BatchIngestResponse,
    CollectionStatsResponse,
    CreateCollectionRequest,
    RAGAskRequest,
    RAGAskResponse,
    RAGContextRequest,
    RAGContextResponse,
    RAGIngestRequest,
    RAGIngestResponse,
    SearchCollectionRequest,
)

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG Knowledge Base"])


@router.post(
    "/ask",
    response_model=RAGAskResponse,
    summary="Ask a question",
)
async def ask_question(
    request: RAGAskRequest,
    rag_service: Any = Depends(get_rag_service),  # noqa: B008
) -> RAGAskResponse:
    try:
        results = await rag_service.ask(
            query=request.query,
            k=request.k,
            _collection_id=request.collection_id,
        )

        result_dicts: list[dict[str, Any]] = []
        for r in results:
            result_dicts.append(
                {
                    "chunk_id": r.chunk.chunk_id,
                    "document_id": r.chunk.document_id,
                    "text": r.chunk.text[:500],
                    "score": r.score,
                    "rank": r.rank,
                    "metadata": r.chunk.metadata,
                }
            )

        return RAGAskResponse(
            query=request.query,
            results=result_dicts,
            total_results=len(result_dicts),
        )
    except Exception as exc:
        _logger.exception("RAG query failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Knowledge base query failed",
        ) from exc


@router.post(
    "/ingest",
    response_model=RAGIngestResponse,
    summary="Ingest a document",
    status_code=status.HTTP_201_CREATED,
)
async def ingest_document(
    request: RAGIngestRequest,
    rag_service: Any = Depends(get_rag_service),  # noqa: B008
) -> RAGIngestResponse:
    try:
        from climatedt.models.rag import Document as RAGDocument

        doc = RAGDocument(
            title=request.title,
            source=request.source,
            content=request.content,
            content_type=request.content_type,
            tags=request.tags,
            metadata=request.metadata,
        )

        chunks = await rag_service.ingest(doc)

        return RAGIngestResponse(
            document_id=doc.document_id,
            chunks_created=len(chunks),
            title=doc.title,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Document ingestion failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document ingestion failed",
        ) from exc


@router.post(
    "/ingest/batch",
    response_model=BatchIngestResponse,
    summary="Batch ingest documents",
    status_code=status.HTTP_201_CREATED,
)
async def ingest_documents_batch(
    request: BatchIngestRequest,
    rag_service: Any = Depends(get_rag_service),  # noqa: B008
) -> BatchIngestResponse:
    try:
        from climatedt.models.rag import Document as RAGDocument

        documents: list[RAGDocument] = []
        for doc_req in request.documents:
            documents.append(
                RAGDocument(
                    title=doc_req.title,
                    source=doc_req.source,
                    content=doc_req.content,
                    content_type=doc_req.content_type,
                    tags=doc_req.tags,
                    metadata=doc_req.metadata,
                )
            )

        results = await rag_service.ingest_batch(documents)

        response_results: dict[str, RAGIngestResponse] = {}
        total_chunks = 0
        for doc in documents:
            doc_chunks = results.get(doc.document_id, [])
            response_results[doc.document_id] = RAGIngestResponse(
                document_id=doc.document_id,
                chunks_created=len(doc_chunks),
                title=doc.title,
            )
            total_chunks += len(doc_chunks)

        return BatchIngestResponse(
            results=response_results,
            total_documents=len(documents),
            total_chunks=total_chunks,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Batch ingestion failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch ingestion failed",
        ) from exc


@router.post(
    "/context",
    response_model=RAGContextResponse,
    summary="Get context for a query",
)
async def get_context(
    request: RAGContextRequest,
    rag_service: Any = Depends(get_rag_service),  # noqa: B008
) -> RAGContextResponse:
    try:
        context = await rag_service.get_context(
            query=request.query,
            max_tokens=request.max_tokens,
        )

        sources = context.count("---") + 1 if context else 0

        return RAGContextResponse(
            query=request.query,
            context=context,
            sources=sources,
        )
    except Exception as exc:
        _logger.exception("Context retrieval failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Context retrieval failed",
        ) from exc


@router.get(
    "/collections",
    summary="List knowledge base collections",
)
async def list_collections(
    rag_service: Any = Depends(get_rag_service),  # noqa: B008
) -> dict[str, list[dict[str, Any]]]:
    try:
        kb = rag_service.knowledge_base
        collections = kb.list_collections() if hasattr(kb, "list_collections") else []

        return {
            "collections": [
                {
                    "id": c.get("id", "") if isinstance(c, dict) else getattr(c, "collection_id", str(c)),
                    "name": c.get("name", "") if isinstance(c, dict) else getattr(c, "name", str(c)),
                    "chunk_count": c.get("chunk_count", 0) if isinstance(c, dict) else getattr(c, "chunk_count", 0),
                }
                for c in collections
            ]
        }
    except Exception as exc:
        _logger.exception("List collections failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list collections",
        ) from exc


@router.post(
    "/collections",
    response_model=dict[str, str],
    summary="Create a collection",
    status_code=status.HTTP_201_CREATED,
)
async def create_collection(
    request: CreateCollectionRequest,
    rag_service: Any = Depends(get_rag_service),  # noqa: B008
) -> dict[str, str]:
    try:
        kb = rag_service.knowledge_base
        if hasattr(kb, "create_collection"):
            collection_id = kb.create_collection(
                _name=request.name,
                _description=request.description,
            )
            return {"collection_id": collection_id, "name": request.name}
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Collection creation not supported",
        )
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("Create collection failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create collection",
        ) from exc


@router.get(
    "/collections/{collection_id}/stats",
    response_model=CollectionStatsResponse,
    summary="Get collection stats",
)
async def get_collection_stats(
    collection_id: str,
    rag_service: Any = Depends(get_rag_service),  # noqa: B008
) -> CollectionStatsResponse:
    try:
        kb = rag_service.knowledge_base
        stats = (
            await kb.get_collection_stats(collection_id)
            if hasattr(kb, "get_collection_stats")
            else {}
        )

        return CollectionStatsResponse(
            collection_id=collection_id,
            name=stats.get("name", ""),
            document_count=stats.get("document_count", 0),
            chunk_count=stats.get("chunk_count", 0),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Collection stats retrieval failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get collection stats",
        ) from exc


@router.post(
    "/search/{collection_id}",
    summary="Search within collection",
)
async def search_collection(
    collection_id: str,
    request: SearchCollectionRequest,
    rag_service: Any = Depends(get_rag_service),  # noqa: B008
) -> dict[str, Any]:
    try:
        kb = rag_service.knowledge_base
        results = await kb.search(
            query=request.query,
            k=request.k,
            _collection_id=collection_id,
        )

        return {
            "collection_id": collection_id,
            "query": request.query,
            "results": [
                {
                    "chunk_id": r.chunk.chunk_id,
                    "text": r.chunk.text[:500] if r.chunk.text else "",
                    "score": r.score,
                }
                for r in results
            ],
            "total": len(results),
        }
    except Exception as exc:
        _logger.exception("Collection search failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Collection search failed",
        ) from exc
