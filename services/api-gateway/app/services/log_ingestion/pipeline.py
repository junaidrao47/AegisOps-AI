from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    index: int
    text: str


@dataclass(frozen=True)
class Finding:
    category: str
    severity: str
    title: str
    evidence: str | None


_ANSI_ESCAPE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def clean_text(text: str) -> str:
    text = _ANSI_ESCAPE.sub("", text)
    # normalize Windows newlines, trim null bytes
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    return text


def chunk_text(text: str, *, max_chars: int = 2200, overlap_chars: int = 200) -> list[Chunk]:
    if max_chars <= 0:
        return [Chunk(index=0, text=text)]

    lines = text.splitlines(keepends=True)
    chunks: list[Chunk] = []
    current: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if not current:
            return
        chunk_text_value = "".join(current).strip()
        if chunk_text_value:
            chunks.append(Chunk(index=len(chunks), text=chunk_text_value))

        if overlap_chars > 0 and chunk_text_value:
            overlap = chunk_text_value[-overlap_chars:]
            current = [overlap]
            current_len = len(overlap)
        else:
            current = []
            current_len = 0

    for line in lines:
        if current_len + len(line) > max_chars and current:
            flush()
        current.append(line)
        current_len += len(line)

    flush()
    return chunks


_SOURCE_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("kubernetes", re.compile(r"CrashLoopBackOff|OOMKilled|kubelet|kubectl|namespace=|pod/", re.I)),
    ("docker", re.compile(r"docker\[|containerd|\{""log"":|\{""time"":.*""log"":", re.I)),
    ("nginx", re.compile(r"nginx\/\d|\s\"(GET|POST|PUT|DELETE|PATCH)\s+[^\"]+\s+HTTP\/", re.I)),
    ("apache", re.compile(r"\"(GET|POST|PUT|DELETE|PATCH)\s+[^\"]+\s+HTTP\/\d\.\d\"\s+\d{3}\s+", re.I)),
    ("jenkins", re.compile(r"\[Pipeline\]|Finished: (SUCCESS|FAILURE)|hudson\.model", re.I)),
    ("github_actions", re.compile(r"##\[(error|warning)\]|Run actions\/checkout|GITHUB_ACTIONS", re.I)),
    ("terraform", re.compile(r"Terraform will perform|Plan: \d+ to add|Error: .*", re.I)),
    ("cloudwatch", re.compile(r"\t@timestamp\t|\"@timestamp\"|CloudWatch", re.I)),
]


def classify_source(text: str) -> str:
    sample = text[:200_000]
    for name, pat in _SOURCE_RULES:
        if pat.search(sample):
            return name
    return "generic"


_DETECTION_RULES: list[tuple[str, str, str, re.Pattern[str]]] = [
    ("CrashLoopBackOff", "high", "CrashLoopBackOff detected", re.compile(r"CrashLoopBackOff|Back-off restarting failed container", re.I)),
    ("OOMKilled", "high", "OOMKilled / out-of-memory kill detected", re.compile(r"OOMKilled|Killed process \d+|out of memory", re.I)),
    ("DNSFailure", "medium", "DNS resolution failure detected", re.compile(r"Temporary failure in name resolution|no such host|NXDOMAIN|SERVFAIL", re.I)),
    ("ConnectionTimeout", "medium", "Connection timeout detected", re.compile(r"timed out|ETIMEDOUT|context deadline exceeded|Read timed out", re.I)),
    ("SSLFailure", "medium", "SSL/TLS failure detected", re.compile(r"SSL routines|certificate verify failed|x509: certificate|handshake failure", re.I)),
    ("MemoryLeak", "low", "Potential memory leak symptoms detected", re.compile(r"memory leak|heap size|GC overhead limit exceeded", re.I)),
    ("CPUSpike", "low", "Potential CPU spike symptoms detected", re.compile(r"cpu throttling|load average|CPU\s+usage\s+\d{2,}%", re.I)),
    ("BuildFailure", "high", "Build failure detected", re.compile(r"BUILD FAILED|Build step .* marked build as failure|##\[error\]|Process completed with exit code", re.I)),
]


def detect_findings(text: str) -> list[Finding]:
    findings: list[Finding] = []
    sample = text[:500_000]

    for category, severity, title, pat in _DETECTION_RULES:
        m = pat.search(sample)
        if not m:
            continue
        # Provide a short evidence snippet around the match
        start = max(m.start() - 120, 0)
        end = min(m.end() + 200, len(sample))
        evidence = sample[start:end].replace("\n", " ").strip()
        findings.append(Finding(category=category, severity=severity, title=title, evidence=evidence))

    return findings


@dataclass(frozen=True)
class PipelineResult:
    source_type: str
    chunks: list[Chunk]
    findings: list[Finding]


def run_pipeline(raw_text: str) -> PipelineResult:
    cleaned = clean_text(raw_text)
    source_type = classify_source(cleaned)
    chunks = chunk_text(cleaned)
    findings = detect_findings(cleaned)
    return PipelineResult(source_type=source_type, chunks=chunks, findings=findings)
