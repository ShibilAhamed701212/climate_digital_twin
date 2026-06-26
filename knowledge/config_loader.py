"""Configuration loader for the RAG Knowledge Base.

Loads settings from rag.yaml with sensible defaults.
"""

from typing import Any

import yaml


def load_rag_config(config_path: str = "knowledge/configs/rag.yaml") -> dict[str, Any]:
    """Load RAG configuration from YAML file.

    Args:
        config_path: Path to rag.yaml config file.

    Returns:
        Dict with all configuration sections.
    """
    default = {
        "rag": {"chunk_size": 700, "chunk_overlap": 120, "embedding_model": "all-MiniLM-L6-v2", "embedding_dimension": 384},
        "retrieval": {"top_k": 5, "score_threshold": 0.5, "enable_metadata_filtering": True},
        "vector_store": {"type": "faiss", "index_path": "knowledge/vector_store/index.faiss", "metadata_path": "knowledge/vector_store/metadata.pkl"},
        "documents": {"base_path": "knowledge/documents", "supported_formats": ["pdf", "md", "txt", "csv", "json"]},
        "logging": {"log_path": "logs/rag.log", "log_level": "INFO"},
    }

    try:
        with open(config_path) as f:
            loaded = yaml.safe_load(f)
        if loaded:
            for section, values in loaded.items():
                if section in default:
                    default[section].update(values)
                else:
                    default[section] = values
    except FileNotFoundError:
        pass

    return default
