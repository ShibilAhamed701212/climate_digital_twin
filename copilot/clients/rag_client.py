from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

RAG_SERVICE_URL = os.environ.get("RAG_SERVICE_URL", "http://rag-service:8004")
CLIENT_TIMEOUT = float(os.environ.get("CLIENT_TIMEOUT", "5"))


class RAGClient:
    def search(
        self, query: str, top_k: int = 3, timeout: float = CLIENT_TIMEOUT
    ) -> list[dict[str, Any]]:
        resp = requests.post(
            f"{RAG_SERVICE_URL}/search",
            json={"query": query, "top_k": top_k},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])
