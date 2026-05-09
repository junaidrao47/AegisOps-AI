"""
Log Ingestion Engine - MODULE 3

This module provides a complete log ingestion pipeline for processing
operational logs from various sources.

Supported Sources:
- Kubernetes logs
- Docker logs
- Nginx logs
- Apache logs
- Jenkins logs
- GitHub Actions logs
- Terraform output
- AWS CloudWatch exports

Processing Pipeline:
Upload → Parsing → Cleaning → Chunking → Classification → Embedding → Storage

AI Detection Capabilities:
- CrashLoopBackOff
- OOMKilled
- DNS failures
- Connection timeout
- SSL failures
- Memory leaks
- CPU spikes
- Build failures
"""

from app.services.log_ingestion.parsers import (
    # Enums
    LogSource,
    # Data classes
    ParsedLogEntry,
    ParsedLogBatch,
    # Parser classes
    BaseLogParser,
    KubernetesLogParser,
    DockerLogParser,
    NginxLogParser,
    ApacheLogParser,
    JenkinsLogParser,
    GitHubActionsLogParser,
    TerraformLogParser,
    CloudWatchLogParser,
    GenericLogParser,
    # Functions
    LOG_PARSERS,
    detect_log_source,
    get_parser_for_source,
    parse_logs,
)

from app.services.log_ingestion.pipeline import (
    # Data classes
    Chunk,
    Finding,
    PipelineResult,
    DetectionRule,
    # Detection rules
    DETECTION_RULES,
    # Functions
    clean_text,
    chunk_text,
    classify_source,
    classify_source_enhanced,
    detect_findings,
    detect_findings_from_entries,
    prepare_for_embedding,
    run_pipeline,
    run_pipeline_enhanced,
)

__all__ = [
    # Enums
    "LogSource",
    # Data classes
    "ParsedLogEntry",
    "ParsedLogBatch",
    "Chunk",
    "Finding",
    "PipelineResult",
    "DetectionRule",
    # Parser classes
    "BaseLogParser",
    "KubernetesLogParser",
    "DockerLogParser",
    "NginxLogParser",
    "ApacheLogParser",
    "JenkinsLogParser",
    "GitHubActionsLogParser",
    "TerraformLogParser",
    "CloudWatchLogParser",
    "GenericLogParser",
    # Parser registry
    "LOG_PARSERS",
    # Detection rules
    "DETECTION_RULES",
    # Functions
    "detect_log_source",
    "get_parser_for_source",
    "parse_logs",
    "clean_text",
    "chunk_text",
    "classify_source",
    "classify_source_enhanced",
    "detect_findings",
    "detect_findings_from_entries",
    "prepare_for_embedding",
    "run_pipeline",
    "run_pipeline_enhanced",
]