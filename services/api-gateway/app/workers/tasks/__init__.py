"""Celery tasks for async orchestrator processing."""

from __future__ import annotations

from app.workers.celery_app import celery_app


@celery_app.task(bind=True, name="app.workers.tasks.run_orchestrator_analysis")
def run_orchestrator_analysis(
    self,
    payload: dict,
    incident_id: int | None = None,
) -> dict:
    """
    Async task to run orchestrator analysis.

    This task is triggered when logs are uploaded and auto-analysis is enabled.
    """
    from app.services.orchestrator import run_orchestrator

    try:
        result = run_orchestrator(payload, incident_id=incident_id)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}