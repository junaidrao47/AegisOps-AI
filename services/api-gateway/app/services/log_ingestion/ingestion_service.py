"""
Log Ingestion Service - MODULE 3: Log Ingestion Engine

Service layer for log ingestion operations including database persistence.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from app.db.models.log_ingestion import LogIngestionJob
from app.db.models.log_chunk import LogChunk
from app.db.models.log_finding import LogFinding
from app.db.models.attachment import IncidentAttachment
from app.services.log_ingestion.pipeline import (
    Chunk,
    Finding,
    PipelineResult,
    run_pipeline,
    run_pipeline_enhanced,
)
from app.services.log_ingestion.parsers import LogSource, parse_logs
from app.services.storage import read_text_file


def _utcnow() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


class LogIngestionService:
    """
    Service for handling log ingestion operations.

    Provides methods for:
    - Processing raw log text
    - Storing results in database
    - Retrieving ingestion jobs and results
    - Generating statistics
    """

    def __init__(self, db: Session):
        self.db = db

    # ========================================================================
    # Core Ingestion Methods
    # ========================================================================

    def process_log_text(
        self,
        raw_text: str,
        incident_id: int | None = None,
        attachment_id: int | None = None,
        force_source_type: LogSource | None = None,
    ) -> PipelineResult:
        """
        Process raw log text through the pipeline.

        Args:
            raw_text: Raw log text to process
            incident_id: Optional incident ID for association
            attachment_id: Optional attachment ID for association
            force_source_type: Optional forced log source type

        Returns:
            PipelineResult with all processed data
        """
        if force_source_type:
            # Use forced source type
            parsed_batch = parse_logs(raw_text, force_source=force_source_type)
            # Build result manually
            from app.services.log_ingestion.pipeline import (
                clean_text,
                chunk_text,
                detect_findings,
                PipelineResult,
            )
            cleaned = clean_text(raw_text)
            chunks = chunk_text(cleaned)
            findings = detect_findings(cleaned, force_source_type.value)
            result = PipelineResult(
                source_type=force_source_type.value,
                chunks=chunks,
                findings=findings,
                parsed_batch=parsed_batch,
                total_lines=parsed_batch.total_lines,
                parsed_lines=parsed_batch.parsed_lines,
                failed_lines=parsed_batch.failed_lines,
            )
        else:
            result = run_pipeline_enhanced(
                raw_text,
                incident_id=incident_id,
                attachment_id=attachment_id,
            )

        return result

    def create_ingestion_job(
        self,
        incident_id: int,
        attachment_id: int,
        source_type: str | None = None,
    ) -> LogIngestionJob:
        """
        Create a new log ingestion job record.

        Args:
            incident_id: Associated incident ID
            attachment_id: Associated attachment ID
            source_type: Detected or forced source type

        Returns:
            Created LogIngestionJob record
        """
        job = LogIngestionJob(
            incident_id=incident_id,
            attachment_id=attachment_id,
            status="queued",
            source_type=source_type,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def start_job(self, job_id: int) -> LogIngestionJob:
        """
        Mark a job as started.

        Args:
            job_id: ID of the job to start

        Returns:
            Updated LogIngestionJob record
        """
        job = self.db.get(LogIngestionJob, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = "running"
        job.started_at = _utcnow()
        self.db.commit()
        self.db.refresh(job)
        return job

    def complete_job(
        self,
        job_id: int,
        source_type: str,
        chunks: list[Chunk],
        findings: list[Finding],
    ) -> LogIngestionJob:
        """
        Mark a job as completed and store results.

        Args:
            job_id: ID of the job to complete
            source_type: Detected log source type
            chunks: Processed log chunks
            findings: Detected findings/issues

        Returns:
            Updated LogIngestionJob record
        """
        job = self.db.get(LogIngestionJob, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = "succeeded"
        job.source_type = source_type
        job.finished_at = _utcnow()

        # Store chunks
        for chunk in chunks:
            db_chunk = LogChunk(
                incident_id=job.incident_id,
                attachment_id=job.attachment_id,
                job_id=job_id,
                chunk_index=chunk.index,
                text=chunk.text,
            )
            self.db.add(db_chunk)

        # Store findings
        for finding in findings:
            db_finding = LogFinding(
                incident_id=job.incident_id,
                attachment_id=job.attachment_id,
                job_id=job_id,
                category=finding.category,
                severity=finding.severity,
                title=finding.title,
                evidence=finding.evidence,
            )
            self.db.add(db_finding)

        self.db.commit()
        self.db.refresh(job)
        return job

    def fail_job(self, job_id: int, error: str) -> LogIngestionJob:
        """
        Mark a job as failed.

        Args:
            job_id: ID of the job to fail
            error: Error message

        Returns:
            Updated LogIngestionJob record
        """
        job = self.db.get(LogIngestionJob, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = "failed"
        job.error = error
        job.finished_at = _utcnow()
        self.db.commit()
        self.db.refresh(job)
        return job

    # ========================================================================
    # Process and Store (Combined)
    # ========================================================================

    def process_and_store(
        self,
        raw_text: str,
        incident_id: int,
        attachment_id: int,
        force_source_type: LogSource | None = None,
    ) -> tuple[LogIngestionJob, PipelineResult]:
        """
        Process log text and store results in database.

        This is the main entry point for synchronous log ingestion.

        Args:
            raw_text: Raw log text to process
            incident_id: Associated incident ID
            attachment_id: Associated attachment ID
            force_source_type: Optional forced log source type

        Returns:
            Tuple of (LogIngestionJob, PipelineResult)
        """
        # Create job record
        result = self.process_log_text(
            raw_text,
            incident_id=incident_id,
            attachment_id=attachment_id,
            force_source_type=force_source_type,
        )

        # Create and complete job in one transaction
        job = LogIngestionJob(
            incident_id=incident_id,
            attachment_id=attachment_id,
            status="succeeded",
            source_type=result.source_type,
            started_at=_utcnow(),
            finished_at=_utcnow(),
        )
        self.db.add(job)
        self.db.flush()  # Get job ID

        # Store chunks
        for chunk in result.chunks:
            db_chunk = LogChunk(
                incident_id=incident_id,
                attachment_id=attachment_id,
                job_id=job.id,
                chunk_index=chunk.index,
                text=chunk.text,
            )
            self.db.add(db_chunk)

        # Store findings
        for finding in result.findings:
            db_finding = LogFinding(
                incident_id=incident_id,
                attachment_id=attachment_id,
                job_id=job.id,
                category=finding.category,
                severity=finding.severity,
                title=finding.title,
                evidence=finding.evidence,
            )
            self.db.add(db_finding)

        self.db.commit()
        self.db.refresh(job)

        return job, result

    def process_from_storage(
        self,
        storage_path: str,
        incident_id: int,
        attachment_id: int,
        force_source_type: LogSource | None = None,
    ) -> tuple[LogIngestionJob, PipelineResult]:
        """
        Read log file from storage and process it.

        Args:
            storage_path: Path to the log file in storage
            incident_id: Associated incident ID
            attachment_id: Associated attachment ID
            force_source_type: Optional forced log source type

        Returns:
            Tuple of (LogIngestionJob, PipelineResult)
        """
        # Read file from storage
        raw_text = read_text_file(storage_path, max_chars=10_000_000)

        # Process and store
        return self.process_and_store(
            raw_text,
            incident_id=incident_id,
            attachment_id=attachment_id,
            force_source_type=force_source_type,
        )

    # ========================================================================
    # Query Methods
    # ========================================================================

    def get_job(self, job_id: int) -> LogIngestionJob | None:
        """Get a job by ID."""
        return self.db.get(LogIngestionJob, job_id)

    def get_jobs_by_incident(
        self,
        incident_id: int,
        status: str | None = None,
    ) -> list[LogIngestionJob]:
        """
        Get all ingestion jobs for an incident.

        Args:
            incident_id: Incident ID to filter by
            status: Optional status filter

        Returns:
            List of LogIngestionJob records
        """
        query = select(LogIngestionJob).where(
            LogIngestionJob.incident_id == incident_id
        )
        if status:
            query = query.where(LogIngestionJob.status == status)
        query = query.order_by(LogIngestionJob.created_at.desc())
        return list(self.db.execute(query).scalars().all())

    def get_chunks_by_job(self, job_id: int) -> list[LogChunk]:
        """
        Get all chunks for a job.

        Args:
            job_id: Job ID to filter by

        Returns:
            List of LogChunk records
        """
        query = select(LogChunk).where(
            LogChunk.job_id == job_id
        ).order_by(LogChunk.chunk_index)
        return list(self.db.execute(query).scalars().all())

    def get_findings_by_job(self, job_id: int) -> list[LogFinding]:
        """
        Get all findings for a job.

        Args:
            job_id: Job ID to filter by

        Returns:
            List of LogFinding records
        """
        query = select(LogFinding).where(
            LogFinding.job_id == job_id
        ).order_by(LogFinding.severity.desc(), LogFinding.category)
        return list(self.db.execute(query).scalars().all())

    def get_findings_by_incident(
        self,
        incident_id: int,
        severity: str | None = None,
        category: str | None = None,
    ) -> list[LogFinding]:
        """
        Get all findings for an incident.

        Args:
            incident_id: Incident ID to filter by
            severity: Optional severity filter
            category: Optional category filter

        Returns:
            List of LogFinding records
        """
        query = select(LogFinding).where(
            LogFinding.incident_id == incident_id
        )
        if severity:
            query = query.where(LogFinding.severity == severity)
        if category:
            query = query.where(LogFinding.category == category)
        query = query.order_by(
            LogFinding.severity.desc(),
            LogFinding.created_at.desc()
        )
        return list(self.db.execute(query).scalars().all())

    # ========================================================================
    # Statistics Methods
    # ========================================================================

    def get_stats(self, incident_id: int | None = None) -> dict[str, Any]:
        """
        Get log ingestion statistics.

        Args:
            incident_id: Optional incident ID for filtered stats

        Returns:
            Dictionary with statistics
        """
        # Job stats
        job_query = select(
            LogIngestionJob.status,
            func.count(LogIngestionJob.id)
        )
        if incident_id:
            job_query = job_query.where(LogIngestionJob.incident_id == incident_id)
        job_query = job_query.group_by(LogIngestionJob.status)
        job_stats = dict(self.db.execute(job_query).all())

        # Chunk stats
        chunk_query = select(func.count(LogChunk.id))
        if incident_id:
            chunk_query = chunk_query.where(LogChunk.incident_id == incident_id)
        total_chunks = self.db.execute(chunk_query).scalar() or 0

        # Finding stats
        finding_query = select(
            LogFinding.severity,
            func.count(LogFinding.id)
        )
        if incident_id:
            finding_query = finding_query.where(LogFinding.incident_id == incident_id)
        finding_query = finding_query.group_by(LogFinding.severity)
        severity_stats = dict(self.db.execute(finding_query).all())

        category_query = select(
            LogFinding.category,
            func.count(LogFinding.id)
        )
        if incident_id:
            category_query = category_query.where(LogFinding.incident_id == incident_id)
        category_query = category_query.group_by(LogFinding.category)
        category_stats = dict(self.db.execute(category_query).all())

        total_findings = sum(severity_stats.values())

        return {
            "total_jobs": sum(job_stats.values()),
            "pending_jobs": job_stats.get("queued", 0),
            "running_jobs": job_stats.get("running", 0),
            "completed_jobs": job_stats.get("succeeded", 0),
            "failed_jobs": job_stats.get("failed", 0),
            "total_chunks": total_chunks,
            "total_findings": total_findings,
            "findings_by_severity": {
                "critical": severity_stats.get("critical", 0),
                "high": severity_stats.get("high", 0),
                "medium": severity_stats.get("medium", 0),
                "low": severity_stats.get("low", 0),
            },
            "findings_by_category": category_stats,
        }

    def get_critical_findings(
        self,
        incident_id: int | None = None,
        limit: int = 10,
    ) -> list[LogFinding]:
        """
        Get critical and high severity findings.

        Args:
            incident_id: Optional incident ID for filtered results
            limit: Maximum number of findings to return

        Returns:
            List of critical/high severity LogFinding records
        """
        query = select(LogFinding).where(
            LogFinding.severity.in_(["critical", "high"])
        )
        if incident_id:
            query = query.where(LogFinding.incident_id == incident_id)
        query = query.order_by(
            LogFinding.severity.desc(),
            LogFinding.created_at.desc()
        ).limit(limit)
        return list(self.db.execute(query).scalars().all())


# ============================================================================
# Standalone Functions (for backward compatibility)
# ============================================================================

def process_log(
    raw_text: str,
    incident_id: int | None = None,
    attachment_id: int | None = None,
) -> PipelineResult:
    """
    Process raw log text through the pipeline.

    This is a standalone function for simple use cases.

    Args:
        raw_text: Raw log text to process
        incident_id: Optional incident ID for context
        attachment_id: Optional attachment ID for context

    Returns:
        PipelineResult with all processed data
    """
    return run_pipeline_enhanced(
        raw_text,
        incident_id=incident_id,
        attachment_id=attachment_id,
    )


def process_log_from_file(
    storage_path: str,
    max_chars: int = 10_000_000,
) -> PipelineResult:
    """
    Process a log file from storage.

    Args:
        storage_path: Path to the log file
        max_chars: Maximum characters to read

    Returns:
        PipelineResult with all processed data
    """
    raw_text = read_text_file(storage_path, max_chars=max_chars)
    return run_pipeline(raw_text)