"""Unit tests for the embedding model."""



class TestEmbeddingModel:
    def test_encode_single(self):
        from knowledge.embeddings import EmbeddingModel

        model = EmbeddingModel()
        emb = model.encode_single("test text")
        assert len(emb) > 0
        assert all(isinstance(v, float) for v in emb)

    def test_encode_list(self):
        from knowledge.embeddings import EmbeddingModel

        model = EmbeddingModel()
        embs = model.encode(["text one", "text two"])
        assert len(embs) == 2
        for emb in embs:
            assert len(emb) > 0

    def test_deterministic_dummy(self):
        from knowledge.embeddings.embedding_model import _get_dummy_embedding

        emb1 = _get_dummy_embedding("hello world", 384)
        emb2 = _get_dummy_embedding("hello world", 384)
        emb3 = _get_dummy_embedding("different", 384)
        assert emb1 == emb2
        assert emb1 != emb3

    def test_dummy_embedding_dimension(self):
        from knowledge.embeddings.embedding_model import _get_dummy_embedding

        emb = _get_dummy_embedding("test", 128)
        assert len(emb) == 128

    def test_embedding_values_float(self):
        from knowledge.embeddings import EmbeddingModel

        model = EmbeddingModel()
        emb = model.encode_single("test")
        assert all(0.0 <= v <= 1.0 for v in emb)
