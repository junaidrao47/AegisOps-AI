from __future__ import annotations

from aegis_ai.agents.utils import extract_text, keyword_hits
from aegis_ai.orchestration.state import AgentResult, IncidentContext


def analyze_security(ctx: IncidentContext) -> AgentResult:
    text = extract_text(
        ctx.payload,
        ["security", "alerts", "logs", "details", "summary", "description"],
    )
    patterns = [
        r"cve-\d{4}-\d+",
        r"unauthorized",
        r"privilege escalation",
        r"token leak",
        r"credentials? exposed",
        r"malware",
        r"sql injection",
    ]
    hits = keyword_hits(text, patterns)
    findings = [f"Security signal: {hit}" for hit in hits]
    summary = "security analysis complete" if hits else "no critical security signals detected"
    confidence = 0.8 if hits else 0.35

    return AgentResult(
        agent="security",
        summary=summary,
        findings=findings,
        confidence=confidence,
        evidence=_trim_evidence(text),
    )


def _trim_evidence(text: str, limit: int = 3) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[:limit]
