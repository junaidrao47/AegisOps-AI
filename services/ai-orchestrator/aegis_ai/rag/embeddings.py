from __future__ import annotations

from functools import lru_cache
from typing import Iterable, List

from aegis_ai.common.config import settings


class SentenceTransformerEmbeddingFunction:
    """Chroma-compatible embedding function using sentence-transformers."""

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model = _get_model(model_name)

    def __call__(self, input: Iterable[str]) -> List[List[float]]:
        texts = list(input)
        if not texts:
            return []
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()


@lru_cache(maxsize=1)
def _get_model(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - import guard
        raise RuntimeError(
            "sentence-transformers is not installed. Install with 'pip install sentence-transformers'."
        ) from exc

    return SentenceTransformer(model_name)


def get_embedding_function() -> SentenceTransformerEmbeddingFunction:
    """Return a cached embedding function for the configured model."""

    return SentenceTransformerEmbeddingFunction(settings.embedding_model)
