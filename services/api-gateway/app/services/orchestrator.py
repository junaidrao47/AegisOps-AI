from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from app.core.config import settings

# Cache for imported modules to avoid repeated imports
_orchestrator_modules = None


def run_orchestrator(payload: dict[str, Any], incident_id: int | None = None) -> dict[str, Any]:
    """
    Run the AI orchestrator to analyze an incident.

    This function imports the orchestrator as a Python library and executes
    the orchestration graph with the provided payload.

    Args:
        payload: Dictionary containing incident data (logs, incident_type, etc.)
        incident_id: Optional incident ID for tracking

    Returns:
        Dictionary containing analysis results including summary, recommendations,
        and agent results.

    Raises:
        RuntimeError: If orchestrator is disabled or import fails
    """
    if not settings.orchestrator_enabled:
        raise RuntimeError("orchestrator_disabled")

    _ensure_orchestrator_path()
    _import_orchestrator_modules()

    ctx = _orchestrator_modules["IncidentContext"](
        incident_id=str(incident_id or "unknown"),
        payload=payload
    )
    result = _orchestrator_modules["build_graph"]()(ctx)

    return {
        "incident_id": incident_id,
        "summary": result.summary,
        "recommendations": result.recommendations or [],
        "agent_results": {
            key: {
                "summary": value.summary,
                "findings": value.findings,
                "confidence": value.confidence,
                "evidence": value.evidence,
            }
            for key, value in result.agent_results.items()
        },
        "errors": result.errors,
    }


def run_orchestrator_async(
    payload: dict[str, Any],
    incident_id: int | None = None,
) -> dict[str, Any]:
    """
    Run orchestrator analysis asynchronously via Celery.

    This function queues the analysis task and returns immediately with a task ID.
    The caller can poll for results using the task ID.

    Args:
        payload: Dictionary containing incident data
        incident_id: Optional incident ID for tracking

    Returns:
        Dictionary with task_id for polling results
    """
    from app.workers.tasks import run_orchestrator_analysis

    task = run_orchestrator_analysis.delay(payload, incident_id)
    return {"task_id": task.id, "status": "queued"}


def is_orchestrator_available() -> bool:
    """
    Check if the orchestrator is available and can be imported.

    Returns:
        True if orchestrator is available, False otherwise
    """
    if not settings.orchestrator_enabled:
        return False

    try:
        _ensure_orchestrator_path()
        _import_orchestrator_modules()
        return True
    except Exception:
        return False


def get_orchestrator_health() -> dict[str, Any]:
    """
    Get health status of the orchestrator.

    Returns:
        Dictionary with health status information
    """
    available = is_orchestrator_available()
    return {
        "enabled": settings.orchestrator_enabled,
        "available": available,
        "path": str(Path(settings.orchestrator_path).resolve()),
        "auto_analyze_logs": settings.orchestrator_auto_analyze_logs,
    }


def _import_orchestrator_modules() -> None:
    """Import and cache orchestrator modules."""
    global _orchestrator_modules
    if _orchestrator_modules is not None:
        return

    try:
        from aegis_ai.orchestration.graph import build_graph
        from aegis_ai.orchestration.state import IncidentContext

        _orchestrator_modules = {
            "build_graph": build_graph,
            "IncidentContext": IncidentContext,
        }
    except Exception as exc:  # pragma: no cover - import guard
        raise RuntimeError(f"orchestrator_import_failed: {exc}") from exc


def _ensure_orchestrator_path() -> None:
    """Add orchestrator path to sys.path if not already present."""
    path = Path(settings.orchestrator_path).resolve()
    if not path.exists():
        return
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def reset_orchestrator_cache() -> None:
    """
    Reset the orchestrator module cache.

    Useful for testing or when the orchestrator code changes.
    """
    global _orchestrator_modules
    _orchestrator_modules = None