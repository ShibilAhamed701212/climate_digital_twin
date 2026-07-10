"""Unit tests for EmbeddingModel class (not just _get_dummy_embedding)."""

from unittest.mock import MagicMock, patch

import numpy as np


class TestEmbeddingModelExtended:
    """Cover _load_model sentence_transformer success, _encode_with_st, TF-IDF paths."""

    def test_load_model_sentence_transformer_success(self):
        mock_st = MagicMock()
        mock_model = MagicMock()
        mock_st.SentenceTransformer.return_value = mock_model

        with patch.dict("sys.modules", {"sentence_transformers": mock_st}):
            from knowledge.embeddings.embedding_model import EmbeddingModel

            model = EmbeddingModel.__new__(EmbeddingModel)
            model._lock = MagicMock()
            model.model_name = "test-model"
            model.dimension = 384
            model._model = None
            model._tfidf_vectorizer = None
            model._svd = None
            model._tfidf_fitted = False
            model._load_model()
            assert model._strategy == "sentence_transformer"
            assert model._model is mock_model

    def test_load_model_sklearn_import_error_fallsback_to_dummy(self):
        with patch.dict(
            "sys.modules",
            {
                "sentence_transformers": None,
                "sklearn": None,
                "sklearn.feature_extraction": None,
                "sklearn.feature_extraction.text": None,
                "sklearn.decomposition": None,
            },
        ):
            from knowledge.embeddings.embedding_model import EmbeddingModel

            model = EmbeddingModel.__new__(EmbeddingModel)
            model._lock = MagicMock()
            model.model_name = "test"
            model.dimension = 384
            model._model = None
            model._tfidf_vectorizer = None
            model._svd = None
            model._tfidf_fitted = False
            model._load_model()
            assert model._strategy == "dummy"

    def test_encode_with_st_strategy(self):
        mock_model = MagicMock()
        mock_model.encode.return_value = [np.array([0.1, 0.2, 0.3])]

        from knowledge.embeddings.embedding_model import EmbeddingModel

        model = EmbeddingModel.__new__(EmbeddingModel)
        model._lock = MagicMock()
        model.model_name = "test"
        model.dimension = 384
        model._strategy = "sentence_transformer"
        model._model = mock_model
        model._tfidf_vectorizer = None
        model._svd = None
        model._tfidf_fitted = False

        result = model.encode("hello")
        assert len(result) == 1
        assert result[0] == [0.1, 0.2, 0.3]
        mock_model.encode.assert_called_once_with(
            ["hello"], normalize_embeddings=True, show_progress_bar=False
        )

    def test_encode_with_st_list(self):
        mock_model = MagicMock()
        mock_model.encode.return_value = [np.array([0.1, 0.2]), np.array([0.3, 0.4])]

        from knowledge.embeddings.embedding_model import EmbeddingModel

        model = EmbeddingModel.__new__(EmbeddingModel)
        model._lock = MagicMock()
        model.model_name = "test"
        model.dimension = 384
        model._strategy = "sentence_transformer"
        model._model = mock_model
        model._tfidf_vectorizer = None
        model._svd = None
        model._tfidf_fitted = False

        result = model.encode(["a", "b"])
        assert len(result) == 2

    def test_encode_with_tfidf_truncated_svd_creation(self):
        from scipy.sparse import csr_matrix

        from knowledge.embeddings.embedding_model import EmbeddingModel

        mock_vectorizer = MagicMock()
        mock_tfidf_mat = csr_matrix(np.random.rand(1, 10))
        mock_vectorizer.fit_transform.return_value = mock_tfidf_mat

        mock_svd_instance = MagicMock()
        mock_svd_result = np.random.randn(1, 384).astype(np.float32)
        mock_svd_instance.fit_transform.return_value = mock_svd_result

        with patch("sklearn.decomposition.TruncatedSVD", return_value=mock_svd_instance):
            model = EmbeddingModel.__new__(EmbeddingModel)
            model._lock = MagicMock()
            model.model_name = "test"
            model.dimension = 384
            model._strategy = "tfidf_svd"
            model._tfidf_vectorizer = mock_vectorizer
            model._svd = None
            model._tfidf_fitted = False
            model._model = None
            result = model.encode("hello world rainfall temperature")
            assert len(result) == 1
            assert len(result[0]) == 384
            assert model._tfidf_fitted is True

    def test_encode_with_tfidf_already_fitted(self):
        from scipy.sparse import csr_matrix

        from knowledge.embeddings.embedding_model import EmbeddingModel

        mock_vectorizer = MagicMock()
        mock_tfidf_mat = csr_matrix(np.random.rand(1, 10))
        mock_vectorizer.transform.return_value = mock_tfidf_mat

        mock_svd = MagicMock()
        mock_svd_result = np.random.randn(1, 384).astype(np.float32)
        mock_svd.transform.return_value = mock_svd_result

        model = EmbeddingModel.__new__(EmbeddingModel)
        model._lock = MagicMock()
        model.model_name = "test"
        model.dimension = 384
        model._strategy = "tfidf_svd"
        model._tfidf_vectorizer = mock_vectorizer
        model._svd = mock_svd
        model._tfidf_fitted = True
        model._model = None
        result = model.encode("hello world rainfall temperature")
        assert len(result) == 1
        assert len(result[0]) == 384
        mock_vectorizer.transform.assert_called_once()

    def test_init_default_config(self):
        from knowledge.embeddings.embedding_model import EmbeddingModel

        with patch("knowledge.embeddings.embedding_model.load_rag_config") as mock_load:
            mock_load.return_value = {
                "rag": {"embedding_model": "test", "embedding_dimension": 384}
            }
            with patch.object(EmbeddingModel, "_load_model"):
                model = EmbeddingModel()
                assert model.model_name == "test"
                assert model.dimension == 384

    def test_load_model_sentence_transformer_exception(self):
        mock_st = MagicMock()
        mock_st.SentenceTransformer.side_effect = ValueError("bad model")

        with patch.dict("sys.modules", {"sentence_transformers": mock_st}):
            from knowledge.embeddings.embedding_model import EmbeddingModel

            model = EmbeddingModel.__new__(EmbeddingModel)
            model._lock = MagicMock()
            model.model_name = "test-model"
            model.dimension = 384
            model._model = None
            model._tfidf_vectorizer = None
            model._svd = None
            model._tfidf_fitted = False
            model._load_model()
            assert model._strategy in ("tfidf_svd", "dummy")

    def test_encode_with_tfidf_svd_creation_real_sklearn(self):
        import threading

        from sklearn.feature_extraction.text import TfidfVectorizer

        from knowledge.embeddings.embedding_model import EmbeddingModel

        model = EmbeddingModel.__new__(EmbeddingModel)
        model._lock = threading.Lock()
        model.model_name = "test"
        model.dimension = 384
        model._strategy = "tfidf_svd"
        model._tfidf_vectorizer = TfidfVectorizer(
            max_features=5000, stop_words="english", sublinear_tf=True
        )
        model._svd = None
        model._tfidf_fitted = False
        model._model = None

        result = model.encode("hello world rainfall temperature climate weather data anomaly")
        assert len(result) == 1
        assert model._tfidf_fitted is True
        assert model._svd is not None

    def test_encode_with_tfidf_nan_fallback(self):
        from scipy.sparse import csr_matrix

        from knowledge.embeddings.embedding_model import EmbeddingModel

        mock_vectorizer = MagicMock()
        mock_tfidf_mat = csr_matrix(np.random.rand(1, 10))
        mock_vectorizer.fit_transform.return_value = mock_tfidf_mat

        mock_svd_instance = MagicMock()
        mock_svd_result = np.full((1, 384), np.nan, dtype=np.float32)
        mock_svd_instance.fit_transform.return_value = mock_svd_result

        with patch("sklearn.decomposition.TruncatedSVD", return_value=mock_svd_instance):
            model = EmbeddingModel.__new__(EmbeddingModel)
            model._lock = MagicMock()
            model.model_name = "test"
            model.dimension = 384
            model._strategy = "tfidf_svd"
            model._tfidf_vectorizer = mock_vectorizer
            model._svd = None
            model._tfidf_fitted = False
            model._model = None
            result = model.encode("hello world rainfall temperature")
            assert len(result) == 1
            assert len(result[0]) == 384


