from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from knowledge.api.search_api import KnowledgeAPI

app = FastAPI(title="RAG Knowledge API", version="2.1.0")
_knowledge_api: KnowledgeAPI | None = None


def _get_api() -> KnowledgeAPI:
    global _knowledge_api
    if _knowledge_api is None:
        _knowledge_api = KnowledgeAPI()
    return _knowledge_api


class SearchRequest(BaseModel):
    query: str
    top_k: int = 3
    category: str | None = None
    source: str | None = None


class SearchResult(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    source: str
    category: str
    content: str
    score: float
    chunk_number: int = 0
    page_number: int = 0
    date: str = ""
    region: str = ""
    keywords: list[str] = []


class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: list[SearchResult]


@app.get("/health")
def health():
    return {"status": "healthy", "service": "rag-service", "version": "2.1.0"}


@app.post("/search", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    api = _get_api()
    try:
        results = api.search(query=req.query, top_k=req.top_k)
        if req.category:
            results = [r for r in results if r.category == req.category]
        if req.source:
            results = [r for r in results if r.source == req.source]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return SearchResponse(
        query=req.query,
        total_results=len(results),
        results=[SearchResult(**r.to_dict()) for r in results],
    )
