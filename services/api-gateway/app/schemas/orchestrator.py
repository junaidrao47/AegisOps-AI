from __future__ import annotations

from pydantic import BaseModel, Field


class OrchestratorAnalyzeRequest(BaseModel):
    """Request schema for orchestrator analysis."""

    incident_id: int | None = None
    log_text: str | None = None
    incident_type: str | None = None
    summary: str | None = None
    rag_query: str | None = None
    tags: list[str] = Field(default_factory=list)


class AgentResultRead(BaseModel):
    """Schema for individual agent results."""

    summary: str
    findings: list[str]
    confidence: float
    evidence: list[str]


class OrchestratorAnalyzeResponse(BaseModel):
    """Response schema for orchestrator analysis."""

    incident_id: int | None
    summary: str | None
    recommendations: list[str]
    agent_results: dict[str, AgentResultRead]
    errors: list[str]


class OrchestratorHealthResponse(BaseModel):
    """Health status response for the orchestrator."""

    enabled: bool
    available: bool
    path: str
    auto_analyze_logs: bool