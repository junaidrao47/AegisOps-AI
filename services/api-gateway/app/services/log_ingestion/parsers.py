"""
Log Parsers Module - MODULE 3: Log Ingestion Engine

Provides dedicated parsers for various log sources:
- Kubernetes logs
- Docker logs
- Nginx logs
- Apache logs
- Jenkins logs
- GitHub Actions logs
- Terraform output
- AWS CloudWatch exports
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class LogSource(Enum):
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


@dataclass
class ParsedLogEntry:
    """Represents a single parsed log entry."""
    timestamp: datetime | None
    level: str | None  # INFO, WARN, ERROR, etc.
    message: str
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)
    raw: str = ""


@dataclass
class ParsedLogBatch:
    """Result of parsing a log file/batch."""
    source_type: LogSource
    entries: list[ParsedLogEntry]
    total_lines: int
    parsed_lines: int
    failed_lines: int
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseLogParser(ABC):
    """Abstract base class for log parsers."""

    @property
    @abstractmethod
    def source_type(self) -> LogSource:
        """Return the log source type this parser handles."""
        pass

    @abstractmethod
    def can_parse(self, text: str) -> bool:
        """Determine if this parser can handle the given text."""
        pass

    @abstractmethod
    def parse(self, text: str) -> ParsedLogBatch:
        """Parse the log text and return structured entries."""
        pass

    def detect_source_patterns(self, text: str, patterns: list[re.Pattern]) -> bool:
        """Check if any of the patterns match the text."""
        sample = text[:10_000]  # Check first 10K chars for efficiency
        return any(p.search(sample) for p in patterns)


class KubernetesLogParser(BaseLogParser):
    """Parser for Kubernetes logs (kubectl logs, kubelet, etc.)."""

    # Patterns that indicate Kubernetes logs
    DETECTION_PATTERNS = [
        re.compile(r"CrashLoopBackOff|OOMKilled|kubelet|kubectl|namespace=", re.I),
        re.compile(r"pod/|deployment/|replicaset/|statefulset/", re.I),
        re.compile(r"\[kubelet\]|\[kubectl\]|\[kube-apiserver\]", re.I),
        re.compile(r"k8s\.io|kubernetes\.io", re.I),
        re.compile(r"Error from server|error when reading", re.I),
    ]

    # Common K8s log patterns
    TIMESTAMP_PATTERN = re.compile(
        r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^\s]*)\s+'
    )
    K8S_JSON_PATTERN = re.compile(r'^\s*\{.*"log":')
    LEVEL_PATTERN = re.compile(r'\b(TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\b', re.I)

    # K8s-specific issue patterns
    CRASH_LOOP_PATTERN = re.compile(r'CrashLoopBackOff|Back-off restarting failed container', re.I)
    OOM_PATTERN = re.compile(r'OOMKilled|Out of memory|Killed process', re.I)
    READY_PATTERN = re.compile(r'readiness probe failed|liveness probe failed', re.I)
    IMAGE_PATTERN = re.compile(r'ImagePullBackOff|ErrImagePull|image not found', re.I)
    RESOURCE_PATTERN = re.compile(r'Insufficient (cpu|memory|ephemeral-storage)', re.I)

    @property
    def source_type(self) -> LogSource:
        return LogSource.KUBERNETES

    def can_parse(self, text: str) -> bool:
        return self.detect_source_patterns(text, self.DETECTION_PATTERNS)

    def parse(self, text: str) -> ParsedLogBatch:
        lines = text.splitlines()
        entries: list[ParsedLogEntry] = []
        parsed = 0
        failed = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                entry = self._parse_line(line)
                entries.append(entry)
                parsed += 1
            except Exception:
                failed += 1
                # Still create a basic entry
                entries.append(ParsedLogEntry(
                    timestamp=None,
                    level=None,
                    message=line,
                    source=self.source_type.value,
                    raw=line
                ))

        return ParsedLogBatch(
            source_type=self.source_type,
            entries=entries,
            total_lines=len(lines),
            parsed_lines=parsed,
            failed_lines=failed,
            metadata={
                "has_crash_loop": bool(self.CRASH_LOOP_PATTERN.search(text)),
                "has_oom": bool(self.OOM_PATTERN.search(text)),
                "has_probe_issues": bool(self.READY_PATTERN.search(text)),
                "has_image_issues": bool(self.IMAGE_PATTERN.search(text)),
                "has_resource_issues": bool(self.RESOURCE_PATTERN.search(text)),
            }
        )

    def _parse_line(self, line: str) -> ParsedLogEntry:
        timestamp = None
        level = None
        message = line
        metadata = {}

        # Try JSON parsing (common in K8s container logs)
        if self.K8S_JSON_PATTERN.match(line):
            try:
                data = json.loads(line)
                message = data.get("log", data.get("message", line))
                level = data.get("stream", data.get("level", None))
                if "time" in data:
                    try:
                        timestamp = datetime.fromisoformat(data["time"].replace("Z", "+00:00"))
                    except Exception:
                        pass
                metadata = {k: v for k, v in data.items() if k not in ("log", "message", "stream", "time")}
            except json.JSONDecodeError:
                pass
        else:
            # Try standard timestamp prefix
            ts_match = self.TIMESTAMP_PATTERN.match(line)
            if ts_match:
                try:
                    timestamp = datetime.fromisoformat(ts_match.group(1).replace("Z", "+00:00"))
                    message = line[ts_match.end():]
                except Exception:
                    pass

            # Extract log level
            level_match = self.LEVEL_PATTERN.search(message)
            if level_match:
                level = level_match.group(1).upper()
                if level == "WARNING":
                    level = "WARN"

        return ParsedLogEntry(
            timestamp=timestamp,
            level=level,
            message=message,
            source=self.source_type.value,
            metadata=metadata,
            raw=line
        )


class DockerLogParser(BaseLogParser):
    """Parser for Docker logs (docker logs, containerd, docker-compose)."""

    DETECTION_PATTERNS = [
        re.compile(r'docker\[|containerd|docker-compose', re.I),
        re.compile(r'\{"log":|\{"time":.*"log":', re.I),
        re.compile(r'^\s*\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', re.I),
        re.compile(r'container\s+\w+\s+(started|stopped|created|removed)', re.I),
    ]

    DOCKER_LOG_PREFIX_PATTERN = re.compile(
        r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^\s]*)\s+'
    )
    LEVEL_PATTERN = re.compile(r'\b(TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\b', re.I)

    @property
    def source_type(self) -> LogSource:
        return LogSource.DOCKER

    def can_parse(self, text: str) -> bool:
        return self.detect_source_patterns(text, self.DETECTION_PATTERNS)

    def parse(self, text: str) -> ParsedLogBatch:
        lines = text.splitlines()
        entries: list[ParsedLogEntry] = []
        parsed = 0
        failed = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                entry = self._parse_line(line)
                entries.append(entry)
                parsed += 1
            except Exception:
                failed += 1
                entries.append(ParsedLogEntry(
                    timestamp=None,
                    level=None,
                    message=line,
                    source=self.source_type.value,
                    raw=line
                ))

        return ParsedLogBatch(
            source_type=self.source_type,
            entries=entries,
            total_lines=len(lines),
            parsed_lines=parsed,
            failed_lines=failed
        )

    def _parse_line(self, line: str) -> ParsedLogEntry:
        timestamp = None
        level = None
        message = line
        metadata = {}

        # Docker JSON log format
        if line.startswith('{'):
            try:
                data = json.loads(line)
                message = data.get("log", data.get("message", line))
                level = data.get("stream", None)
                if "time" in data:
                    try:
                        timestamp = datetime.fromisoformat(data["time"].replace("Z", "+00:00"))
                    except Exception:
                        pass
            except json.JSONDecodeError:
                pass
        else:
            ts_match = self.DOCKER_LOG_PREFIX_PATTERN.match(line)
            if ts_match:
                try:
                    timestamp = datetime.fromisoformat(ts_match.group(1).replace("Z", "+00:00"))
                    message = line[ts_match.end():]
                except Exception:
                    pass

            level_match = self.LEVEL_PATTERN.search(message)
            if level_match:
                level = level_match.group(1).upper()

        return ParsedLogEntry(
            timestamp=timestamp,
            level=level,
            message=message,
            source=self.source_type.value,
            metadata=metadata,
            raw=line
        )


class NginxLogParser(BaseLogParser):
    """Parser for Nginx access and error logs."""

    DETECTION_PATTERNS = [
        re.compile(r'nginx/\d|nginx:', re.I),
        re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s+-\s+-\s+', re.I),
        re.compile(r'\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}\s+\[\w+\]\s+\d+#\d+:', re.I),  # Nginx error log format
    ]

    # Combined log format pattern
    COMBINED_LOG_PATTERN = re.compile(
        r'^(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+-\s+(?P<user>\S+)\s+'
        r'\[(?P<timestamp>[^\]]+)\]\s+'
        r'"(?P<method>GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+(?P<path>\S+)\s+HTTP/(?P<protocol>[^"]+)"\s+'
        r'(?P<status>\d{3})\s+(?P<size>\d+|-)\s*'
        r'(?:"(?P<referer>[^"]*)"\s+"(?P<user_agent>[^"]*)")?'
    )

    # Error log pattern
    ERROR_LOG_PATTERN = re.compile(
        r'^(?P<timestamp>\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
        r'\[(?P<level>[^\]]+)\]\s+'
        r'(?P<pid>\d+)#(?P<tid>\d+):\s+'
        r'(?P<message>.+)$'
    )

    ERROR_SEVERITY_MAP = {
        "emerg": "CRITICAL",
        "alert": "CRITICAL",
        "crit": "CRITICAL",
        "error": "ERROR",
        "warn": "WARN",
        "notice": "INFO",
        "info": "INFO",
        "debug": "DEBUG",
    }

    @property
    def source_type(self) -> LogSource:
        return LogSource.NGINX

    def can_parse(self, text: str) -> bool:
        return self.detect_source_patterns(text, self.DETECTION_PATTERNS)

    def parse(self, text: str) -> ParsedLogBatch:
        lines = text.splitlines()
        entries: list[ParsedLogEntry] = []
        parsed = 0
        failed = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                entry = self._parse_line(line)
                entries.append(entry)
                parsed += 1
            except Exception:
                failed += 1
                entries.append(ParsedLogEntry(
                    timestamp=None,
                    level=None,
                    message=line,
                    source=self.source_type.value,
                    raw=line
                ))

        return ParsedLogBatch(
            source_type=self.source_type,
            entries=entries,
            total_lines=len(lines),
            parsed_lines=parsed,
            failed_lines=failed
        )

    def _parse_line(self, line: str) -> ParsedLogEntry:
        # Try access log format first
        match = self.COMBINED_LOG_PATTERN.match(line)
        if match:
            metadata = match.groupdict()
            status = int(metadata.get("status", 0))
            level = "ERROR" if status >= 400 else "INFO"

            try:
                timestamp = datetime.strptime(metadata["timestamp"], "%d/%b/%Y:%H:%M:%S %z")
            except Exception:
                timestamp = None

            return ParsedLogEntry(
                timestamp=timestamp,
                level=level,
                message=f"{metadata['method']} {metadata['path']} - {status}",
                source=self.source_type.value,
                metadata={
                    "ip": metadata.get("ip"),
                    "status": status,
                    "method": metadata.get("method"),
                    "path": metadata.get("path"),
                    "size": int(metadata["size"]) if metadata.get("size", "-") != "-" else None,
                },
                raw=line
            )

        # Try error log format
        match = self.ERROR_LOG_PATTERN.match(line)
        if match:
            metadata = match.groupdict()
            level = self.ERROR_SEVERITY_MAP.get(metadata.get("level", "").lower(), "INFO")

            try:
                timestamp = datetime.strptime(metadata["timestamp"], "%Y/%m/%d %H:%M:%S")
            except Exception:
                timestamp = None

            return ParsedLogEntry(
                timestamp=timestamp,
                level=level,
                message=metadata.get("message", line),
                source=self.source_type.value,
                metadata={
                    "pid": metadata.get("pid"),
                    "tid": metadata.get("tid"),
                    "nginx_level": metadata.get("level"),
                },
                raw=line
            )

        # Fallback
        return ParsedLogEntry(
            timestamp=None,
            level=None,
            message=line,
            source=self.source_type.value,
            raw=line
        )


class ApacheLogParser(BaseLogParser):
    """Parser for Apache HTTP Server logs."""

    DETECTION_PATTERNS = [
        re.compile(r'"(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+[^"]+\s+HTTP/\d\.\d"\s+\d{3}\s+', re.I),
        re.compile(r'\[apache\]|\[mpm_|\[core\]|\[http:', re.I),
        re.compile(r'apache2|httpd', re.I),
    ]

    # Similar to Nginx combined log format
    COMBINED_LOG_PATTERN = re.compile(
        r'^(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+\S+\s+(?P<user>\S+)\s+'
        r'\[(?P<timestamp>[^\]]+)\]\s+'
        r'"(?P<method>GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+(?P<path>\S+)\s+HTTP/(?P<protocol>[^"]+)"\s+'
        r'(?P<status>\d{3})\s+(?P<size>\d+|-)\s*'
        r'(?:"(?P<referer>[^"]*)"\s+"(?P<user_agent>[^"]*)")?'
    )

    # Error log pattern
    ERROR_LOG_PATTERN = re.compile(
        r'^\[(?P<timestamp>[^\]]+)\]\s+'
        r'\[(?P<module>[^\]]+)\]\s+'
        r'\[(?P<level>[^\]]+)\]\s+'
        r'(?P<message>.+)$'
    )

    ERROR_SEVERITY_MAP = {
        "emerg": "CRITICAL",
        "alert": "CRITICAL",
        "crit": "CRITICAL",
        "error": "ERROR",
        "warn": "WARN",
        "notice": "INFO",
        "info": "INFO",
        "debug": "DEBUG",
        "trace": "TRACE",
    }

    @property
    def source_type(self) -> LogSource:
        return LogSource.APACHE

    def can_parse(self, text: str) -> bool:
        return self.detect_source_patterns(text, self.DETECTION_PATTERNS)

    def parse(self, text: str) -> ParsedLogBatch:
        lines = text.splitlines()
        entries: list[ParsedLogEntry] = []
        parsed = 0
        failed = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                entry = self._parse_line(line)
                entries.append(entry)
                parsed += 1
            except Exception:
                failed += 1
                entries.append(ParsedLogEntry(
                    timestamp=None,
                    level=None,
                    message=line,
                    source=self.source_type.value,
                    raw=line
                ))

        return ParsedLogBatch(
            source_type=self.source_type,
            entries=entries,
            total_lines=len(lines),
            parsed_lines=parsed,
            failed_lines=failed
        )

    def _parse_line(self, line: str) -> ParsedLogEntry:
        # Try access log format
        match = self.COMBINED_LOG_PATTERN.match(line)
        if match:
            metadata = match.groupdict()
            status = int(metadata.get("status", 0))
            level = "ERROR" if status >= 400 else "INFO"

            try:
                timestamp = datetime.strptime(metadata["timestamp"], "%d/%b/%Y:%H:%M:%S %z")
            except Exception:
                timestamp = None

            return ParsedLogEntry(
                timestamp=timestamp,
                level=level,
                message=f"{metadata['method']} {metadata['path']} - {status}",
                source=self.source_type.value,
                metadata={
                    "ip": metadata.get("ip"),
                    "status": status,
                    "method": metadata.get("method"),
                    "path": metadata.get("path"),
                },
                raw=line
            )

        # Try error log format
        match = self.ERROR_LOG_PATTERN.match(line)
        if match:
            metadata = match.groupdict()
            level = self.ERROR_SEVERITY_MAP.get(metadata.get("level", "").lower(), "INFO")

            return ParsedLogEntry(
                timestamp=None,
                level=level,
                message=metadata.get("message", line),
                source=self.source_type.value,
                metadata={
                    "module": metadata.get("module"),
                    "apache_level": metadata.get("level"),
                },
                raw=line
            )

        return ParsedLogEntry(
            timestamp=None,
            level=None,
            message=line,
            source=self.source_type.value,
            raw=line
        )


class JenkinsLogParser(BaseLogParser):
    """Parser for Jenkins CI/CD pipeline logs."""

    DETECTION_PATTERNS = [
        re.compile(r'\[Pipeline\]|Finished: (SUCCESS|FAILURE)|hudson\.model', re.I),
        re.compile(r'Jenkins CLI|Jenkins Web UI', re.I),
        re.compile(r'\[JENKINS\]|\[hudson\]', re.I),
        re.compile(r'Building in workspace|Checking out git', re.I),
    ]

    PIPELINE_STAGE_PATTERN = re.compile(r'\[Pipeline\]\s+(.+)$', re.I)
    TIMESTAMP_PATTERN = re.compile(
        r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+\s+[+-]\d{4})\s+'
    )
    LEVEL_PATTERN = re.compile(r'\b(SEVERE|WARNING|INFO|FINE|FINER|FINEST)\b', re.I)

    SEVERITY_MAP = {
        "SEVERE": "ERROR",
        "WARNING": "WARN",
        "INFO": "INFO",
        "FINE": "DEBUG",
        "FINER": "DEBUG",
        "FINEST": "DEBUG",
    }

    @property
    def source_type(self) -> LogSource:
        return LogSource.JENKINS

    def can_parse(self, text: str) -> bool:
        return self.detect_source_patterns(text, self.DETECTION_PATTERNS)

    def parse(self, text: str) -> ParsedLogBatch:
        lines = text.splitlines()
        entries: list[ParsedLogEntry] = []
        parsed = 0
        failed = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                entry = self._parse_line(line)
                entries.append(entry)
                parsed += 1
            except Exception:
                failed += 1
                entries.append(ParsedLogEntry(
                    timestamp=None,
                    level=None,
                    message=line,
                    source=self.source_type.value,
                    raw=line
                ))

        return ParsedLogBatch(
            source_type=self.source_type,
            entries=entries,
            total_lines=len(lines),
            parsed_lines=parsed,
            failed_lines=failed
        )

    def _parse_line(self, line: str) -> ParsedLogEntry:
        timestamp = None
        level = None
        message = line
        metadata = {}

        # Extract timestamp
        ts_match = self.TIMESTAMP_PATTERN.match(line)
        if ts_match:
            try:
                timestamp = datetime.strptime(ts_match.group(1), "%Y-%m-%d %H:%M:%S.%f %z")
                message = line[ts_match.end():]
            except Exception:
                pass

        # Check for pipeline stage
        stage_match = self.PIPELINE_STAGE_PATTERN.search(line)
        if stage_match:
            metadata["pipeline_action"] = stage_match.group(1)

        # Extract level
        level_match = self.LEVEL_PATTERN.search(message)
        if level_match:
            level = self.SEVERITY_MAP.get(level_match.group(1), "INFO")

        return ParsedLogEntry(
            timestamp=timestamp,
            level=level,
            message=message,
            source=self.source_type.value,
            metadata=metadata,
            raw=line
        )


class GitHubActionsLogParser(BaseLogParser):
    """Parser for GitHub Actions workflow logs."""

    DETECTION_PATTERNS = [
        re.compile(r'##\[error\]|##\[warning\]|##\[notice\]', re.I),
        re.compile(r'Run actions/checkout|GITHUB_ACTIONS', re.I),
        re.compile(r'\^::(error|warning|notice)::', re.I),
        re.compile(r'GITHUB_WORKFLOW|GITHUB_RUN_ID|GITHUB_SHA', re.I),
    ]

    ANNOTATION_PATTERN = re.compile(
        r'^(?P<type>error|warning|notice)::(?P<params>[^:]*):(?P<message>.*)$',
        re.I
    )
    TIMESTAMP_PATTERN = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\s+')

    @property
    def source_type(self) -> LogSource:
        return LogSource.GITHUB_ACTIONS

    def can_parse(self, text: str) -> bool:
        return self.detect_source_patterns(text, self.DETECTION_PATTERNS)

    def parse(self, text: str) -> ParsedLogBatch:
        lines = text.splitlines()
        entries: list[ParsedLogEntry] = []
        parsed = 0
        failed = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                entry = self._parse_line(line)
                entries.append(entry)
                parsed += 1
            except Exception:
                failed += 1
                entries.append(ParsedLogEntry(
                    timestamp=None,
                    level=None,
                    message=line,
                    source=self.source_type.value,
                    raw=line
                ))

        return ParsedLogBatch(
            source_type=self.source_type,
            entries=entries,
            total_lines=len(lines),
            parsed_lines=parsed,
            failed_lines=failed
        )

    def _parse_line(self, line: str) -> ParsedLogEntry:
        level = None
        message = line
        metadata = {}

        # Check for GitHub Actions annotations
        match = self.ANNOTATION_PATTERN.match(line)
        if match:
            annotation_type = match.group("type").lower()
            level = annotation_type.upper() if annotation_type != "notice" else "INFO"
            message = match.group("message")
            params = match.group("params")
            if params:
                for param in params.split(","):
                    if "=" in param:
                        k, v = param.split("=", 1)
                        metadata[k.strip()] = v.strip()

        # Extract timestamp
        ts_match = self.TIMESTAMP_PATTERN.match(message)
        timestamp = None
        if ts_match:
            try:
                timestamp = datetime.fromisoformat(ts_match.group(1))
                message = message[ts_match.end():]
            except Exception:
                pass

        return ParsedLogEntry(
            timestamp=timestamp,
            level=level,
            message=message,
            source=self.source_type.value,
            metadata=metadata,
            raw=line
        )


class TerraformLogParser(BaseLogParser):
    """Parser for Terraform CLI output and logs."""

    DETECTION_PATTERNS = [
        re.compile(r'Terraform will perform|Plan: \d+ to add|Error: .*', re.I),
        re.compile(r'Apply complete|Destroy complete|Refresh complete', re.I),
        re.compile(r'\[TRACE\]|\[DEBUG\]|\[WARN\]', re.I),
        re.compile(r'terraform(?:\.exe)?\s+(apply|plan|destroy|init)', re.I),
    ]

    LEVEL_PREFIX_PATTERN = re.compile(r'^\[(TRACE|DEBUG|WARN|ERROR)\]\s+', re.I)
    TIMESTAMP_PATTERN = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^\s]*)\s+')

    @property
    def source_type(self) -> LogSource:
        return LogSource.TERRAFORM

    def can_parse(self, text: str) -> bool:
        return self.detect_source_patterns(text, self.DETECTION_PATTERNS)

    def parse(self, text: str) -> ParsedLogBatch:
        lines = text.splitlines()
        entries: list[ParsedLogEntry] = []
        parsed = 0
        failed = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                entry = self._parse_line(line)
                entries.append(entry)
                parsed += 1
            except Exception:
                failed += 1
                entries.append(ParsedLogEntry(
                    timestamp=None,
                    level=None,
                    message=line,
                    source=self.source_type.value,
                    raw=line
                ))

        return ParsedLogBatch(
            source_type=self.source_type,
            entries=entries,
            total_lines=len(lines),
            parsed_lines=parsed,
            failed_lines=failed
        )

    def _parse_line(self, line: str) -> ParsedLogEntry:
        level = None
        message = line
        metadata = {}

        # Extract level prefix
        match = self.LEVEL_PREFIX_PATTERN.match(line)
        if match:
            level = match.group(1).upper()
            message = line[match.end():]

        # Extract timestamp
        ts_match = self.TIMESTAMP_PATTERN.match(message)
        timestamp = None
        if ts_match:
            try:
                timestamp = datetime.fromisoformat(ts_match.group(1).replace("Z", "+00:00"))
                message = message[ts_match.end():]
            except Exception:
                pass

        return ParsedLogEntry(
            timestamp=timestamp,
            level=level,
            message=message,
            source=self.source_type.value,
            metadata=metadata,
            raw=line
        )


class CloudWatchLogParser(BaseLogParser):
    """Parser for AWS CloudWatch log exports."""

    DETECTION_PATTERNS = [
        re.compile(r'\t@timestamp\t|"@timestamp"|CloudWatch', re.I),
        re.compile(r'"logStream"|"logGroup"|"owner"', re.I),
        re.compile(r'"message":\s*"', re.I),
    ]

    JSON_LOG_PATTERN = re.compile(r'^\s*\{.*"@timestamp".*\}$', re.DOTALL)

    @property
    def source_type(self) -> LogSource:
        return LogSource.CLOUDWATCH

    def can_parse(self, text: str) -> bool:
        return self.detect_source_patterns(text, self.DETECTION_PATTERNS)

    def parse(self, text: str) -> ParsedLogBatch:
        lines = text.splitlines()
        entries: list[ParsedLogEntry] = []
        parsed = 0
        failed = 0

        # Try to parse as JSON array (CloudWatch JSON export format)
        try:
            data = json.loads(text)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        entry = self._parse_json_entry(item)
                        entries.append(entry)
                        parsed += 1
                return ParsedLogBatch(
                    source_type=self.source_type,
                    entries=entries,
                    total_lines=len(lines),
                    parsed_lines=parsed,
                    failed_lines=failed,
                    metadata={"format": "json_export"}
                )
        except json.JSONDecodeError:
            pass

        # Parse line by line
        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                entry = self._parse_line(line)
                entries.append(entry)
                parsed += 1
            except Exception:
                failed += 1
                entries.append(ParsedLogEntry(
                    timestamp=None,
                    level=None,
                    message=line,
                    source=self.source_type.value,
                    raw=line
                ))

        return ParsedLogBatch(
            source_type=self.source_type,
            entries=entries,
            total_lines=len(lines),
            parsed_lines=parsed,
            failed_lines=failed
        )

    def _parse_json_entry(self, data: dict) -> ParsedLogEntry:
        timestamp = None
        message = ""
        level = None
        metadata = {}

        if "@timestamp" in data:
            try:
                ts_value = data["@timestamp"]
                if isinstance(ts_value, (int, float)):
                    timestamp = datetime.utcfromtimestamp(ts_value / 1000)
                else:
                    timestamp = datetime.fromisoformat(str(ts_value).replace("Z", "+00:00"))
            except Exception:
                pass

        if "message" in data:
            message = str(data["message"])
        elif "@message" in data:
            message = str(data["@message"])

        # Try to extract level from message
        level_match = re.search(r'\b(TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\b', message, re.I)
        if level_match:
            level = level_match.group(1).upper()
            if level == "WARNING":
                level = "WARN"

        # Capture other fields as metadata
        for k, v in data.items():
            if k not in ("@timestamp", "message", "@message"):
                metadata[k] = v

        return ParsedLogEntry(
            timestamp=timestamp,
            level=level,
            message=message,
            source=self.source_type.value,
            metadata=metadata,
            raw=json.dumps(data) if data.get("message") else ""
        )

    def _parse_line(self, line: str) -> ParsedLogEntry:
        timestamp = None
        message = line
        level = None
        metadata = {}

        # Try JSON parsing
        if line.startswith('{'):
            try:
                data = json.loads(line)
                return self._parse_json_entry(data)
            except json.JSONDecodeError:
                pass

        # Tab-separated format: @timestamp @message @logStream
        parts = line.split('\t')
        if len(parts) >= 2:
            try:
                timestamp = datetime.fromisoformat(parts[0].replace("Z", "+00:00"))
            except Exception:
                pass
            message = parts[1] if len(parts) > 1 else line
            if len(parts) > 2:
                metadata["log_stream"] = parts[2]

        return ParsedLogEntry(
            timestamp=timestamp,
            level=level,
            message=message,
            source=self.source_type.value,
            metadata=metadata,
            raw=line
        )


class GenericLogParser(BaseLogParser):
    """Fallback parser for unrecognized log formats."""

    TIMESTAMP_PATTERNS = [
        re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^\s]*)\s+'),
        re.compile(r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+'),
        re.compile(r'^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+'),
    ]

    LEVEL_PATTERN = re.compile(r'\b(TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\b', re.I)

    @property
    def source_type(self) -> LogSource:
        return LogSource.GENERIC

    def can_parse(self, text: str) -> bool:
        # Generic parser can always parse
        return True

    def parse(self, text: str) -> ParsedLogBatch:
        lines = text.splitlines()
        entries: list[ParsedLogEntry] = []
        parsed = 0
        failed = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                entry = self._parse_line(line)
                entries.append(entry)
                parsed += 1
            except Exception:
                failed += 1
                entries.append(ParsedLogEntry(
                    timestamp=None,
                    level=None,
                    message=line,
                    source=self.source_type.value,
                    raw=line
                ))

        return ParsedLogBatch(
            source_type=self.source_type,
            entries=entries,
            total_lines=len(lines),
            parsed_lines=parsed,
            failed_lines=failed
        )

    def _parse_line(self, line: str) -> ParsedLogEntry:
        timestamp = None
        level = None
        message = line

        # Try various timestamp patterns
        for pattern in self.TIMESTAMP_PATTERNS:
            match = pattern.match(line)
            if match:
                try:
                    ts_str = match.group(1)
                    # Try multiple formats
                    for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%b %d %H:%M:%S"]:
                        try:
                            timestamp = datetime.strptime(ts_str, fmt)
                            break
                        except ValueError:
                            continue
                    message = line[match.end():]
                    break
                except Exception:
                    pass

        # Extract level
        level_match = self.LEVEL_PATTERN.search(message)
        if level_match:
            level = level_match.group(1).upper()
            if level == "WARNING":
                level = "WARN"

        return ParsedLogEntry(
            timestamp=timestamp,
            level=level,
            message=message,
            source=self.source_type.value,
            raw=line
        )


# Registry of all parsers (ordered by specificity)
LOG_PARSERS: list[BaseLogParser] = [
    KubernetesLogParser(),
    DockerLogParser(),
    NginxLogParser(),
    ApacheLogParser(),
    JenkinsLogParser(),
    GitHubActionsLogParser(),
    TerraformLogParser(),
    CloudWatchLogParser(),
    GenericLogParser(),  # Always last as fallback
]


def detect_log_source(text: str) -> LogSource:
    """Detect the log source type from the text content."""
    for parser in LOG_PARSERS:
        if isinstance(parser, GenericLogParser):
            continue
        if parser.can_parse(text):
            return parser.source_type
    return LogSource.GENERIC


def get_parser_for_source(source_type: LogSource) -> BaseLogParser:
    """Get the appropriate parser for a given log source type."""
    for parser in LOG_PARSERS:
        if parser.source_type == source_type:
            return parser
    return GenericLogParser()


def parse_logs(text: str, force_source: LogSource | None = None) -> ParsedLogBatch:
    """
    Parse log text using the appropriate parser.

    Args:
        text: The raw log text to parse
        force_source: Optional source type to force (skip auto-detection)

    Returns:
        ParsedLogBatch containing structured log entries
    """
    if force_source:
        parser = get_parser_for_source(force_source)
    else:
        # Find the first parser that can handle this text
        for parser in LOG_PARSERS:
            if isinstance(parser, GenericLogParser) or parser.can_parse(text):
                return parser.parse(text)
        parser = GenericLogParser()

    return parser.parse(text)