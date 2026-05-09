from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.db.models.attachment import IncidentAttachment
from app.db.models.event import IncidentEvent
from app.db.models.incident import Incident
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.orchestrator import (
    OrchestratorAnalyzeRequest,
    OrchestratorAnalyzeResponse,
    OrchestratorHealthResponse,
)
from app.services.orchestrator import (
    get_orchestrator_health,
    run_orchestrator,
    run_orchestrator_async,
)
from app.services.storage import read_text_file

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_incident_or_404(db: Session, incident_id: int, user: User) -> Incident:
    incident = db.get(Incident, incident_id)
    if not incident or incident.owner_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="incident_not_found")
    return incident


@router.post("/orchestrator/analyze", response_model=OrchestratorAnalyzeResponse, tags=["orchestrator"])
def analyze_incident(
    payload: OrchestratorAnalyzeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrchestratorAnalyzeResponse:
    """
    Analyze an incident using the AI Orchestrator.

    This endpoint runs the full orchestration pipeline including:
    - Log analysis
    - Kubernetes/Docker issue detection
    - CI/CD pipeline analysis
    - Security scanning
    - Documentation retrieval
    - Remediation recommendations

    Args:
        payload: Analysis request containing log text, incident type, and optional incident ID
        db: Database session
        user: Current authenticated user

    Returns:
        Analysis results with summary, recommendations, and detailed agent findings
    """
    if not settings.orchestrator_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="orchestrator_disabled")

    incident: Incident | None = None
    if payload.incident_id:
        incident = _get_incident_or_404(db, payload.incident_id, user)

    log_text = payload.log_text
    if not log_text and incident:
        log_text = _load_latest_log(db, incident.id)

    request_payload = {
        "incident_type": payload.incident_type or (incident.environment if incident else None),
        "summary": payload.summary or (incident.title if incident else None),
        "description": incident.description if incident else None,
        "severity": incident.severity if incident else None,
        "service_name": incident.service_name if incident else None,
        "deployment_version": incident.deployment_version if incident else None,
        "tags": payload.tags,
        "log_text": log_text,
        "rag_query": payload.rag_query,
    }

    result = run_orchestrator(request_payload, incident_id=payload.incident_id)

    if incident:
        _store_ai_event(db, incident.id, result)

    return OrchestratorAnalyzeResponse(**result)


@router.post("/orchestrator/analyze-async", response_model=dict, tags=["orchestrator"])
def analyze_incident_async(
    payload: OrchestratorAnalyzeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """
    Analyze an incident asynchronously using the AI Orchestrator.

    This endpoint queues the analysis task and returns immediately with a task ID.
    Useful for large log files or when you don't want to wait for the full analysis.

    Args:
        payload: Analysis request containing log text, incident type, and optional incident ID
        db: Database session
        user: Current authenticated user

    Returns:
        Dictionary with task_id for polling results
    """
    if not settings.orchestrator_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="orchestrator_disabled")

    incident: Incident | None = None
    if payload.incident_id:
        incident = _get_incident_or_404(db, payload.incident_id, user)

    log_text = payload.log_text
    if not log_text and incident:
        log_text = _load_latest_log(db, incident.id)

    request_payload = {
        "incident_type": payload.incident_type or (incident.environment if incident else None),
        "summary": payload.summary or (incident.title if incident else None),
        "description": incident.description if incident else None,
        "severity": incident.severity if incident else None,
        "service_name": incident.service_name if incident else None,
        "deployment_version": incident.deployment_version if incident else None,
        "tags": payload.tags,
        "log_text": log_text,
        "rag_query": payload.rag_query,
    }

    result = run_orchestrator_async(request_payload, incident_id=payload.incident_id)

    return result


@router.get("/orchestrator/health", response_model=OrchestratorHealthResponse, tags=["orchestrator"])
def orchestrator_health(
    user: User = Depends(get_current_user),
) -> OrchestratorHealthResponse:
    """
    Get the health status of the AI Orchestrator.

    Returns information about:
    - Whether the orchestrator is enabled
    - Whether it's available (can be imported)
    - Configuration path
    - Auto-analysis settings

    Args:
        user: Current authenticated user

    Returns:
        Health status information
    """
    return OrchestratorHealthResponse(**get_orchestrator_health())


def _load_latest_log(db: Session, incident_id: int) -> str | None:
    attachment = db.execute(
        select(IncidentAttachment)
        .where(
            IncidentAttachment.incident_id == incident_id,
            IncidentAttachment.kind == "log",
        )
        .order_by(IncidentAttachment.created_at.desc())
        .limit(1)
    ).scalars().first()

    if not attachment:
        return None

    try:
        return read_text_file(attachment.storage_path, max_chars=5_000_000)
    except Exception:
        return None


def _store_ai_event(db: Session, incident_id: int, result: dict) -> None:
    summary = result.get("summary")
    recommendations = result.get("recommendations", [])
    detail = None
    if summary or recommendations:
        detail = _format_ai_detail(summary, recommendations)

    event = IncidentEvent(
        incident_id=incident_id,
        occurred_at=_utcnow(),
        title="AI Orchestrator Analysis",
        detail=detail,
        source="ai",
    )
    db.add(event)
    db.commit()


def _format_ai_detail(summary: str | None, recommendations: list[str]) -> str:
    lines = []
    if summary:
        lines.append(f"Summary: {summary}")
    if recommendations:
        lines.append("Recommendations:")
        lines.extend([f"- {item}" for item in recommendations])
    return "\n".join(lines)