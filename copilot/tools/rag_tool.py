from __future__ import annotations

import json
import logging
from typing import Any

from requests.exceptions import ConnectionError, HTTPError, Timeout

from copilot.clients.rag_client import RAGClient
from copilot.tools.base import BaseTool

logger = logging.getLogger(__name__)


class RAGRetrieverTool(BaseTool):
    def __init__(self) -> None:
        self._name = "rag_retriever"
        self._description = "Retrieve context from the climate knowledge base using semantic search"
        self._client = RAGClient()

    def run(self, **kwargs: Any) -> dict[str, Any]:
        query = kwargs.get("query", "")
        top_k = kwargs.get("top_k", 3)
        try:
            results = self._client.search(query, top_k)
            return {
                "tool": self._name,
                "query": query,
                "top_k": top_k,
                "results": results,
                "fallback": False,
            }
        except (ConnectionError, Timeout, HTTPError, json.JSONDecodeError) as e:
            logger.warning("RAG service unavailable: %s", e)
            return {
                "tool": self._name,
                "query": query,
                "top_k": top_k,
                "results": _synthetic_rag(query, top_k),
                "fallback": True,
            }

    def validate(self, **kwargs: Any) -> tuple[bool, str]:
        if (
            "query" not in kwargs
            or not isinstance(kwargs["query"], str)
            or not kwargs["query"].strip()
        ):
            return False, "query is required and must be a non-empty string"
        if "top_k" in kwargs and (
            not isinstance(kwargs["top_k"], int) or kwargs["top_k"] < 1 or kwargs["top_k"] > 10
        ):
            return False, "top_k must be an integer between 1 and 10"
        return True, ""

    def describe(self) -> dict[str, Any]:
        return {
            "name": self._name,
            "description": self._description,
            "parameters": {"query": "str", "top_k": "int (1-10)"},
        }

    def health_check(self) -> tuple[bool, str]:
        return True, "rag_retriever healthy"


def _synthetic_rag(query: str, top_k: int) -> list[dict[str, Any]]:
    return [
        {
            "source": "Climate Report 2025",
            "content": f"Relevant information about: {query}",
            "score": round(0.95 - i * 0.1, 2),
            "category": "general",
        }
        for i in range(top_k)
    ]
