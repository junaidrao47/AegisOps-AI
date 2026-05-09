"""
Log Ingestion Pipeline - MODULE 3: Log Ingestion Engine

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

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.services.log_ingestion.parsers import (
    LogSource,
    ParsedLogBatch,
    ParsedLogEntry,
    detect_log_source,
    parse_logs,
)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass(frozen=True)
class Chunk:
    """Represents a chunk of log text for embedding/storage."""
    index: int
    text: str
    start_line: int = 0
    end_line: int = 0
    checksum: str = ""

    @staticmethod
    def compute_checksum(text: str) -> str:
        """Compute a SHA256 checksum for text deduplication."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]


@dataclass(frozen=True)
class Finding:
    """Represents a detected issue/anomaly in the logs."""
    category: str
    severity: str  # low, medium, high, critical
    title: str
    evidence: str | None
    source_type: str = ""
    confidence: float = 1.0
    timestamp: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert finding to dictionary."""
        return {
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "evidence": self.evidence,
            "source_type": self.source_type,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


@dataclass
class PipelineResult:
    """Result of the complete log ingestion pipeline."""
    source_type: str
    chunks: list[Chunk]
    findings: list[Finding]
    parsed_batch: ParsedLogBatch | None = None
    total_lines: int = 0
    parsed_lines: int = 0
    failed_lines: int = 0
    processing_time_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def critical_findings(self) -> list[Finding]:
        """Get all critical severity findings."""
        return [f for f in self.findings if f.severity == "critical"]

    @property
    def high_findings(self) -> list[Finding]:
        """Get all high severity findings."""
        return [f for f in self.findings if f.severity == "high"]

    @property
    def has_critical_issues(self) -> bool:
        """Check if there are any critical issues."""
        return len(self.critical_findings) > 0


# ============================================================================
# Text Cleaning
# ============================================================================

_ANSI_ESCAPE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
_UNICODE_CONTROL = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
_MULTIPLE_WHITESPACE = re.compile(r"[ \t]+")
_TRAILING_WHITESPACE = re.compile(r"\s+$", re.MULTILINE)


def clean_text(text: str) -> str:
    """
    Clean raw log text by removing ANSI codes, control characters,
    and normalizing whitespace.
    """
    # Remove ANSI escape sequences
    text = _ANSI_ESCAPE.sub("", text)

    # Remove Unicode control characters (except newline, tab, carriage return)
    text = _UNICODE_CONTROL.sub("", text)

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove null bytes
    text = text.replace("\x00", "")

    # Normalize multiple spaces (but preserve indentation)
    # Only collapse spaces that aren't at the start of a line
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        # Strip trailing whitespace
        line = line.rstrip()
        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)

    return text


# ============================================================================
# Text Chunking
# ============================================================================

def chunk_text(
    text: str,
    *,
    max_chars: int = 2200,
    overlap_chars: int = 200,
    respect_lines: bool = True,
) -> list[Chunk]:
    """
    Split text into overlapping chunks for embedding.

    Args:
        text: The text to chunk
        max_chars: Maximum characters per chunk
        overlap_chars: Number of overlapping characters between chunks
        respect_lines: If True, don't break in the middle of a line

    Returns:
        List of Chunk objects
    """
    if not text:
        return []

    if max_chars <= 0:
        return [Chunk(
            index=0,
            text=text,
            start_line=0,
            end_line=text.count("\n"),
            checksum=Chunk.compute_checksum(text)
        )]

    lines = text.splitlines(keepends=False)
    chunks: list[Chunk] = []
    current: list[str] = []
    current_len = 0
    start_line = 0

    def flush() -> None:
        nonlocal current, current_len, start_line
        if not current:
            return

        chunk_text_value = "\n".join(current).strip()
        if chunk_text_value:
            end_line = start_line + len(current) - 1
            chunks.append(Chunk(
                index=len(chunks),
                text=chunk_text_value,
                start_line=start_line,
                end_line=end_line,
                checksum=Chunk.compute_checksum(chunk_text_value)
            ))

        if overlap_chars > 0 and chunk_text_value and len(chunk_text_value) > overlap_chars:
            # Create overlap from the end of the current chunk
            overlap_text = chunk_text_value[-overlap_chars:]
            # Find a good break point in the overlap
            overlap_lines = overlap_text.split("\n")
            if len(overlap_lines) > 1:
                # Keep from the second line to avoid partial lines
                current = overlap_lines[1:]
            else:
                current = [overlap_text]
            current_len = sum(len(l) for l in current) + len(current) - 1
            start_line = end_line - len(overlap_lines) + 2
        else:
            current = []
            current_len = 0
            start_line = start_line + len(current) if current else start_line

    for line in lines:
        line_len = len(line)

        if respect_lines:
            # If adding this line would exceed max, flush first
            if current_len + line_len + 1 > max_chars and current:
                flush()
                start_line = len(chunks) > 0 and chunks[-1].end_line + 1 or start_line

            current.append(line)
            current_len += line_len + 1  # +1 for newline
        else:
            if current_len + line_len > max_chars and current:
                flush()

            current.append(line)
            current_len += line_len

    # Flush remaining
    if current:
        flush()

    return chunks


# ============================================================================
# Source Classification
# ============================================================================

_SOURCE_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("kubernetes", re.compile(r"CrashLoopBackOff|OOMKilled|kubelet|kubectl|namespace=|pod/", re.I)),
    ("docker", re.compile(r"docker\[|containerd|\{\"log\":|\{\"time\":.*\"log\":", re.I)),
    ("nginx", re.compile(r"nginx\/\d|\s\"(GET|POST|PUT|DELETE|PATCH)\s+[^\"]+\s+HTTP\/", re.I)),
    ("apache", re.compile(r"\"(GET|POST|PUT|DELETE|PATCH)\s+[^\"]+\s+HTTP\/\d\.\d\"\s+\d{3}\s+", re.I)),
    ("jenkins", re.compile(r"\[Pipeline\]|Finished: (SUCCESS|FAILURE)|hudson\.model", re.I)),
    ("github_actions", re.compile(r"##\[(error|warning)\]|Run actions\/checkout|GITHUB_ACTIONS", re.I)),
    ("terraform", re.compile(r"Terraform will perform|Plan: \d+ to add|Error: .*", re.I)),
    ("cloudwatch", re.compile(r"\t@timestamp\t|\"@timestamp\"|CloudWatch", re.I)),
]


def classify_source(text: str) -> str:
    """
    Classify the source type of log text using pattern matching.
    This is a fallback when parser-based detection isn't available.
    """
    sample = text[:200_000]
    for name, pat in _SOURCE_RULES:
        if pat.search(sample):
            return name
    return "generic"


def classify_source_enhanced(text: str) -> tuple[str, float]:
    """
    Enhanced source classification that returns both the source type
    and a confidence score.
    """
    sample = text[:200_000]
    scores: dict[str, int] = {}

    for name, pat in _SOURCE_RULES:
        matches = pat.findall(sample)
        if matches:
            scores[name] = len(matches)

    if not scores:
        return "generic", 0.5

    best_source = max(scores, key=scores.get)
    best_count = scores[best_source]
    total_matches = sum(scores.values())

    confidence = best_count / total_matches if total_matches > 0 else 0.5

    return best_source, min(confidence + 0.3, 1.0)  # Base confidence boost


# ============================================================================
# AI Detection Rules
# ============================================================================

@dataclass
class DetectionRule:
    """Represents a detection rule for finding issues in logs."""
    category: str
    severity: str
    title: str
    pattern: re.Pattern[str]
    source_filter: set[str] | None = None  # None = all sources
    evidence_context: int = 120  # chars before match
    evidence_extension: int = 200  # chars after match


# Comprehensive detection rules
DETECTION_RULES: list[DetectionRule] = [
    # Kubernetes-specific issues
    DetectionRule(
        category="CrashLoopBackOff",
        severity="high",
        title="CrashLoopBackOff detected - Container is repeatedly crashing",
        pattern=re.compile(r"CrashLoopBackOff|Back-off restarting failed container", re.I),
        source_filter={"kubernetes", "generic"},
    ),
    DetectionRule(
        category="OOMKilled",
        severity="high",
        title="OOMKilled - Container terminated due to out-of-memory",
        pattern=re.compile(r"OOMKilled|Out of memory|Killed process \d+|killed process|memory cgroup out of memory", re.I),
        source_filter=None,
    ),
    DetectionRule(
        category="ProbeFailure",
        severity="medium",
        title="Kubernetes probe failure detected",
        pattern=re.compile(r"readiness probe failed|liveness probe failed|startup probe failed", re.I),
        source_filter={"kubernetes", "generic"},
    ),
    DetectionRule(
        category="ImagePullError",
        severity="medium",
        title="Container image pull error",
        pattern=re.compile(r"ImagePullBackOff|ErrImagePull|image not found|manifest unknown|unauthorized", re.I),
        source_filter={"kubernetes", "docker", "generic"},
    ),

    # Network issues
    DetectionRule(
        category="DNSFailure",
        severity="medium",
        title="DNS resolution failure detected",
        pattern=re.compile(r"Temporary failure in name resolution|no such host|NXDOMAIN|SERVFAIL|getaddrinfo failed|DNS.*failed", re.I),
        source_filter=None,
    ),
    DetectionRule(
        category="ConnectionTimeout",
        severity="medium",
        title="Connection timeout detected",
        pattern=re.compile(r"timed out|ETIMEDOUT|context deadline exceeded|Read timed out|connection timed out|dial timeout|connection reset by peer", re.I),
        source_filter=None,
    ),
    DetectionRule(
        category="ConnectionRefused",
        severity="medium",
        title="Connection refused detected",
        pattern=re.compile(r"connection refused|ECONNREFUSED|can't connect|unable to connect", re.I),
        source_filter=None,
    ),

    # SSL/TLS issues
    DetectionRule(
        category="SSLFailure",
        severity="medium",
        title="SSL/TLS failure detected",
        pattern=re.compile(r"SSL routines|certificate verify failed|x509: certificate|handshake failure|TLS handshake|certificate expired|CERT_", re.I),
        source_filter=None,
    ),

    # Resource issues
    DetectionRule(
        category="MemoryLeak",
        severity="low",
        title="Potential memory leak symptoms detected",
        pattern=re.compile(r"memory leak|heap size|GC overhead limit exceeded|OutOfMemoryError|java\.lang\.OutOfMemoryError|cannot allocate memory", re.I),
        source_filter=None,
    ),
    DetectionRule(
        category="CPUSpike",
        severity="low",
        title="Potential CPU spike symptoms detected",
        pattern=re.compile(r"cpu throttling|load average|CPU\s+usage\s+\d{2,}%|high cpu|cpu.*spike", re.I),
        source_filter=None,
    ),
    DetectionRule(
        category="DiskSpace",
        severity="medium",
        title="Disk space issue detected",
        pattern=re.compile(r"no space left on device|ENOSPC|disk full|filesystem full|quota exceeded", re.I),
        source_filter=None,
    ),

    # Build/CI issues
    DetectionRule(
        category="BuildFailure",
        severity="high",
        title="Build failure detected",
        pattern=re.compile(r"BUILD FAILED|Build step .* marked build as failure|##\[error\]|Process completed with exit code|FAILED!|error TS\d+|error CS\d+", re.I),
        source_filter={"jenkins", "github_actions", "generic"},
    ),
    DetectionRule(
        category="TestFailure",
        severity="medium",
        title="Test failure detected",
        pattern=re.compile(r"FAILED|tests? failed|AssertionError|assert.*false|expect.*received|Test.*FAILED", re.I),
        source_filter={"jenkins", "github_actions", "generic"},
    ),

    # Terraform issues
    DetectionRule(
        category="TerraformError",
        severity="high",
        title="Terraform error detected",
        pattern=re.compile(r"Error:|terraform.*error|resource.*not found|Invalid.*configuration", re.I),
        source_filter={"terraform", "generic"},
    ),
    DetectionRule(
        category="TerraformPlanChange",
        severity="low",
        title="Terraform plan shows infrastructure changes",
        pattern=re.compile(r"Plan: \d+ to add|\d+ to change|\d+ to destroy", re.I),
        source_filter={"terraform", "generic"},
    ),

    # HTTP errors
    DetectionRule(
        category="HTTPError5xx",
        severity="high",
        title="HTTP 5xx server error detected",
        pattern=re.compile(r'" (5\d{2}) ', re.I),
        source_filter={"nginx", "apache", "generic"},
    ),
    DetectionRule(
        category="HTTPError4xx",
        severity="low",
        title="HTTP 4xx client error detected",
        pattern=re.compile(r'" (4\d{2}) ', re.I),
        source_filter={"nginx", "apache", "generic"},
    ),

    # Application errors
    DetectionRule(
        category="PanicError",
        severity="critical",
        title="Application panic detected",
        pattern=re.compile(r"panic:|fatal error:|runtime error:|uncaught exception", re.I),
        source_filter=None,
    ),
    DetectionRule(
        category="SegfaultError",
        severity="critical",
        title="Segmentation fault detected",
        pattern=re.compile(r"segmentation fault|SIGSEGV|core dumped", re.I),
        source_filter=None,
    ),
    DetectionRule(
        category="DatabaseError",
        severity="high",
        title="Database error detected",
        pattern=re.compile(r"database.*error|SQL.*error|connection.*database|postgres.*error|mysql.*error|mongodb.*error", re.I),
        source_filter=None,
    ),
]


def detect_findings(text: str, source_type: str = "generic") -> list[Finding]:
    """
    Detect issues/anomalies in log text using pattern matching.

    Args:
        text: The log text to analyze
        source_type: The detected source type for filtering rules

    Returns:
        List of Finding objects for detected issues
    """
    findings: list[Finding] = []
    sample = text[:500_000]  # Limit for performance

    for rule in DETECTION_RULES:
        # Skip if source filter doesn't match
        if rule.source_filter and source_type not in rule.source_filter:
            continue

        matches = list(rule.pattern.finditer(sample))
        if not matches:
            continue

        # Create a finding for each unique match
        seen_evidence: set[str] = set()
        for match in matches:
            # Provide context around the match
            start = max(match.start() - rule.evidence_context, 0)
            end = min(match.end() + rule.evidence_extension, len(sample))
            evidence = sample[start:end].replace("\n", " ").strip()

            # Deduplicate evidence
            evidence_key = evidence[:100]
            if evidence_key in seen_evidence:
                continue
            seen_evidence.add(evidence_key)

            findings.append(Finding(
                category=rule.category,
                severity=rule.severity,
                title=rule.title,
                evidence=evidence,
                source_type=source_type,
            ))

            # Limit findings per rule to avoid flooding
            if len(seen_evidence) >= 5:
                break

    return findings


def detect_findings_from_entries(
    entries: list[ParsedLogEntry],
    source_type: str = "generic"
) -> list[Finding]:
    """
    Detect issues from parsed log entries, preserving timestamps.

    Args:
        entries: List of parsed log entries
        source_type: The detected source type

    Returns:
        List of Finding objects with timestamps where available
    """
    findings: list[Finding] = []

    for entry in entries:
        entry_findings = detect_findings(entry.message, source_type)
        for finding in entry_findings:
            findings.append(Finding(
                category=finding.category,
                severity=finding.severity,
                title=finding.title,
                evidence=finding.evidence,
                source_type=finding.source_type,
                timestamp=entry.timestamp,
            ))

    return findings


# ============================================================================
# Embedding Preparation
# ============================================================================

def prepare_for_embedding(chunk: Chunk, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Prepare a chunk for embedding by adding metadata.

    Args:
        chunk: The chunk to prepare
        metadata: Optional additional metadata

    Returns:
        Dictionary ready for embedding API
    """
    return {
        "text": chunk.text,
        "metadata": {
            "chunk_index": chunk.index,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "checksum": chunk.checksum,
            **(metadata or {}),
        }
    }


