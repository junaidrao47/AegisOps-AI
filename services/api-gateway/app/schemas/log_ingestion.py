"""
Log Ingestion Schemas - MODULE 3: Log Ingestion Engine

Pydantic schemas for log ingestion API requests and responses.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class LogSourceType(str, Enum):
    """Supported log source types."""
    KUBERNETES = "kubernetes"
    DOCKER = "docker"
    NGINX = "nginx"
    APACHE = "apache"
    JENKINS = "jenkins"
    GITHUB_ACTIONS = "github_actions"
    TERRAFORM = "terraform"
    CLOUDWATCH = "cloudwatch"
    GENERIC = "generic"


class FindingSeverity(str, Enum):
    """Finding severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
# Request Schemas
# ============================================================================

class LogIngestRequest(BaseModel):
    """Request schema for log ingestion via API."""
    log_text: str = Field(..., min_length=1, description="Raw log text to process")
    source_type: LogSourceType | None = Field(
        default=None,
        description="Optional: Force a specific log source type"
    )
    incident_id: int | None = Field(
        default=None,
        description="Optional: Associate with an incident"
    )


class LogIngestFileRequest(BaseModel):
    """Request schema for file-based log ingestion."""
    incident_id: int = Field(..., description="Incident ID to associate logs with")
    kind: str = Field(default="log", description="Attachment kind (log|screenshot|yaml)")


# ============================================================================
# Response Schemas
# ============================================================================

class ChunkRead(BaseModel):
    """Schema for a processed log chunk."""
    index: int
    text: str
    start_line: int
    end_line: int
    checksum: str

    model_config = {"from_attributes": True}


class FindingRead(BaseModel):
    """Schema for a detected finding/issue."""
    category: str
    severity: str
    title: str
    evidence: str | None
    source_type: str
    confidence: float
    timestamp: datetime | None

    model_config = {"from_attributes": True}


class FindingSummary(BaseModel):
    """Summary of findings by severity."""
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    total: int = 0


class PipelineMetadata(BaseModel):
    """Metadata from pipeline processing."""
    classification_confidence: float | None = None
    classification_source: str | None = None
    parser_source: str | None = None
    parser_metadata: dict[str, Any] = Field(default_factory=dict)
    incident_id: int | None = None
    attachment_id: int | None = None


class LogIngestResponse(BaseModel):
    """Response schema for log ingestion."""
    success: bool
    source_type: str
    total_lines: int
    parsed_lines: int
    failed_lines: int
    chunks_count: int
    findings_count: int
    findings_summary: FindingSummary
    findings: list[FindingRead]
    chunks: list[ChunkRead]
    processing_time_ms: float
    metadata: PipelineMetadata

    model_config = {"from_attributes": True}


class LogIngestBriefResponse(BaseModel):
    """Brief response for log ingestion (without full chunks/findings)."""
    success: bool
    source_type: str
    total_lines: int
    parsed_lines: int
    failed_lines: int
    chunks_count: int
    findings_count: int
    findings_summary: FindingSummary
    critical_findings: list[FindingRead]
    high_findings: list[FindingRead]
    processing_time_ms: float
    message: str | None = None

    model_config = {"from_attributes": True}


class LogSourceDetectResponse(BaseModel):
    """Response for log source detection endpoint."""
    detected_source: str
    confidence: float
    all_matches: dict[str, int]


class LogIngestionJobRead(BaseModel):
    """Schema for reading a log ingestion job."""
    id: int
    incident_id: int
    attachment_id: int
    status: str
    source_type: str | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class LogChunkRead(BaseModel):
    """Schema for reading a stored log chunk."""
    id: int
    incident_id: int
    attachment_id: int
    job_id: int
    chunk_index: int
    text: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LogFindingRead(BaseModel):
    """Schema for reading a stored log finding."""
    id: int
    incident_id: int
    attachment_id: int
    job_id: int
    category: str
    severity: str
    title: str
    evidence: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LogIngestionStats(BaseModel):
    """Statistics for log ingestion jobs."""
    total_jobs: int
    pending_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    total_chunks: int
    total_findings: int
    findings_by_severity: dict[str, int]
    findings_by_category: dict[str, int]


# ============================================================================
# Worker/Async Task Schemas
# ============================================================================

class LogIngestionTaskRequest(BaseModel):
    """Request for async log ingestion task."""
    incident_id: int
    attachment_id: int
    storage_path: str
    force_source_type: LogSourceType | None = None


class LogIngestionTaskResponse(BaseModel):
    """Response from async log ingestion task."""
    job_id: int
    status: str
    source_type: str | None
    findings_count: int
    chunks_count: int
    error: str | None
    processing_time_ms: float | None