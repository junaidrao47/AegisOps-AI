from dataclasses import dataclass
from typing import Any


@dataclass
class IncidentContext:
    """Shared state passed through the graph."""

    incident_id: str
    payload: dict[str, Any]
    summary: str | None = None
    recommendations: list[str] | None = None
