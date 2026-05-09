from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


def validate_upload(filename: str) -> None:
    """Validate that a filename is provided."""
    if not filename:
        raise ValueError("filename is required")


def trigger_auto_analysis(
    log_text: str,
    incident_id: int | None = None,
    source_type: str | None = None,
) -> dict[str, Any] | None:
    """
    Trigger automatic AI analysis after log ingestion.

    This function is called as a hook after logs are uploaded and processed.
    It checks if auto-analysis is enabled and runs the orchestrator.

    Args:
        log_text: The processed log text to analyze
        incident_id: Optional incident ID to associate with the analysis
        source_type: The detected log source type (kubernetes, docker, nginx, etc.)

    Returns:
        Analysis results if auto-analysis is enabled and successful, None otherwise
    """
    if not settings.orchestrator_auto_analyze_logs:
        logger.info("Auto-analysis disabled, skipping orchestrator")
        return None

    if not log_text:
        logger.warning("No log text provided for auto-analysis")
        return None

    try:
        from app.services.orchestrator import run_orchestrator

        payload = {
            "incident_type": source_type,
            "log_text": log_text,
            "tags": ["auto-analysis", source_type] if source_type else ["auto-analysis"],
        }

        result = run_orchestrator(payload, incident_id=incident_id)
        logger.info(
            "Auto-analysis completed for incident %s",
            incident_id,
        )
        return result

    except RuntimeError as e:
        if "orchestrator_disabled" in str(e):
            logger.info("Orchestrator disabled, skipping auto-analysis")
        else:
            logger.error("Auto-analysis failed: %s", e)
        return None
    except Exception as e:
        logger.exception("Unexpected error during auto-analysis: %s", e)
        return None


def trigger_auto_analysis_async(
    log_text: str,
    incident_id: int | None = None,
    source_type: str | None = None,
) -> dict[str, Any] | None:
    """
    Trigger asynchronous automatic AI analysis after log ingestion.

    This function queues the analysis task and returns immediately.
    Useful for large log files or high-traffic scenarios.

    Args:
        log_text: The processed log text to analyze
        incident_id: Optional incident ID to associate with the analysis
        source_type: The detected log source type

    Returns:
        Task information if queued successfully, None otherwise
    """
    if not settings.orchestrator_auto_analyze_logs:
        logger.info("Auto-analysis disabled, skipping orchestrator")
        return None

    if not log_text:
        logger.warning("No log text provided for auto-analysis")
        return None

    try:
        from app.services.orchestrator import run_orchestrator_async

        payload = {
            "incident_type": source_type,
            "log_text": log_text,
            "tags": ["auto-analysis", source_type] if source_type else ["auto-analysis"],
        }

        result = run_orchestrator_async(payload, incident_id=incident_id)
        logger.info(
            "Auto-analysis task queued (task_id=%s) for incident %s",
            result.get("task_id"),
            incident_id,
        )
        return result

    except RuntimeError as e:
        if "orchestrator_disabled" in str(e):
            logger.info("Orchestrator disabled, skipping auto-analysis")
        else:
            logger.error("Auto-analysis queue failed: %s", e)
        return None
    except Exception as e:
        logger.exception("Unexpected error during auto-analysis queue: %s", e)
        return None