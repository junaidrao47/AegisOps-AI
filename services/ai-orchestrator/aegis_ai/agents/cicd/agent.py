from __future__ import annotations

from aegis_ai.agents.utils import extract_text, keyword_hits
from aegis_ai.orchestration.state import AgentResult, IncidentContext


def analyze_cicd(ctx: IncidentContext) -> AgentResult:
    text = extract_text(ctx.payload, ["pipeline", "ci", "cd", "logs", "details", "summary"])
    patterns = [
        r"build failed",
        r"test(s)? failed",
        r"pipeline.*failed",
        r"artifact.*missing",
        r"deploy(ment)? failed",
        r"permission denied",
        r"timeout",
    ]
    hits = keyword_hits(text, patterns)
    findings = [f"Detected CI/CD signal: {hit}" for hit in hits]
    summary = "cicd analysis complete" if hits else "no critical cicd signals detected"
    confidence = 0.7 if hits else 0.4

    return AgentResult(
        agent="cicd",
        summary=summary,
        findings=findings,
        confidence=confidence,
        evidence=_trim_evidence(text),
    )


def _trim_evidence(text: str, limit: int = 3) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[:limit]
