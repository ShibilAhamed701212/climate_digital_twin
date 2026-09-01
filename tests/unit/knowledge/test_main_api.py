"""Unit tests for the FastAPI main app."""

from unittest.mock import MagicMock, patch


class TestMainAPI:
    def test_app_creation(self):
        from knowledge.api.main import app

        assert app.title == "RAG Knowledge API"
        assert app.version == "2.1.0"

    def test_health_endpoint(self):
        from fastapi.testclient import TestClient

        from knowledge.api.main import app

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "rag-service"

    @patch("knowledge.api.main._get_api")
    def test_search_endpoint(self, mock_get_api):
        from fastapi.testclient import TestClient

        from knowledge.api.main import app
        from knowledge.models import SearchResult

        mock_api = MagicMock()
        mock_api.search.return_value = [
            SearchResult(
                chunk_id="c1",
                document_id="d1",
                title="Doc",
                source="src",
                category="general",
                content="text",
                score=0.9,
                chunk_number=1,
            ),
        ]
        mock_get_api.return_value = mock_api
        client = TestClient(app)
        response = client.post("/search", json={"query": "test", "top_k": 3})
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "test"
        assert data["total_results"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["chunk_id"] == "c1"

    @patch("knowledge.api.main._get_api")
    def test_search_category_filter(self, mock_get_api):
        from fastapi.testclient import TestClient

        from knowledge.api.main import app
        from knowledge.models import SearchResult

        mock_api = MagicMock()
        mock_api.search.return_value = [
            SearchResult(
                chunk_id="c1",
                document_id="d1",
                title="Doc",
                source="src",
                category="disaster",
                content="text",
                score=0.9,
                chunk_number=1,
            ),
            SearchResult(
                chunk_id="c2",
                document_id="d2",
                title="Other",
                source="src",
                category="general",
                content="text",
                score=0.8,
                chunk_number=1,
            ),
        ]
        mock_get_api.return_value = mock_api
        client = TestClient(app)
        response = client.post(
            "/search", json={"query": "test", "top_k": 3, "category": "disaster"}
        )
        assert response.status_code == 200
        assert response.json()["total_results"] == 1
        assert response.json()["results"][0]["chunk_id"] == "c1"

    @patch("knowledge.api.main._get_api")
    def test_search_endpoint_error(self, mock_get_api):
        from fastapi.testclient import TestClient

        from knowledge.api.main import app

        mock_api = MagicMock()
        mock_api.search.side_effect = RuntimeError("search failed")
        mock_get_api.return_value = mock_api
        client = TestClient(app)
        response = client.post("/search", json={"query": "test", "top_k": 3})
        assert response.status_code == 500
        assert "search failed" in response.json()["detail"]

    @patch("knowledge.api.main._get_api")
    def test_search_endpoint_empty_query(self, mock_get_api):
        from fastapi.testclient import TestClient

        from knowledge.api.main import app

        mock_api = MagicMock()
        mock_api.search.return_value = []
        mock_get_api.return_value = mock_api
        client = TestClient(app)
        response = client.post("/search", json={"query": "", "top_k": 3})
        assert response.status_code == 200
        assert response.json()["total_results"] == 0

    @patch("knowledge.api.main._get_api")
    def test_search_endpoint_negative_top_k(self, mock_get_api):
        from fastapi.testclient import TestClient

        from knowledge.api.main import app

        mock_api = MagicMock()
        mock_api.search.return_value = []
        mock_get_api.return_value = mock_api
        client = TestClient(app)
        response = client.post("/search", json={"query": "test", "top_k": -1})
        assert response.status_code == 200
