from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    agent: str
    summary: str
    findings: list[str] = field(default_factory=list)
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IncidentContext:
    """Shared state passed through the graph."""

    incident_id: str
    payload: dict[str, Any]
    summary: str | None = None
    recommendations: list[str] | None = None
    agent_results: dict[str, AgentResult] = field(default_factory=dict)
    shared_context: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
