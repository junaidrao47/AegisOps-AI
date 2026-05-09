import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("ENVIRONMENT", "local")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    chroma_path: str = os.getenv("CHROMA_PATH", "./.chroma")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    chroma_collection: str = os.getenv("CHROMA_COLLECTION", "aegisops_knowledge")
    rag_chunk_size: int = int(os.getenv("RAG_CHUNK_SIZE", "1200"))
    rag_chunk_overlap: int = int(os.getenv("RAG_CHUNK_OVERLAP", "150"))
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "5"))
    rag_max_doc_bytes: int = int(os.getenv("RAG_MAX_DOC_BYTES", "20000000"))
    rag_max_chunks: int = int(os.getenv("RAG_MAX_CHUNKS", "1000"))


settings = Settings()
