from aegis_ai.common.config import settings


def get_llm():
    """Placeholder for Groq LLM client creation."""

    if not settings.groq_api_key:
        return None

    return None
