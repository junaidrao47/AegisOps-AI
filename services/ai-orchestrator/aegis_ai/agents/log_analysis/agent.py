from __future__ import annotations

from aegis_ai.agents.utils import extract_text, keyword_hits
from aegis_ai.orchestration.state import AgentResult, IncidentContext


def analyze_logs(ctx: IncidentContext) -> AgentResult:
    text = extract_text(ctx.payload, ["logs", "log_text", "error", "trace", "details"])
    patterns = [
        r"exception",
        r"traceback",
        r"segmentation fault",
        r"panic",
        r"out of memory",
        r"connection refused",
        r"timeout",
        r"permission denied",
        r"disk full",
    ]
    hits = keyword_hits(text, patterns)
    findings = [f"Matched log signal: {hit}" for hit in hits]
    summary = "log analysis complete" if hits else "no critical log signals detected"
    confidence = 0.7 if hits else 0.4

    return AgentResult(
        agent="log_analysis",
        summary=summary,
        findings=findings,
        confidence=confidence,
        evidence=_trim_evidence(text),
    )


def _trim_evidence(text: str, limit: int = 3) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[:limit]