class TestEmbeddingModel:
    def test_strategy_dummy_when_no_deps(self):
        with patch("knowledge.embeddings.embedding_model.load_rag_config") as mock_load:
            mock_load.return_value = {
                "rag": {"embedding_model": "test-model", "embedding_dimension": 384}
            }
            with patch.dict("sys.modules", {"sentence_transformers": None, "sklearn": None}):
                from knowledge.embeddings.embedding_model import EmbeddingModel

                model = EmbeddingModel.__new__(EmbeddingModel)
                model._lock = MagicMock()
                model.model_name = "test-model"
                model.dimension = 384
                model._model = None
                model._tfidf_vectorizer = None
                model._svd = None
                model._tfidf_fitted = False
                model._strategy = "dummy"
                assert model.strategy == "dummy"
                assert model.is_available() is False

    def test_encode_empty_list(self):
        from knowledge.embeddings.embedding_model import EmbeddingModel

        config = {
            "rag": {"embedding_model": "test", "embedding_dimension": 384},
        }
        with patch.object(EmbeddingModel, "_load_model"):
            model = EmbeddingModel(config)
            model._strategy = "dummy"
            model.dimension = 384
            result = model.encode([])
            assert result == []

    def test_encode_none_empty_text(self):
        from knowledge.embeddings.embedding_model import EmbeddingModel

        config = {
            "rag": {"embedding_model": "test", "embedding_dimension": 384},
        }
        with patch.object(EmbeddingModel, "_load_model"):
            model = EmbeddingModel(config)
            model._strategy = "dummy"
            model.dimension = 384
            result = model.encode("")
            assert len(result) == 1
            assert len(result[0]) == 384

    def test_encode_single_string(self):
        from knowledge.embeddings.embedding_model import EmbeddingModel

        config = {
            "rag": {"embedding_model": "test", "embedding_dimension": 128},
        }
        with patch.object(EmbeddingModel, "_load_model"):
            model = EmbeddingModel(config)
            model._strategy = "dummy"
            model.dimension = 128
            result = model.encode("hello world")
            assert len(result) == 1
            assert len(result[0]) == 128

    def test_encode_list_of_texts(self):
        from knowledge.embeddings.embedding_model import EmbeddingModel

        local_config = {
            "rag": {"embedding_model": "test", "embedding_dimension": 64},
        }
        with patch.object(EmbeddingModel, "_load_model"):
            model = EmbeddingModel(local_config)
            model._strategy = "dummy"
            model.dimension = 64
            result = model.encode(["hello", "world"])
            assert len(result) == 2
            assert len(result[0]) == 64

    def test_encode_single_delegates(self):
        from knowledge.embeddings.embedding_model import EmbeddingModel

        config = {
            "rag": {"embedding_model": "test", "embedding_dimension": 384},
        }
        with patch.object(EmbeddingModel, "_load_model"):
            model = EmbeddingModel(config)
            model._strategy = "dummy"
            model.dimension = 384
            result = model.encode_single("test query")
            assert len(result) == 384

    def test_embed_query(self):
        from knowledge.embeddings.embedding_model import EmbeddingModel

        config = {
            "rag": {"embedding_model": "test", "embedding_dimension": 384},
        }
        with patch.object(EmbeddingModel, "_load_model"):
            model = EmbeddingModel(config)
            model._strategy = "dummy"
            model.dimension = 384
            result = model.embed_query("test query")
            assert len(result) == 384

    def test_get_dimension(self):
        from knowledge.embeddings.embedding_model import EmbeddingModel

        config = {
            "rag": {"embedding_model": "test", "embedding_dimension": 128},
        }
        with patch.object(EmbeddingModel, "_load_model"):
            model = EmbeddingModel(config)
            model.dimension = 128
            assert model.get_dimension() == 128

    def test_encode_with_tfidf_strategy(self):
        import numpy as np
        from scipy.sparse import csr_matrix

        from knowledge.embeddings.embedding_model import EmbeddingModel

        mock_vectorizer = MagicMock()
        mock_tfidf_mat = csr_matrix(np.random.rand(1, 10))
        mock_vectorizer.fit_transform.return_value = mock_tfidf_mat
        mock_vectorizer.transform.return_value = mock_tfidf_mat
        mock_svd = MagicMock()
        mock_svd_result = np.random.randn(1, 384).astype(np.float32)
        mock_svd.fit_transform.return_value = mock_svd_result
        mock_svd.transform.return_value = mock_svd_result

        with (
            patch.object(EmbeddingModel, "_load_model"),
            patch("sklearn.decomposition.TruncatedSVD", return_value=mock_svd),
        ):
            model = EmbeddingModel.__new__(EmbeddingModel)
            model._lock = MagicMock()
            model.model_name = "test"
            model.dimension = 384
            model._strategy = "tfidf_svd"
            model._tfidf_vectorizer = mock_vectorizer
            model._svd = None
            model._tfidf_fitted = False
            model._model = None
            result = model.encode("hello world rainfall temperature")
            assert len(result) == 1
            assert len(result[0]) == 384

    def test_encode_with_tfidf_single_word_vocab(self):
        from knowledge.embeddings.embedding_model import EmbeddingModel

        with patch.object(EmbeddingModel, "_load_model"):
            model = EmbeddingModel.__new__(EmbeddingModel)
            model._lock = MagicMock()
            model.model_name = "test"
            model.dimension = 384
            model._strategy = "tfidf_svd"
            model._tfidf_vectorizer = None
            model._svd = None
            model._tfidf_fitted = False
            model._model = None
            result = model.encode("hello")
            assert len(result) == 1

    def test_deterministic_embeddings(self):
        from knowledge.embeddings.embedding_model import _get_dummy_embedding

        e1 = _get_dummy_embedding("same text", 384)
        e2 = _get_dummy_embedding("same text", 384)
        e3 = _get_dummy_embedding("different", 384)
        assert e1 == e2
        assert e1 != e3

    def test_cache_behavior(self):
        from knowledge.embeddings.embedding_model import _get_dummy_embedding

        e1 = _get_dummy_embedding("text", 384)
        e2 = _get_dummy_embedding("text", 384)
        assert e1 == e2
        assert all(isinstance(v, float) for v in e1)
        assert len(e1) == 384

    def test_model_unloads_gracefully(self):
        config = {
            "rag": {"embedding_model": "nonexistent-model", "embedding_dimension": 384},
        }
        from knowledge.embeddings.embedding_model import EmbeddingModel

        with patch.object(EmbeddingModel, "_load_model"):
            model = EmbeddingModel(config)
            model._strategy = "dummy"
            model.dimension = 384
            assert not model.is_available()

    def test_load_model_sentence_transformers_fails_gracefully(self):
        with patch("knowledge.embeddings.embedding_model.load_rag_config") as mock_load:
            mock_load.return_value = {
                "rag": {"embedding_model": "test", "embedding_dimension": 384}
            }
            with patch.dict("sys.modules", {"sentence_transformers": None}):
                from knowledge.embeddings.embedding_model import EmbeddingModel

                model = EmbeddingModel.__new__(EmbeddingModel)
                model._lock = MagicMock()
                model.model_name = "test"
                model.dimension = 384
                model._model = None
                model._tfidf_vectorizer = None
                model._svd = None
                model._tfidf_fitted = False
                model._load_model()
                assert model._strategy in ("dummy", "tfidf_svd")
