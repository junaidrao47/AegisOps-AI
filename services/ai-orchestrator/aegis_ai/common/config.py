import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("ENVIRONMENT", "local")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    chroma_path: str = os.getenv("CHROMA_PATH", "./.chroma")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


settings = Settings()