# ============================================================================
# Main Pipeline
# ============================================================================

def run_pipeline(raw_text: str) -> PipelineResult:
    """
    Run the complete log ingestion pipeline.

    Processing steps:
    1. Parsing - Detect source type and parse log structure
    2. Cleaning - Remove ANSI codes, normalize whitespace
    3. Chunking - Split into overlapping chunks for embedding
    4. Classification - Confirm/verify source type
    5. Detection - Find issues and anomalies
    6. Storage preparation - Prepare for database storage

    Args:
        raw_text: Raw log text to process

    Returns:
        PipelineResult containing all processed data
    """
    import time
    start_time = time.time()

    # Step 1: Parse logs (auto-detects source type)
    parsed_batch = parse_logs(raw_text)
    source_type = parsed_batch.source_type.value

    # Step 2: Clean text
    cleaned_text = clean_text(raw_text)

    # Step 3: Classify source (verify detection)
    classified_source, classification_confidence = classify_source_enhanced(cleaned_text)

    # Use parser detection if confident, otherwise use classification
    if parsed_batch.source_type != LogSource.GENERIC:
        final_source = parsed_batch.source_type.value
    else:
        final_source = classified_source

    # Step 4: Chunk text
    chunks = chunk_text(cleaned_text)

    # Step 5: Detect findings
    findings = detect_findings(cleaned_text, final_source)

    processing_time = (time.time() - start_time) * 1000

    return PipelineResult(
        source_type=final_source,
        chunks=chunks,
        findings=findings,
        parsed_batch=parsed_batch,
        total_lines=parsed_batch.total_lines,
        parsed_lines=parsed_batch.parsed_lines,
        failed_lines=parsed_batch.failed_lines,
        processing_time_ms=processing_time,
        metadata={
            "classification_confidence": classification_confidence,
            "classification_source": classified_source,
            "parser_source": parsed_batch.source_type.value,
            "parser_metadata": parsed_batch.metadata,
        }
    )


def run_pipeline_enhanced(
    raw_text: str,
    incident_id: int | None = None,
    attachment_id: int | None = None,
) -> PipelineResult:
    """
    Enhanced pipeline that includes additional context.

    Args:
        raw_text: Raw log text to process
        incident_id: Optional incident ID for context
        attachment_id: Optional attachment ID for context

    Returns:
        Enhanced PipelineResult
    """
    result = run_pipeline(raw_text)

    if incident_id is not None:
        result.metadata["incident_id"] = incident_id
    if attachment_id is not None:
        result.metadata["attachment_id"] = attachment_id

    return result