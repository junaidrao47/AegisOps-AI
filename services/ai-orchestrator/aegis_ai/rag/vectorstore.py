from __future__ import annotations

from aegis_ai.common.config import settings
from aegis_ai.integrations.chroma_client import get_chroma_client
from aegis_ai.rag.embeddings import get_embedding_function


def get_vectorstore():
    """Return the ChromaDB collection used for knowledge retrieval."""

    client = get_chroma_client()
    embedding_fn = get_embedding_function()
    return client.get_or_create_collection(
        name=settings.chroma_collection,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )
