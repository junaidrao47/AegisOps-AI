"""
Log Ingestion API Routes - MODULE 3: Log Ingestion Engine

REST API endpoints for log ingestion operations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.db.models.user import User
from app.db.models.incident import Incident
from app.db.models.attachment import IncidentAttachment
from app.db.models.event import IncidentEvent
from app.db.session import get_db
from app.schemas.log_ingestion import (
    ChunkRead,
    FindingRead,
    FindingSummary,
    LogIngestBriefResponse,
    LogIngestRequest,
    LogIngestResponse,
    LogIngestionJobRead,
    LogIngestionStats,
    LogSourceDetectResponse,
    PipelineMetadata,
)
from app.services.log_ingestion import (
    Finding,
    LogSource,
    run_pipeline,
    run_pipeline_enhanced,
    classify_source_enhanced,
    detect_log_source,
)
from app.services.ingestion_service import trigger_auto_analysis
from app.services.log_ingestion.ingestion_service import LogIngestionService
from app.services.storage import read_text_file, save_upload


router = APIRouter()


def _utcnow() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def _get_incident_or_404(db: Session, incident_id: int, user: User) -> Incident:
    """Get incident or raise 404."""
    incident = db.get(Incident, incident_id)
    if not incident or incident.owner_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="incident_not_found"
        )
    return incident


def _convert_pipeline_result(
    result,
    include_chunks: bool = True,
    include_findings: bool = True,
) -> LogIngestResponse:
    """Convert PipelineResult to LogIngestResponse schema."""
    # Build findings summary
    summary = FindingSummary()
    for f in result.findings:
        if f.severity == "critical":
            summary.critical += 1
        elif f.severity == "high":
            summary.high += 1
        elif f.severity == "medium":
            summary.medium += 1
        elif f.severity == "low":
            summary.low += 1
        summary.total += 1

    # Convert findings
    findings_list = []
    if include_findings:
        findings_list = [
            FindingRead(
                category=f.category,
                severity=f.severity,
                title=f.title,
                evidence=f.evidence,
                source_type=f.source_type,
                confidence=f.confidence,
                timestamp=f.timestamp,
            )
            for f in result.findings
        ]

    # Convert chunks
    chunks_list = []
    if include_chunks:
        chunks_list = [
            ChunkRead(
                index=c.index,
                text=c.text,
                start_line=c.start_line,
                end_line=c.end_line,
                checksum=c.checksum,
            )
            for c in result.chunks
        ]

    # Convert metadata
    metadata = PipelineMetadata(
        classification_confidence=result.metadata.get("classification_confidence"),
        classification_source=result.metadata.get("classification_source"),
        parser_source=result.metadata.get("parser_source"),
        parser_metadata=result.metadata.get("parser_metadata", {}),
        incident_id=result.metadata.get("incident_id"),
        attachment_id=result.metadata.get("attachment_id"),
    )

    return LogIngestResponse(
        success=True,
        source_type=result.source_type,
        total_lines=result.total_lines,
        parsed_lines=result.parsed_lines,
        failed_lines=result.failed_lines,
        chunks_count=len(result.chunks),
        findings_count=len(result.findings),
        findings_summary=summary,
        findings=findings_list,
        chunks=chunks_list,
        processing_time_ms=result.processing_time_ms,
        metadata=metadata,
    )


def _convert_pipeline_result_brief(result) -> LogIngestBriefResponse:
    """Convert PipelineResult to LogIngestBriefResponse schema."""
    # Build findings summary
    summary = FindingSummary()
    for f in result.findings:
        if f.severity == "critical":
            summary.critical += 1
        elif f.severity == "high":
            summary.high += 1
        elif f.severity == "medium":
            summary.medium += 1
        elif f.severity == "low":
            summary.low += 1
        summary.total += 1

    # Get critical and high findings
    critical_findings = [
        FindingRead(
            category=f.category,
            severity=f.severity,
            title=f.title,
            evidence=f.evidence,
            source_type=f.source_type,
            confidence=f.confidence,
            timestamp=f.timestamp,
        )
        for f in result.findings
        if f.severity in ("critical", "high")
    ]

    high_findings = [
        FindingRead(
            category=f.category,
            severity=f.severity,
            title=f.title,
            evidence=f.evidence,
            source_type=f.source_type,
            confidence=f.confidence,
            timestamp=f.timestamp,
        )
        for f in result.findings
        if f.severity == "high"
    ]

    # Determine message based on findings
    message = None
    if result.has_critical_issues:
        message = f"Critical issues detected: {len(result.critical_findings)} critical findings"
    elif summary.high > 0:
        message = f"High severity issues detected: {summary.high} high findings"
    elif summary.total > 0:
        message = f"{summary.total} issues detected"
    else:
        message = "No issues detected"

    return LogIngestBriefResponse(
        success=True,
        source_type=result.source_type,
        total_lines=result.total_lines,
        parsed_lines=result.parsed_lines,
        failed_lines=result.failed_lines,
        chunks_count=len(result.chunks),
        findings_count=len(result.findings),
        findings_summary=summary,
        critical_findings=critical_findings,
        high_findings=high_findings,
        processing_time_ms=result.processing_time_ms,
        message=message,
    )


# ============================================================================
# Log Processing Endpoints
# ============================================================================

@router.post("/logs/process", response_model=LogIngestResponse, tags=["logs"])
def process_log_text(
    payload: LogIngestRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LogIngestResponse:
    """
    Process raw log text through the ingestion pipeline.

    This endpoint accepts raw log text and processes it through the complete
    pipeline: parsing, cleaning, chunking, classification, and AI-powered
    issue detection.

    **Supported log sources:**
    - Kubernetes logs
    - Docker logs
    - Nginx logs
    - Apache logs
    - Jenkins logs
    - GitHub Actions logs
    - Terraform output
    - AWS CloudWatch exports

    **Detected issues:**
    - CrashLoopBackOff
    - OOMKilled
    - DNS failures
    - Connection timeouts
    - SSL failures
    - Memory leaks
    - CPU spikes
    - Build failures
    """
    # Verify incident access if incident_id provided
    if payload.incident_id:
        _get_incident_or_404(db, payload.incident_id, user)

    # Determine force source type
    force_source = None
    if payload.source_type:
        force_source = LogSource(payload.source_type.value)

    # Run pipeline
    result = run_pipeline_enhanced(
        payload.log_text,
        incident_id=payload.incident_id,
    )

    return _convert_pipeline_result(result)


@router.post("/logs/process-brief", response_model=LogIngestBriefResponse, tags=["logs"])
def process_log_text_brief(
    payload: LogIngestRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LogIngestBriefResponse:
    """
    Process raw log text and return a brief response.

    Returns only summary information and critical/high severity findings.
    Useful for quick analysis without transferring large amounts of data.
    """
    # Verify incident access if incident_id provided
    if payload.incident_id:
        _get_incident_or_404(db, payload.incident_id, user)

    # Run pipeline
    result = run_pipeline_enhanced(
        payload.log_text,
        incident_id=payload.incident_id,
    )

    return _convert_pipeline_result_brief(result)


@router.post("/logs/detect-source", response_model=LogSourceDetectResponse, tags=["logs"])
def detect_log_source_endpoint(
    payload: LogIngestRequest,
    user: User = Depends(get_current_user),
) -> LogSourceDetectResponse:
    """
    Detect the source type of log text.

    Analyzes the log text and returns the detected source type with
    a confidence score.
    """
    # Use enhanced classification
    source, confidence = classify_source_enhanced(payload.log_text)

    # Count matches for each source type
    all_matches: dict[str, int] = {}
    sample = payload.log_text[:200_000]
    from app.services.log_ingestion.pipeline import _SOURCE_RULES
    for name, pat in _SOURCE_RULES:
        matches = pat.findall(sample)
        if matches:
            all_matches[name] = len(matches)

    return LogSourceDetectResponse(
        detected_source=source,
        confidence=confidence,
        all_matches=all_matches,
    )


# ============================================================================
# File Upload Endpoints
# ============================================================================

@router.post("/logs/upload", response_model=LogIngestResponse, tags=["logs"])
def upload_and_process_log(
    incident_id: int = Form(..., description="Incident ID to associate with"),
    file: UploadFile = File(..., description="Log file to process"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LogIngestResponse:
    """
    Upload a log file and process it through the ingestion pipeline.

    The file will be stored and processed, with results saved to the database.
    Chunks and findings will be associated with the specified incident.
    """
    # Verify incident access
    incident = _get_incident_or_404(db, incident_id, user)

    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="missing_filename"
        )

    # Save the file
    storage_path, size_bytes = save_upload(
        user_id=user.id,
        incident_id=incident.id,
        kind="log",
        upload=file,
    )

    # Create attachment record
    attachment = IncidentAttachment(
        incident_id=incident.id,
        uploaded_by_user_id=user.id,
        kind="log",
        filename=file.filename or "file",
        content_type=file.content_type,
        storage_path=storage_path,
        size_bytes=size_bytes,
    )
    db.add(attachment)
    db.flush()

    # Read and process the log file
    try:
        raw_text = read_text_file(storage_path, max_chars=10_000_000)
        result = run_pipeline_enhanced(
            raw_text,
            incident_id=incident.id,
            attachment_id=attachment.id,
        )

        # Store results in database
        service = LogIngestionService(db)
        job, _ = service.process_and_store(
            raw_text,
            incident_id=incident.id,
            attachment_id=attachment.id,
        )

        # Update incident timestamp
        incident.updated_at = _utcnow()

        # Trigger auto-analysis hook (sync)
        ai_result = None
        if settings.orchestrator_auto_analyze_logs:
            ai_result = trigger_auto_analysis(
                raw_text,
                incident_id=incident.id,
                source_type=result.source_type.value if hasattr(result.source_type, 'value') else str(result.source_type),
            )
            if ai_result and incident:
                _store_ai_event(db, incident.id, ai_result)

        db.commit()

        return _convert_pipeline_result(result)

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"log_processing_failed: {str(e)}"
        )


def _store_ai_event(db: Session, incident_id: int, ai_result: dict) -> None:
    """Store AI analysis results as an incident event."""
    from datetime import datetime, timezone

    summary = ai_result.get("summary")
    recommendations = ai_result.get("recommendations", [])

    if not summary and not recommendations:
        return

    lines = []
    if summary:
        lines.append(f"Summary: {summary}")
    if recommendations:
        lines.append("Recommendations:")
        lines.extend([f"- {item}" for item in recommendations])

    event = IncidentEvent(
        incident_id=incident_id,
        occurred_at=datetime.now(timezone.utc),
        title="AI Auto-Analysis",
        detail="\n".join(lines),
        source="ai",
    )
    db.add(event)


@router.post("/logs/upload-brief", response_model=LogIngestBriefResponse, tags=["logs"])
def upload_and_process_log_brief(
    incident_id: int = Form(..., description="Incident ID to associate with"),
    file: UploadFile = File(..., description="Log file to process"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LogIngestBriefResponse:
    """
    Upload a log file and return a brief processing result.

    Same as upload_and_process_log but returns only summary information.
    """
    # Verify incident access
    incident = _get_incident_or_404(db, incident_id, user)

    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="missing_filename"
        )

    # Save the file
    storage_path, size_bytes = save_upload(
        user_id=user.id,
        incident_id=incident.id,
        kind="log",
        upload=file,
    )

    # Create attachment record
    attachment = IncidentAttachment(
        incident_id=incident.id,
        uploaded_by_user_id=user.id,
        kind="log",
        filename=file.filename or "file",
        content_type=file.content_type,
        storage_path=storage_path,
        size_bytes=size_bytes,
    )
    db.add(attachment)
    db.flush()

    # Read and process the log file
    try:
        raw_text = read_text_file(storage_path, max_chars=10_000_000)
        result = run_pipeline_enhanced(
            raw_text,
            incident_id=incident.id,
            attachment_id=attachment.id,
        )

        # Store results in database
        service = LogIngestionService(db)
        job, _ = service.process_and_store(
            raw_text,
            incident_id=incident.id,
            attachment_id=attachment.id,
        )

        # Update incident timestamp
        incident.updated_at = _utcnow()

        # Trigger auto-analysis hook (sync) for brief uploads too
        ai_result = None
        if settings.orchestrator_auto_analyze_logs:
            ai_result = trigger_auto_analysis(
                raw_text,
                incident_id=incident.id,
                source_type=result.source_type.value if hasattr(result.source_type, 'value') else str(result.source_type),
            )
            if ai_result:
                _store_ai_event(db, incident.id, ai_result)

        db.commit()

        return _convert_pipeline_result_brief(result)

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"log_processing_failed: {str(e)}"
        )


# ============================================================================
# Job Management Endpoints
# ============================================================================

@router.get("/logs/jobs", response_model=list[LogIngestionJobRead], tags=["logs"])
def list_ingestion_jobs(
    incident_id: int = Query(None, description="Filter by incident ID"),
    status: str = Query(None, description="Filter by status (queued|running|succeeded|failed)"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[LogIngestionJobRead]:
    """
    List log ingestion jobs.

    Can be filtered by incident ID and/or status.
    """
    service = LogIngestionService(db)

    if incident_id:
        # Verify incident access
        _get_incident_or_404(db, incident_id, user)
        jobs = service.get_jobs_by_incident(incident_id, status)
    else:
        # Get all jobs for user's incidents
        from sqlalchemy import select
        from app.db.models.incident import Incident
        user_incidents = db.execute(
            select(Incident.id).where(Incident.owner_user_id == user.id)
        ).scalars().all()

        if not user_incidents:
            return []

        jobs = []
        for inc_id in user_incidents:
            jobs.extend(service.get_jobs_by_incident(inc_id, status))

        # Sort by created_at descending
        jobs.sort(key=lambda j: j.created_at, reverse=True)

    return jobs


@router.get("/logs/jobs/{job_id}", response_model=LogIngestionJobRead, tags=["logs"])
def get_ingestion_job(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LogIngestionJobRead:
    """
    Get details of a specific ingestion job.
    """
    service = LogIngestionService(db)
    job = service.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="job_not_found"
        )

    # Verify access
    _get_incident_or_404(db, job.incident_id, user)

    return job


@router.get("/logs/jobs/{job_id}/chunks", response_model=list[ChunkRead], tags=["logs"])
def get_job_chunks(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ChunkRead]:
    """
    Get all chunks for an ingestion job.
    """
    service = LogIngestionService(db)
    job = service.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="job_not_found"
        )

    # Verify access
    _get_incident_or_404(db, job.incident_id, user)

    chunks = service.get_chunks_by_job(job_id)
    return [
        ChunkRead(
            index=c.chunk_index,
            text=c.text,
            start_line=0,
            end_line=0,
            checksum="",
        )
        for c in chunks
    ]


@router.get("/logs/jobs/{job_id}/findings", response_model=list[FindingRead], tags=["logs"])
def get_job_findings(
    job_id: int,
    severity: str = Query(None, description="Filter by severity"),
    category: str = Query(None, description="Filter by category"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[FindingRead]:
    """
    Get all findings for an ingestion job.
    """
    service = LogIngestionService(db)
    job = service.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="job_not_found"
        )

    # Verify access
    _get_incident_or_404(db, job.incident_id, user)

    findings = service.get_findings_by_job(job_id)

    # Filter if needed
    if severity:
        findings = [f for f in findings if f.severity == severity]
    if category:
        findings = [f for f in findings if f.category == category]

    return [
        FindingRead(
            category=f.category,
            severity=f.severity,
            title=f.title,
            evidence=f.evidence,
            source_type=f.source_type or "",
            confidence=1.0,
            timestamp=f.created_at,
        )
        for f in findings
    ]


# ============================================================================
# Statistics Endpoints
# ============================================================================

@router.get("/logs/stats", response_model=LogIngestionStats, tags=["logs"])
def get_log_ingestion_stats(
    incident_id: int = Query(None, description="Filter by incident ID"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LogIngestionStats:
    """
    Get log ingestion statistics.

    Returns counts of jobs, chunks, and findings with breakdowns by
    severity and category.
    """
    service = LogIngestionService(db)

    if incident_id:
        # Verify incident access
        _get_incident_or_404(db, incident_id, user)

    stats = service.get_stats(incident_id)
    return LogIngestionStats(**stats)


@router.get("/logs/critical-findings", response_model=list[FindingRead], tags=["logs"])
def get_critical_findings(
    incident_id: int = Query(None, description="Filter by incident ID"),
    limit: int = Query(10, ge=1, le=100, description="Maximum findings to return"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[FindingRead]:
    """
    Get critical and high severity findings.

    Useful for dashboards and alerts.
    """
    service = LogIngestionService(db)

    if incident_id:
        # Verify incident access
        _get_incident_or_404(db, incident_id, user)

    findings = service.get_critical_findings(incident_id, limit)
    return [
        FindingRead(
            category=f.category,
            severity=f.severity,
            title=f.title,
            evidence=f.evidence,
            source_type=f.source_type or "",
            confidence=1.0,
            timestamp=f.created_at,
        )
        for f in findings
    ]