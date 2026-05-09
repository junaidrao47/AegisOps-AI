from __future__ import annotations

from pathlib import Path
from typing import Any

from aegis_ai.common.config import settings


def _require_chromadb() -> Any:
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
    except ImportError as exc:  # pragma: no cover - import guard
        raise RuntimeError(
            "ChromaDB is not installed. Install with 'pip install chromadb'."
        ) from exc

    return chromadb, ChromaSettings


def get_chroma_client():
    """Create a persistent ChromaDB client using the configured path."""

    chromadb, ChromaSettings = _require_chromadb()
    Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=settings.chroma_path,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
