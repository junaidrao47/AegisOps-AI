import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("ENVIRONMENT", "local")
    database_url: str = os.getenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/aegisops")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_ttl_minutes: int = int(os.getenv("ACCESS_TOKEN_TTL_MINUTES", "15"))
    refresh_token_ttl_days: int = int(os.getenv("REFRESH_TOKEN_TTL_DAYS", "30"))
    jwt_issuer: str = os.getenv("JWT_ISSUER", "aegisops")

    github_client_id: str = os.getenv("GITHUB_CLIENT_ID", "")
    github_client_secret: str = os.getenv("GITHUB_CLIENT_SECRET", "")
    github_redirect_uri: str = os.getenv("GITHUB_REDIRECT_URI", "")

    incident_storage_path: str = os.getenv("INCIDENT_STORAGE_PATH", "./.data/incidents")
    max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))

    orchestrator_enabled: bool = os.getenv("ORCHESTRATOR_ENABLED", "true").lower() in {"1", "true", "yes"}
    orchestrator_path: str = os.getenv("ORCHESTRATOR_PATH", "../ai-orchestrator")
    orchestrator_auto_analyze_logs: bool = os.getenv("ORCHESTRATOR_AUTO_ANALYZE_LOGS", "true").lower() in {
        "1",
        "true",
        "yes",
    }


settings = Settings()
